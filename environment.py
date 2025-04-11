import numpy as np
import random
import time
import pandas as pd
import os

class StateCollector:
    """
    Collects and manages environment states for AWS infrastructure monitoring.
    """
    def __init__(self, scenarios=None):
        """
        Initialize the StateCollector for generating system states.

        Args:
            scenarios (list, optional): List of scenarios to use. Defaults to predefined scenarios.
        """
        self.scenarios = scenarios or [
            'normal', 'high_load', 'resource_exhaustion',
            'network_issues', 'security_incidents', 'service_outages'
        ]
        
        # State storage
        self.states = []
        self.labels = []
        self.current_state = None
        self.current_scenario = None
        
        # Feature names
        self.metric_keys = [
            'ec2_count', 'ec2_running', 'ec2_cpu_avg',
            'rds_count', 'rds_available', 'rds_connections', 'rds_cpu',
            'elb_count', 'elb_requests', 'elb_latency',
            'lambda_count', 'lambda_invocations', 'lambda_errors', 'lambda_duration',
            's3_bucket_count', 's3_object_count', 's3_total_size',
            'sqs_queue_count', 'sqs_message_count',
            'security_findings', 'failed_logins', 'vulnerability_count',
            'network_in', 'network_out', 'packet_loss_percent'
        ]
        
        # Define realistic bounds for each feature
        self.state_min = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
        self.state_max = np.array([5, 5, 100, 2, 2, 200, 100, 1, 2000, 5.0, 3, 500, 10, 1000, 10, 5000, 5e9, 2, 500, 20, 50, 10, 5e6, 5e6, 10], dtype=np.float32)

    def collect_state(self, scenario=None, temporal=False):
        """
        Generate a synthetic state based on the provided scenario or a random one.

        Args:
            scenario (str, optional): Specific scenario (e.g., 'normal'). If None, choose randomly.
            temporal (bool): If True, generate state based on the previous state for temporal continuity.

        Returns:
            dict: Generated state with metrics and timestamp.
        """
        if scenario is None:
            scenario = random.choice(self.scenarios)
        
        if temporal and self.current_state is not None and self.current_scenario == scenario:
            state = self._generate_next_state(scenario)
        else:
            state = self._generate_independent_state(scenario)
            if temporal:
                self.current_state = state.copy()
                self.current_scenario = scenario
        
        state['timestamp'] = time.time()
        state['scenario'] = scenario
        return state

    def _generate_independent_state(self, scenario):
        """Generate an independent state based on the scenario."""
        state = {}
        state.update(self._generate_ec2_metrics(scenario))
        state.update(self._generate_rds_metrics(scenario))
        state.update(self._generate_elb_metrics(scenario))
        state.update(self._generate_lambda_metrics(scenario))
        state.update(self._generate_s3_metrics(scenario))
        state.update(self._generate_sqs_metrics(scenario))
        state.update(self._generate_security_metrics(scenario))
        state.update(self._generate_network_metrics(scenario))
        return state

    def _generate_next_state(self, scenario):
        """Generate the next state based on the current state and scenario for temporal dynamics."""
        state = self.current_state.copy()
        
        # Apply scenario-specific changes to create temporal continuity
        if scenario == 'normal':
            state['ec2_cpu_avg'] = max(0, min(100, state['ec2_cpu_avg'] + random.uniform(-5, 5)))
            state['rds_connections'] = max(0, min(200, state['rds_connections'] + random.randint(-10, 10)))
            state['lambda_errors'] = max(0, min(10, state['lambda_errors'] + random.randint(-1, 1)))
        elif scenario == 'high_load':
            state['ec2_cpu_avg'] = min(100, state['ec2_cpu_avg'] + random.uniform(0, 5))
            state['rds_connections'] = min(200, state['rds_connections'] + random.randint(0, 10))
            state['elb_requests'] = min(2000, state['elb_requests'] + random.randint(0, 50))
        elif scenario == 'resource_exhaustion':
            state['ec2_cpu_avg'] = min(100, state['ec2_cpu_avg'] + random.uniform(0, 10))
            state['lambda_errors'] = min(10, state['lambda_errors'] + random.randint(0, 2))
            state['s3_total_size'] = min(5e9, state['s3_total_size'] + random.uniform(0, 1e8))
        elif scenario == 'network_issues':
            state['packet_loss_percent'] = min(10, state['packet_loss_percent'] + random.uniform(0, 1))
            state['elb_latency'] = min(5.0, state['elb_latency'] + random.uniform(0, 0.1))
        elif scenario == 'security_incidents':
            state['failed_logins'] = min(50, state['failed_logins'] + random.randint(0, 3))
            state['security_findings'] = min(20, state['security_findings'] + random.randint(0, 2))
        elif scenario == 'service_outages':
            if random.random() < 0.1:  # 10% chance of service outage
                state['ec2_running'] = max(0, state['ec2_running'] - 1)
                state['rds_available'] = max(0, state['rds_available'] - 1)
        
        self.current_state = state
        return state

    def _generate_ec2_metrics(self, scenario):
        """Generate EC2-related metrics based on the scenario."""
        if scenario == 'normal':
            ec2_running = random.randint(2, 4)  # Away from 0 and 5
            ec2_cpu_avg = random.uniform(20, 40)  # Middle range
        elif scenario == 'high_load':
            ec2_running = 5  # High but allows decrease
            ec2_cpu_avg = random.uniform(60, 80)
        elif scenario == 'resource_exhaustion':
            ec2_running = 5
            ec2_cpu_avg = random.uniform(80, 95)  # Below max to allow decrease
        elif scenario == 'service_outages':
            ec2_running = random.randint(0, 2)  # Low, allows increase
            ec2_cpu_avg = random.uniform(10, 30)
        else:
            ec2_running = random.randint(1, 4)
            ec2_cpu_avg = random.uniform(20, 80)
        
        return {'ec2_count': 5, 'ec2_running': ec2_running, 'ec2_cpu_avg': ec2_cpu_avg}

    def _generate_rds_metrics(self, scenario):
        """Generate RDS-related metrics based on the scenario."""
        if scenario == 'normal':
            rds_available = 2
            rds_connections = random.randint(20, 60)  # Away from 0 and 200
            rds_cpu = random.uniform(10, 30)
        elif scenario == 'high_load':
            rds_available = 2
            rds_connections = random.randint(140, 180)  # High but below max
            rds_cpu = random.uniform(50, 70)
        elif scenario == 'resource_exhaustion':
            rds_available = 2
            rds_connections = random.randint(180, 200)
            rds_cpu = random.uniform(80, 95)
        elif scenario == 'service_outages':
            rds_available = random.randint(0, 1)
            rds_connections = random.randint(10, 40)
            rds_cpu = random.uniform(5, 20)
        else:
            rds_available = random.randint(1, 2)
            rds_connections = random.randint(20, 140)
            rds_cpu = random.uniform(10, 50)
        
        return {'rds_count': 2, 'rds_available': rds_available, 'rds_connections': rds_connections, 'rds_cpu': rds_cpu}

    def _generate_elb_metrics(self, scenario):
        """Generate ELB-related metrics based on the scenario."""
        if scenario == 'normal':
            elb_requests = random.randint(200, 600)  # Away from 0 and 2000
            elb_latency = random.uniform(0.02, 0.1)
        elif scenario == 'high_load':
            elb_requests = random.randint(1400, 1800)  # High but below max
            elb_latency = random.uniform(0.1, 0.4)
        elif scenario == 'network_issues':
            elb_requests = random.randint(100, 400)
            elb_latency = random.uniform(0.4, 1.0)
        elif scenario == 'service_outages':
            elb_requests = random.randint(50, 200)
            elb_latency = random.uniform(0.5, 3.0)
        else:
            elb_requests = random.randint(200, 1400)
            elb_latency = random.uniform(0.02, 0.3)
        
        return {'elb_count': 1, 'elb_requests': elb_requests, 'elb_latency': elb_latency}

    def _generate_lambda_metrics(self, scenario):
        """Generate Lambda-related metrics based on the scenario."""
        if scenario == 'normal':
            lambda_invocations = random.randint(100, 200)  # Away from 0 and 500
            lambda_errors = random.randint(0, 2)  # Low errors
            lambda_duration = random.uniform(150, 250)
        elif scenario == 'high_load':
            lambda_invocations = random.randint(300, 400)
            lambda_errors = random.randint(2, 4)
            lambda_duration = random.uniform(300, 500)
        elif scenario == 'resource_exhaustion':
            lambda_invocations = random.randint(400, 500)
            lambda_errors = random.randint(5, 8)
            lambda_duration = random.uniform(600, 900)
        elif scenario == 'service_outages':
            lambda_invocations = random.randint(50, 100)
            lambda_errors = random.randint(5, 10)
            lambda_duration = random.uniform(800, 1000)
        else:
            lambda_invocations = random.randint(100, 300)
            lambda_errors = random.randint(1, 5)
            lambda_duration = random.uniform(150, 500)
        
        return {'lambda_count': 3, 'lambda_invocations': lambda_invocations, 'lambda_errors': lambda_errors, 'lambda_duration': lambda_duration}

    def _generate_s3_metrics(self, scenario):
        """Generate S3-related metrics based on the scenario."""
        if scenario == 'normal':
            s3_object_count = random.randint(2000, 3000)
            s3_total_size = random.uniform(1e9, 3e9)
        elif scenario == 'high_load':
            s3_object_count = random.randint(3500, 4500)
            s3_total_size = random.uniform(3e9, 4e9)
        elif scenario == 'resource_exhaustion':
            s3_object_count = random.randint(4500, 5000)
            s3_total_size = random.uniform(4e9, 5e9)
        else:
            s3_object_count = random.randint(1000, 4000)
            s3_total_size = random.uniform(0.5e9, 4e9)
        
        return {'s3_bucket_count': 10, 's3_object_count': s3_object_count, 's3_total_size': s3_total_size}

    def _generate_sqs_metrics(self, scenario):
        """Generate SQS-related metrics based on the scenario."""
        if scenario == 'normal':
            sqs_message_count = random.randint(10, 100)  # Away from 0 and 500
        elif scenario == 'high_load':
            sqs_message_count = random.randint(300, 450)
        elif scenario == 'resource_exhaustion':
            sqs_message_count = random.randint(450, 500)
        else:
            sqs_message_count = random.randint(10, 300)
        
        return {'sqs_queue_count': 2, 'sqs_message_count': sqs_message_count}

    def _generate_security_metrics(self, scenario):
        """Generate security-related metrics based on the scenario."""
        if scenario == 'normal':
            security_findings = random.randint(0, 2)
            failed_logins = random.randint(0, 5)
            vulnerability_count = random.randint(0, 2)
        elif scenario == 'security_incidents':
            security_findings = random.randint(10, 20)
            failed_logins = random.randint(20, 50)
            vulnerability_count = random.randint(5, 10)
        else:
            security_findings = random.randint(1, 5)
            failed_logins = random.randint(5, 15)
            vulnerability_count = random.randint(1, 3)
        
        return {'security_findings': security_findings, 'failed_logins': failed_logins, 'vulnerability_count': vulnerability_count}

    def _generate_network_metrics(self, scenario):
        """Generate network-related metrics based on the scenario."""
        if scenario == 'normal':
            network_in = random.uniform(1e6, 3e6)
            network_out = random.uniform(1e6, 3e6)
            packet_loss_percent = random.uniform(0, 0.5)
        elif scenario == 'network_issues':
            network_in = random.uniform(0.5e6, 1e6)
            network_out = random.uniform(0.5e6, 1e6)
            packet_loss_percent = random.uniform(5, 10)
        elif scenario == 'high_load':
            network_in = random.uniform(4e6, 5e6)
            network_out = random.uniform(4e6, 5e6)
            packet_loss_percent = random.uniform(1, 3)
        else:
            network_in = random.uniform(1e6, 4e6)
            network_out = random.uniform(1e6, 4e6)
            packet_loss_percent = random.uniform(0.1, 3)
        
        return {'network_in': network_in, 'network_out': network_out, 'packet_loss_percent': packet_loss_percent}

    def collect_samples(self, num_samples=5000, interval=0, scenario=None, temporal=True, 
                       anomaly_prob=0.3, progress_callback=None):
        """
        Collect a specified number of synthetic state samples with a probability of anomalies.

        Args:
            num_samples (int): Number of samples to collect.
            interval (float): Time interval between samples in seconds.
            scenario (str, optional): Specific scenario for all states.
            temporal (bool): If True, generate temporally correlated states.
            anomaly_prob (float): Probability of generating an anomalous state.
            progress_callback (callable, optional): Function to call with progress updates.

        Returns:
            tuple: (states, labels) where states is list of dicts and labels is list of scenarios.
        """
        print(f"Collecting {num_samples} synthetic state samples with interval {interval}s and anomaly probability {anomaly_prob}")
        
        self.states = []
        self.labels = []
        
        for i in range(num_samples):
            # Choose scenario based on anomaly probability
            if scenario is None:
                if random.random() < anomaly_prob:
                    chosen_scenario = random.choice([s for s in self.scenarios if s != 'normal'])
                else:
                    chosen_scenario = 'normal'
            else:
                chosen_scenario = scenario
            
            # Collect state
            state = self.collect_state(chosen_scenario, temporal)
            self.states.append(state)
            self.labels.append(chosen_scenario)
            
            # Update progress
            if progress_callback and i % max(1, num_samples // 100) == 0:
                progress_callback(i / num_samples)
            
            # Print progress
            if i % max(1, num_samples // 10) == 0:
                print(f"Collected state {i+1}/{num_samples}")
            
            # Wait interval if specified
            if interval > 0 and i < num_samples - 1:
                time.sleep(interval)
        
        print(f"Collected {len(self.states)} samples")
        return self.states, self.labels

    def save_states(self, filename="environment_states.npy", label_filename="labels.npy", csv_filename=None):
        """
        Save collected states and labels to files.

        Args:
            filename (str): File to save states numpy array.
            label_filename (str): File to save labels.
            csv_filename (str, optional): CSV file to save human-readable states.

        Returns:
            bool: True if successful, False otherwise.
        """
        if not self.states:
            print("No states to save.")
            return False
        
        try:
            # Convert states to array
            states_array = np.array([[state[key] for key in self.metric_keys] for state in self.states])
            
            # Save numpy arrays
            np.save(filename, states_array)
            np.save(label_filename, np.array(self.labels))
            
            # Save CSV if requested
            if csv_filename:
                df = pd.DataFrame(self.states)
                df.to_csv(csv_filename, index=False)
            
            print(f"Saved {len(self.states)} states to {filename} and {label_filename}")
            return True
        
        except Exception as e:
            print(f"Error saving states: {e}")
            return False

    def load_states(self, filename="environment_states.npy", label_filename="labels.npy"):
        """
        Load states and labels from files.

        Args:
            filename (str): File to load states from.
            label_filename (str): File to load labels from.

        Returns:
            tuple: (states_array, labels) or (None, None) if error.
        """
        try:
            if not os.path.exists(filename):
                print(f"States file {filename} does not exist.")
                return None, None
            
            # Load numpy arrays
            states_array = np.load(filename)
            labels = np.load(label_filename, allow_pickle=True) if os.path.exists(label_filename) else None
            
            # Recreate state dictionaries
            self.states = []
            for state_row in states_array:
                state_dict = {key: float(value) for key, value in zip(self.metric_keys, state_row)}
                state_dict['timestamp'] = time.time()
                self.states.append(state_dict)
            
            self.labels = list(labels) if labels is not None else []
            
            print(f"Loaded {len(self.states)} states from {filename}")
            return states_array, labels
        
        except Exception as e:
            print(f"Error loading states: {e}")
            return None, None
