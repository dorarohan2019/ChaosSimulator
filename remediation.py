import gym
from gym import spaces
import numpy as np
import time
import os
import torch
import random
from collections import deque
import boto3
from datetime import datetime
import logging
from stable_baselines3 import DQN
from models.predictive_model import LSTMAutoencoder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("remediation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("remediation_agent")

class RemediationEnvironment(gym.Env):
    """
    Remediation environment that automatically fixes AWS infrastructure issues.
    """
    def __init__(self, is_local=True, use_collected_states=True, load_model=False):
        """
        Initialize the remediation environment.
        
        Args:
            is_local (bool): If True, use LocalStack instead of real AWS.
            use_collected_states (bool): If True, use collected state data.
            load_model (bool): If True, load pretrained RL model.
        """
        super(RemediationEnvironment, self).__init__()
        
        # Define action and observation spaces
        self.action_space = spaces.Discrete(37)  # 37 remediation actions
        self.observation_space = spaces.Box(low=0, high=1, shape=(5, 25), dtype=np.float32)
        
        # LocalStack endpoint
        self.endpoint = 'http://localhost:4566' if is_local else None
        self.session = boto3.Session(
            aws_access_key_id='dummy' if is_local else os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key='dummy' if is_local else os.environ.get("AWS_SECRET_ACCESS_KEY"),
            region_name='us-east-1'
        )
        
        # Initialize AWS service clients
        self.initialize_aws_clients()
        
        # Define boundaries for state normalization
        self.state_min = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
        self.state_max = np.array([5, 5, 100, 2, 2, 200, 100, 1, 2000, 5.0, 3, 500, 10, 1000, 10, 5000, 5e9, 2, 500, 20, 50, 10, 5e6, 5e6, 10], dtype=np.float32)
        
        # Define optimal values for key metrics
        self.optimal_values = {
            1: 5.0,      # ec2_running
            2: 50.0,     # ec2_cpu_avg
            4: 2.0,      # rds_available
            5: 100.0,    # rds_connections
            6: 50.0,     # rds_cpu
            8: 1000.0,   # elb_requests
            9: 0.05,     # elb_latency
            11: 250.0,   # lambda_invocations
            12: 0.0,     # lambda_errors
            13: 200.0,   # lambda_duration
            15: 3000.0,  # s3_object_count
            16: 3e9,     # s3_total_size
            18: 100.0,   # sqs_message_count
            19: 0.0,     # security_findings
            20: 0.0,     # failed_logins
            21: 0.0,     # vulnerability_count
            22: 3e6,     # network_in
            23: 3e6,     # network_out
            24: 0.0      # packet_loss_percent
        }
        
        # Load RL model if requested
        if load_model:
            try:
                self.model = DQN.load("remediation_agent")
                logger.info("DQN model loaded successfully.")
            except (FileNotFoundError, ValueError) as e:
                logger.warning(f"DQN model loading error: {e}. Will use random actions.")
                self.model = None
        else:
            self.model = None
        
        # Load predictive model for anomaly detection
        self.predictive_model = LSTMAutoencoder(timesteps=5, features=25)
        try:
            self.predictive_model.load_state_dict(torch.load('lstm_autoencoder.pth'))
            self.predictive_model.eval()
            logger.info("LSTMAutoencoder model loaded successfully.")
        except (FileNotFoundError, RuntimeError) as e:
            logger.warning(f"LSTMAutoencoder model loading error: {e}")
            self.predictive_model = None
        
        # State management
        self.state_history = deque(maxlen=5)
        self.action_costs = {i: 0.5 for i in range(37)}  # Cost for each action
        
        # Get AWS resource information
        self.infrastructure_info = self.get_infrastructure_info()
        
        # Define remediation action methods
        self.remediation_actions = {
            i: getattr(self, f"remediation_action_{i}", self.no_action) 
            for i in range(37)
        }
        
        # Create effects mapping for each remediation action
        self.remediation_action_effects = self.define_remediation_action_effects()
        
        # Action history for logging
        self.action_history = []
        
        # Load collected states if available
        self.use_collected_states = use_collected_states
        if self.use_collected_states:
            try:
                self.collected_states = np.load("environment_states.npy")
                self.labels = np.load("labels.npy", allow_pickle=True)
                logger.info(f"Loaded {len(self.collected_states)} collected states.")
            except (FileNotFoundError, ValueError) as e:
                logger.warning(f"Collected states loading error: {e}. Using default states.")
                self.collected_states = None
                self.labels = None
        else:
            self.collected_states = None
            self.labels = None
    
    def initialize_aws_clients(self):
        """Initialize all AWS service clients."""
        self.ec2 = self.session.client('ec2', endpoint_url=self.endpoint, region_name='us-east-1')
        self.s3 = self.session.client('s3', endpoint_url=self.endpoint)
        self.rds = self.session.client('rds', endpoint_url=self.endpoint, region_name='us-east-1')
        self.lambda_ = self.session.client('lambda', endpoint_url=self.endpoint, region_name='us-east-1')
        self.elb = self.session.client('elb', endpoint_url=self.endpoint, region_name='us-east-1')
        self.dynamodb = self.session.client('dynamodb', endpoint_url=self.endpoint, region_name='us-east-1')
        self.iam = self.session.client('iam', endpoint_url=self.endpoint)
        self.cloudtrail = self.session.client('cloudtrail', endpoint_url=self.endpoint, region_name='us-east-1')
        self.waf = self.session.client('wafv2', endpoint_url=self.endpoint, region_name='us-east-1')
        self.apigateway = self.session.client('apigateway', endpoint_url=self.endpoint, region_name='us-east-1')
    
    def get_infrastructure_info(self):
        """Get information about current AWS infrastructure."""
        info = {}
        try:
            # EC2 instances
            response = self.ec2.describe_instances(
                Filters=[{'Name': 'tag:Name', 'Values': ['ChaosTest']}]
            )
            instances = [inst for res in response.get('Reservations', []) for inst in res.get('Instances', [])]
            info['instance_ids'] = [inst['InstanceId'] for inst in instances] if instances else ['i-123']
            
            # Security groups
            response = self.ec2.describe_security_groups(
                Filters=[{'Name': 'group-name', 'Values': ['chaos-sg']}]
            )
            info['sg_id'] = response['SecurityGroups'][0]['GroupId'] if response['SecurityGroups'] else 'sg-123'
            
            # API Gateway
            response = self.apigateway.get_rest_apis()
            info['api_id'] = response['items'][0]['id'] if response['items'] else 'api-123'
            
            return info
        except Exception as e:
            logger.error(f"Error getting infrastructure info: {e}")
            # Return default values if there's an error
            return {
                'instance_ids': ['i-123'],
                'sg_id': 'sg-123',
                'api_id': 'api-123'
            }
    
    def define_remediation_action_effects(self):
        """
        Define the effects of each remediation action on different metrics.
        
        Returns:
            dict: Mapping of action indices to metric changes.
        """
        # Each entry maps an action index to a dict of {metric_index: change_amount}
        # Positive changes increase the metric, negative changes decrease it
        return {
            # EC2 Instance Remediation
            0: {1: 1, 2: -10},                      # restore_ec2_instance
            1: {1: 1, 2: -5},                       # start_ec2_instance
            2: {2: -20, 6: -10},                    # relieve_cpu_stress
            3: {2: -15, 6: -5},                     # relieve_memory_stress
            
            # Storage Remediation
            4: {15: -100, 16: -1e8},                # relieve_disk_stress
            
            # Network Remediation
            5: {9: -0.5, 24: -2},                   # remove_network_delay
            6: {24: -3, 9: -0.5},                   # remove_packet_loss
            
            # S3 Remediation
            7: {15: 50, 16: 5e7},                   # restore_s3_object
            8: {19: -5, 20: -5},                    # fix_s3_permissions
            9: {8: 100, 9: -0.1},                   # remove_s3_throttling
            
            # Lambda Remediation
            10: {11: 50, 12: -2},                   # enable_lambda_function
            11: {13: -50, 12: -1},                  # reset_lambda_timeout
            12: {12: -5, 11: 20},                   # relieve_lambda_memory_pressure
            13: {11: 50, 13: -20},                  # remove_lambda_concurrency_limit
            
            # DynamoDB Remediation
            14: {22: 5e5, 23: 5e5},                 # restore_dynamodb_throughput
            15: {15: 100, 16: 1e8},                 # restore_dynamodb_items
            16: {22: 1e6, 23: 1e6},                 # enable_dynamodb_table
            
            # IAM Remediation
            17: {19: -5, 20: -5},                   # restore_iam_permissions
            18: {19: -8, 21: -2},                   # remove_restrictive_policy
            19: {20: -10, 19: -3},                  # reset_access_keys
            
            # API Remediation
            20: {8: 200, 9: -0.1},                  # unblock_api_requests
            
            # DNS Remediation
            21: {24: -5, 9: -0.1},                  # fix_dns_failure
            
            # ELB Remediation
            22: {8: 150, 9: -0.05},                 # restore_connection_draining
            23: {9: -0.3, 24: -1},                  # remove_latency_injection
            
            # RDS Remediation
            24: {4: 1, 6: -10},                     # restore_rds_failover
            25: {6: -20, 5: -15},                   # relieve_rds_storage_pressure
            26: {5: -25, 6: -5},                    # relieve_rds_connection_flood
            27: {6: -20, 2: -5},                    # relieve_rds_cpu_stress
            
            # More ELB Remediation
            28: {8: 300, 9: -0.2},                  # register_elb_instance
            29: {8: 250, 24: -1},                   # restore_elb_availability_zone
            
            # Security Remediation
            30: {19: -15, 20: -10, 21: -5},         # mitigate_security_breach
            31: {20: -20, 21: -3},                  # block_brute_force_login
            32: {24: -5, 9: -0.5, 8: 500},          # mitigate_ddos
            33: {19: -10, 21: -5, 16: -5e8},        # prevent_data_exfiltration
            
            # Monitoring Remediation
            34: {19: -5, 21: -2},                   # enable_cloudwatch_alarms
            35: {19: -5, 21: -3},                   # restore_cloudtrail_logs
            
            # No action
            36: {}                                  # no_action
        }
    
    # Placeholder for remediation action methods
    def no_action(self):
        """Do nothing."""
        pass
    
    def normalize_state(self, state):
        """
        Normalize state to range [0, 1].
        
        Args:
            state (np.ndarray): Raw state.
            
        Returns:
            np.ndarray: Normalized state.
        """
        normalized = (state - self.state_min) / (self.state_max - self.state_min + 1e-8)
        return np.clip(normalized, 0, 1)
    
    def denormalize_state(self, normalized_state):
        """
        Convert normalized state back to raw values.
        
        Args:
            normalized_state (np.ndarray): Normalized state.
            
        Returns:
            np.ndarray: Denormalized state.
        """
        return normalized_state * (self.state_max - self.state_min) + self.state_min
    
    def reset(self):
        """
        Reset the environment to an initial abnormal state that needs remediation.
        
        Returns:
            np.ndarray: Initial state observation.
        """
        # Try to find an anomalous state from collected data
        if self.use_collected_states and self.collected_states is not None and len(self.collected_states) >= 5:
            if self.labels is not None and len(self.labels) >= len(self.collected_states):
                # Find indices of anomalous states
                anomalous_indices = [i for i, label in enumerate(self.labels) 
                                     if label != 'normal' and i <= len(self.collected_states) - 5]
                
                if anomalous_indices:
                    # Choose a random anomalous state as starting point
                    start_idx = random.choice(anomalous_indices)
                else:
                    # Fall back to random state if no anomalous states
                    start_idx = random.randint(0, len(self.collected_states) - 5)
            else:
                # No labels, pick random state
                start_idx = random.randint(0, len(self.collected_states) - 5)
            
            # Load sequence of 5 states starting from selected index
            self.state_history.clear()
            for i in range(5):
                state = self.collected_states[start_idx + i].astype(np.float32)
                normalized_state = self.normalize_state(state)
                self.state_history.append(normalized_state.copy())
            
            self.state = self.state_history[-1].copy()
        else:
            # Create synthetic abnormal state
            raw_state = np.array([
                5, 3, 85.0, 2, 1, 180, 90.0, 1, 500, 2.0, 3, 400, 8, 800, 
                10, 4500, 4.5e9, 2, 450, 15, 30, 8, 1e6, 1e6, 7.0
            ], dtype=np.float32)
            
            self.state = self.normalize_state(raw_state)
            self.state_history.clear()
            for _ in range(5):
                self.state_history.append(self.state.copy())
        
        # Clear action history
        self.action_history.clear()
        
        return np.array(self.state_history)
    
    def step(self, action):
        """
        Apply a remediation action to the current state.
        
        Args:
            action (int): Remediation action to take.
            
        Returns:
            tuple: (observation, reward, done, info)
        """
        # Record the state before taking action
        state_sequence_before = np.array(self.state_history)
        denormalized_state_before = self.denormalize_state(self.state)
        anomaly_score_before = self.predictive_model.get_anomaly_score(state_sequence_before)
        
        # Record action info
        action_info = {
            'action': int(action),
            'timestamp': datetime.now().isoformat(),
            'state_before': denormalized_state_before.copy(),
            'anomaly_before': anomaly_score_before
        }
        
        # Apply the action's effects to the state
        for idx, delta in self.remediation_action_effects.get(action, {}).items():
            # Update the state metric
            self.state[idx] += delta * 0.01  # Scale to normalized space
        
        # Ensure state stays in valid range
        self.state = np.clip(self.state, 0, 1)
        
        # Add new state to history
        self.state_history.append(self.state.copy())
        if len(self.state_history) > 5:
            self.state_history.popleft()
        
        # Convert to sequence for observation
        state_sequence_after = np.array(self.state_history)
        
        # Calculate anomaly score after action
        anomaly_score_after = self.predictive_model.get_anomaly_score(state_sequence_after)
        
        # Update action info with results
        denormalized_state_after = self.denormalize_state(self.state)
        action_info['state_after'] = denormalized_state_after.copy()
        action_info['anomaly_after'] = anomaly_score_after
        
        # Calculate reward: reduction in anomaly score minus action cost
        anomaly_reduction = max(0, anomaly_score_before - anomaly_score_after)
        action_cost = self.action_costs[action]
        reward = anomaly_reduction - (0.1 * action_cost)
        
        # Add reward to action info
        action_info['reward'] = reward
        self.action_history.append(action_info)
        
        # Log the action
        logger.info(f"Remediation {action}: Anomaly {anomaly_score_before:.4f} -> {anomaly_score_after:.4f}, Reward: {reward:.4f}")
        
        # Check if done
        done = anomaly_score_after < 0.05 or len(self.action_history) >= 10
        
        # Additional info for debugging
        info = {
            'anomaly_before': anomaly_score_before,
            'anomaly_after': anomaly_score_after,
            'action_cost': action_cost
        }
        
        # Log to file for analysis
        with open("remediation_log.txt", "a") as f:
            f.write(f"{datetime.now().isoformat()}, Action: {action}, Anomaly: {anomaly_score_before:.4f} -> {anomaly_score_after:.4f}, Reward: {reward:.4f}\n")
        
        return state_sequence_after, reward, done, info
    
    def select_action(self, state):
        """
        Select a remediation action using the loaded model or random if no model.
        
        Args:
            state (np.ndarray): Current state observation.
            
        Returns:
            torch.Tensor: Selected action.
        """
        if self.model:
            # Ensure state is in the right format for the model
            if isinstance(state, np.ndarray):
                if len(state.shape) == 2:
                    state = np.expand_dims(state, axis=0)  # Add batch dimension
            
            # Use the model to get action
            action, _ = self.model.predict(state, deterministic=False)
            return torch.tensor([action])
        else:
            # Random action if no model is loaded
            return torch.tensor([self.action_space.sample()])
    
    def get_action_description(self, action):
        """
        Get a human-readable description of the remediation action.
        
        Args:
            action (int): The action index.
            
        Returns:
            str: Description of the action.
        """
        actions = {
            0: "Restore EC2 instance",
            1: "Start EC2 instance",
            2: "Relieve CPU stress",
            3: "Relieve memory stress",
            4: "Relieve disk stress",
            5: "Remove network delay",
            6: "Remove packet loss",
            7: "Restore S3 object",
            8: "Fix S3 permissions",
            9: "Remove S3 throttling",
            10: "Enable Lambda function",
            11: "Reset Lambda timeout",
            12: "Relieve Lambda memory pressure",
            13: "Remove Lambda concurrency limit",
            14: "Restore DynamoDB throughput",
            15: "Restore DynamoDB items",
            16: "Enable DynamoDB table",
            17: "Restore IAM permissions",
            18: "Remove restrictive policy",
            19: "Reset access keys",
            20: "Unblock API requests",
            21: "Fix DNS failure",
            22: "Restore connection draining",
            23: "Remove latency injection",
            24: "Restore RDS failover",
            25: "Relieve RDS storage pressure",
            26: "Relieve RDS connection flood",
            27: "Relieve RDS CPU stress",
            28: "Register ELB instance",
            29: "Restore ELB availability zone",
            30: "Mitigate security breach",
            31: "Block brute force login",
            32: "Mitigate DDoS",
            33: "Prevent data exfiltration",
            34: "Enable CloudWatch alarms",
            35: "Restore CloudTrail logs",
            36: "No action"
        }
        return actions.get(action, f"Unknown action {action}")
    
    def get_action_history(self):
        """
        Get the history of actions performed.
        
        Returns:
            list: List of action information dictionaries.
        """
        return self.action_history
    
    def save_model(self, filename="remediation_agent"):
        """
        Save the RL model.
        
        Args:
            filename (str): Name of the file to save the model to.
        """
        if self.model:
            self.model.save(filename)
            logger.info(f"Model saved to {filename}")
    
    def load_model(self, filename="remediation_agent"):
        """
        Load the RL model.
        
        Args:
            filename (str): Name of the file to load the model from.
        """
        try:
            self.model = DQN.load(filename)
            logger.info(f"Model loaded from {filename}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
