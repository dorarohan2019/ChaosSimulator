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
        logging.FileHandler("chaos.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("chaos_agent")

class ChaosEnvironment(gym.Env):
    """
    Chaos Engineering environment that simulates AWS service disruptions.
    """
    def __init__(self, is_local=True, use_collected_states=True, load_model=False):
        """
        Initialize the chaos environment.
        
        Args:
            is_local (bool): If True, use LocalStack instead of real AWS.
            use_collected_states (bool): If True, use collected state data.
            load_model (bool): If True, load pretrained RL model.
        """
        super(ChaosEnvironment, self).__init__()
        
        # Define action and observation spaces
        self.action_space = spaces.Discrete(37)  # 37 chaos actions
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
        
        # Load RL model if requested
        if load_model:
            try:
                self.model = DQN.load("chaos_agent")
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
        
        # Create effects mapping for each chaos action to impact specific metrics
        self.chaos_action_effects = self.define_chaos_action_effects()
        
        # Action history for logging
        self.action_history = []
        
        # Load collected states if available
        self.use_collected_states = use_collected_states
        if self.use_collected_states:
            try:
                self.collected_states = np.load("environment_states.npy")
                logger.info(f"Loaded {len(self.collected_states)} collected states.")
            except (FileNotFoundError, ValueError) as e:
                logger.warning(f"Collected states loading error: {e}. Using default states.")
                self.collected_states = None
        else:
            self.collected_states = None
    
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
    
    def define_chaos_action_effects(self):
        """
        Define the effects of each chaos action on different metrics.
        
        Returns:
            dict: Mapping of action indices to metric changes.
        """
        # Each entry maps an action index to a dict of {metric_index: change_amount}
        return {
            # EC2 Instance Actions
            0: {0: -1, 1: -1, 2: 20},               # terminate_ec2_instance
            1: {2: 30},                             # cause_cpu_stress
            2: {2: 20, 24: 2},                      # stop_ec2_instance
            
            # RDS Actions
            3: {4: -1, 6: 20},                      # stop_rds_instance
            4: {5: 50, 6: 30},                      # rds_connection_flood
            5: {5: -50, 6: -10},                    # reduce_rds_capacity
            
            # Lambda Actions
            6: {11: -50, 12: 5},                    # disable_lambda_function
            7: {11: 100, 12: 3, 13: 50},            # lambda_memory_pressure
            8: {13: 200, 12: 2},                    # reduce_lambda_timeout
            
            # S3 Actions
            9: {15: -20, 16: -1e8},                 # delete_s3_objects
            10: {22: -1e6, 23: -1e6},               # restrict_s3_permissions
            11: {22: -2e6, 23: -2e6},               # s3_throttling
            
            # NetworkActions
            12: {9: 0.2, 24: 3},                    # introduce_network_latency
            13: {24: 8, 9: 0.5},                    # packet_loss
            14: {9: 1.0, 8: -200},                  # network_partition
            
            # DynamoDB Actions
            15: {15: -100, 16: -2e8},               # reduce_dynamodb_capacity
            16: {22: -5e5, 23: -5e5},               # dynamodb_throttling
            17: {22: -1e6, 23: -1e6},               # disable_dynamodb_table
            
            # Security Actions
            18: {19: 10, 20: 5},                    # revoke_iam_permissions
            19: {19: 15, 21: 5},                    # introduce_security_group_vulnerability
            20: {20: 30, 19: 5},                    # simulate_brute_force_attack
            
            # IAM Actions
            21: {19: 10, 21: 3},                    # create_excessive_roles
            22: {19: 12, 21: 4},                    # revoke_key_permissions
            23: {19: 8, 21: 2},                     # add_restrictive_policy
            
            # API Gateway Actions
            24: {8: -300, 9: 0.2},                  # disable_api_endpoint
            25: {8: -100, 9: 0.3},                  # api_throttling
            
            # ElasticLoadBalancer Actions
            26: {8: -500, 9: 0.1},                  # deregister_elb_instances
            27: {8: -200, 9: 0.2},                  # disable_elb_availability_zone
            
            # DNS Actions
            28: {24: 5, 9: 0.3},                    # dns_failure
            
            # CloudWatch Actions
            29: {19: 3, 21: 1},                     # disable_cloudwatch_alarms
            
            # CloudTrail Actions
            30: {19: 5, 21: 2},                     # disable_cloudtrail_logging
            
            # Advanced Attack Simulations
            31: {19: 20, 20: 40, 21: 5},            # simulate_security_breach
            32: {24: 7, 9: 1.5, 8: -1000},          # simulate_ddos_attack
            33: {19: 15, 16: 1e9, 21: 4},           # simulate_data_exfiltration
            
            # Miscellaneous
            34: {5: 100, 6: 50},                    # cause_database_corruption
            35: {11: 200, 12: 8, 13: 300},          # force_memory_leaks
            36: {2: 10, 6: 10, 9: 0.1, 24: 1}       # gradual_degradation
        }
    
    def normalize_state(self, state_sequence):
        """
        Normalize the entire state sequence to the range [0, 1].

        Args:
            state_sequence (np.ndarray): State sequence of shape (5, 25).

        Returns:
            np.ndarray: Normalized state sequence of shape (5, 25).
        """
        state_sequence = np.clip(state_sequence, self.state_min, self.state_max)
        normalized_sequence = (state_sequence - self.state_min) / (self.state_max - self.state_min + 1e-8)
        return normalized_sequence

    def reset(self):
        """
        Reset the environment to the initial state.

        Returns:
            np.ndarray: Normalized initial state sequence of shape (5, 25).
        """
        if self.use_collected_states and self.collected_states is not None:
            idx = random.randint(0, len(self.collected_states) - 1)
            self.state = np.clip(self.collected_states[idx], self.state_min, self.state_max)
        else:
            # Default state with realistic values aligned with state_max
            self.state = np.array([
                5, 5, 40.0, 2, 2, 100, 50.0, 1, 1000, 0.05, 3, 250, 0, 200.0, 10, 
                3000, 2e9, 2, 100, 0, 0, 0, 3e6, 3e6, 0.5
            ], dtype=np.float32)
        
        # Clear state history and action history
        self.state_history.clear()
        self.action_history.clear()
        
        # Initialize history with current state
        for _ in range(5):
            self.state_history.append(self.state.copy())
        
        state_sequence = np.array(self.state_history)
        return self.normalize_state(state_sequence)

    def step(self, action):
        """
        Take a step in the environment based on the action.

        Args:
            action (int): The action to take (0 to 36).

        Returns:
            tuple: (observation, reward, done, info)
        """
        # Record the action and time
        action_info = {
            'action': int(action),
            'timestamp': datetime.now().isoformat(),
            'state_before': self.state.copy()
        }
        
        # Apply the chaos action effects to the state
        for idx, delta in self.chaos_action_effects.get(action, {}).items():
            self.state[idx] = max(0, self.state[idx] + delta)
        self.state = np.clip(self.state, self.state_min, self.state_max)
        
        # Update action info with new state
        action_info['state_after'] = self.state.copy()
        self.action_history.append(action_info)
        
        # Log the action
        logger.info(f"Performed chaos action {action}: {list(self.chaos_action_effects.get(action, {}).items())}")
        
        # Update state history
        self.state_history.append(self.state.copy())
        if len(self.state_history) > 5:
            self.state_history.popleft()
        
        # Convert state history to sequence and normalize
        state_sequence = np.array(self.state_history)
        normalized_state = self.normalize_state(state_sequence)
        
        # Calculate reward based on anomaly score
        anomaly_score = 0
        if self.predictive_model:
            anomaly_score = self.predictive_model.get_anomaly_score(normalized_state)
        
        business_impact = max(0, 5 - self.state[1])  # Penalty for reducing ec2_running
        reward = anomaly_score - (0.1 * self.action_costs[action]) - (0.2 * business_impact)
        
        # Record anomaly score in action info
        action_info['anomaly_score'] = anomaly_score
        action_info['reward'] = reward
        
        # Check if episode is done
        done = self.state[1] <= 0 or len(self.action_history) >= 100
        
        # Additional info for debugging
        info = {
            'anomaly_score': anomaly_score,
            'business_impact': business_impact,
            'action_cost': self.action_costs[action]
        }
        
        # Log to file for analysis
        with open("chaos_log.txt", "a") as f:
            f.write(f"{datetime.now().isoformat()}, Action: {action}, Anomaly: {anomaly_score:.4f}, Reward: {reward:.4f}\n")
        
        return normalized_state, reward, done, info
    
    def select_action(self, state):
        """
        Select an action using the loaded model or random if no model.
        
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
        Get a human-readable description of the chaos action.
        
        Args:
            action (int): The action index.
            
        Returns:
            str: Description of the action.
        """
        actions = {
            0: "Terminate EC2 instance",
            1: "Cause CPU stress",
            2: "Stop EC2 instance",
            3: "Stop RDS instance",
            4: "RDS connection flood",
            5: "Reduce RDS capacity",
            6: "Disable Lambda function",
            7: "Lambda memory pressure",
            8: "Reduce Lambda timeout",
            9: "Delete S3 objects",
            10: "Restrict S3 permissions",
            11: "S3 throttling",
            12: "Introduce network latency",
            13: "Introduce packet loss",
            14: "Network partition",
            15: "Reduce DynamoDB capacity",
            16: "DynamoDB throttling",
            17: "Disable DynamoDB table",
            18: "Revoke IAM permissions",
            19: "Introduce security group vulnerability",
            20: "Simulate brute force attack",
            21: "Create excessive IAM roles",
            22: "Revoke key permissions",
            23: "Add restrictive policy",
            24: "Disable API endpoint",
            25: "API throttling",
            26: "Deregister ELB instances",
            27: "Disable ELB availability zone",
            28: "DNS failure",
            29: "Disable CloudWatch alarms",
            30: "Disable CloudTrail logging",
            31: "Simulate security breach",
            32: "Simulate DDoS attack",
            33: "Simulate data exfiltration",
            34: "Cause database corruption",
            35: "Force memory leaks",
            36: "Gradual service degradation"
        }
        return actions.get(action, f"Unknown action {action}")
    
    def get_action_history(self):
        """
        Get the history of actions performed.
        
        Returns:
            list: List of action information dictionaries.
        """
        return self.action_history
    
    def save_model(self, filename="chaos_agent"):
        """
        Save the RL model.
        
        Args:
            filename (str): Name of the file to save the model to.
        """
        if self.model:
            self.model.save(filename)
            logger.info(f"Model saved to {filename}")
    
    def load_model(self, filename="chaos_agent"):
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
