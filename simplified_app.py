import streamlit as st
import time
import os
import json
from datetime import datetime, timedelta
import logging
from collections import deque

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("dashboard")

# Page configuration
st.set_page_config(
    page_title="AWS Chaos Engineering Dashboard",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Create placeholder methods for mock functionality
def dashboard_header():
    """Create a header for the dashboard."""
    st.markdown(
        """
        <style>
        .header {
            padding: 1rem;
            text-align: center;
            color: white;
            background-color: #4B0082;
            border-radius: 5px;
            margin-bottom: 1rem;
        }
        </style>
        <div class="header">
            <h1>AWS Chaos Engineering Dashboard</h1>
            <p>Monitor, Detect, and Remediate Infrastructure Vulnerabilities</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

def setup_localstack():
    """Mock function to simulate LocalStack status"""
    return True

def plot_service_health(metrics):
    """Mock function for service health visualization"""
    st.info("Service health visualization would appear here in the full version.")
    # Return a mock metrics display as table
    if metrics:
        st.write("Sample metrics:")
        # Sample metrics to display as JSON
        mock_view = {k: metrics[k] for k in list(metrics.keys())[:5]} if metrics else {}
        st.json(mock_view)

# Session state initialization
if 'metrics_history' not in st.session_state:
    st.session_state.metrics_history = {
        'ec2_cpu_avg': deque(maxlen=100),
        'rds_cpu': deque(maxlen=100),
        'lambda_errors': deque(maxlen=100),
        'elb_latency': deque(maxlen=100),
        'anomaly_score': deque(maxlen=100)
    }

if 'simulation_running' not in st.session_state:
    st.session_state.simulation_running = False

if 'current_state' not in st.session_state:
    st.session_state.current_state = None

if 'approval_requested' not in st.session_state:
    st.session_state.approval_requested = False

if 'chaos_actions' not in st.session_state:
    st.session_state.chaos_actions = []

if 'remediation_actions' not in st.session_state:
    st.session_state.remediation_actions = []

# Mock StateCollector
class MockStateCollector:
    def __init__(self):
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
        
    def collect_state(self, scenario=None):
        """Generate a synthetic state"""
        import random
        
        # Create a sample state dictionary with random values
        state = {}
        for key in self.metric_keys:
            # Generate reasonable sample values for each metric
            if 'count' in key:
                state[key] = random.randint(1, 10)
            elif 'cpu' in key:
                state[key] = random.uniform(10.0, 80.0)
            elif 'errors' in key or 'findings' in key:
                state[key] = random.randint(0, 5)
            elif 'latency' in key:
                state[key] = random.uniform(0.01, 1.0)
            else:
                state[key] = random.uniform(1.0, 100.0)
                
        return state

# Mock Agent Environment
class MockEnvironment:
    def __init__(self):
        self.model = None
        self.predictive_model = None
        
    def select_action(self, state):
        """Mock action selection"""
        class MockAction:
            def item(self):
                import random
                return random.randint(0, 10)
        return MockAction()
        
    def get_action_description(self, action_id):
        """Return a description for a given action ID"""
        actions = {
            0: "EC2 instance termination",
            1: "RDS CPU stress",
            2: "API throttling",
            3: "Network latency injection",
            4: "Lambda concurrency limitation",
            5: "S3 access throttling",
            6: "Security group rule modification",
            7: "Memory exhaustion",
            8: "Disk space filling",
            9: "Database connection flooding",
            10: "Route table modification"
        }
        return actions.get(action_id, f"Unknown action {action_id}")
        
    def reset(self):
        """Reset the environment state"""
        return [[0.5] * 25] * 5  # Return a simple 5x25 state
        
    def step(self, action):
        """Take a step in the environment"""
        import random
        next_state = [[random.random() for _ in range(25)] for _ in range(5)]
        reward = random.uniform(-1.0, 1.0)
        done = random.random() > 0.95  # 5% chance of ending
        info = {'anomaly_score': random.uniform(0.0, 0.5), 'anomaly_after': random.uniform(0.0, 0.3)}
        return next_state, reward, done, info

# Mock loading functions
def load_predictive_model():
    return None

def load_agents():
    return MockEnvironment(), MockEnvironment()

def check_required_files():
    return True

def provision_localstack_resources():
    return {
        "ec2_instances": ["i-mock1", "i-mock2"],
        "s3_bucket": "mock-bucket",
        "lambda_function": "mock-function"
    }

# Dashboard page
def display_dashboard():
    st.header("Infrastructure Dashboard")
    
    # System status cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.info("**LocalStack Status**: Running")
        
    with col2:
        st.info("**Anomaly Model**: Not Loaded")
        
    with col3:
        st.info("**Chaos Agent**: Not Trained")
        
    with col4:
        st.info("**Remediation Agent**: Not Trained")
    
    # Generate current state if none exists
    if st.session_state.current_state is None:
        collector = MockStateCollector()
        state = collector.collect_state(scenario='normal')
        st.session_state.current_state = state
    
    # Service health gauges
    st.subheader("Service Health")
    plot_service_health(st.session_state.current_state)
    
    # Add refresh button
    if st.button("Refresh Metrics"):
        collector = MockStateCollector()
        state = collector.collect_state()
        st.session_state.current_state = state
        
        # Update metrics history
        for key in st.session_state.metrics_history:
            if key in state:
                st.session_state.metrics_history[key].append(state[key])
            elif key == 'anomaly_score':
                # Generate sample anomaly score
                import random
                st.session_state.metrics_history[key].append(random.uniform(0.01, 0.2))
        
        st.rerun()
    
    # Live metrics chart
    st.subheader("Live Metrics")
    
    # Convert deques to lists for plotting
    history_dict = {k: list(v) for k, v in st.session_state.metrics_history.items()}
    if any(len(v) > 0 for v in history_dict.values()):
        st.line_chart(history_dict)
    else:
        st.info("No metrics data available yet. Click 'Refresh Metrics' to collect data.")
    
    # Raw metrics
    with st.expander("Current Metrics"):
        if st.session_state.current_state:
            st.json(st.session_state.current_state)

# Chaos simulation page
def display_chaos_simulation():
    st.header("Chaos Simulation")
    
    # Simulation control
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Simulation Control")
        
        # Configuration parameters
        num_actions = st.slider("Number of Chaos Actions", min_value=1, max_value=10, value=3)
        simulation_speed = st.select_slider(
            "Simulation Speed",
            options=["Very Slow", "Slow", "Medium", "Fast", "Very Fast"],
            value="Medium"
        )
        
        # Map speed to delay
        speed_map = {
            "Very Slow": 10.0, 
            "Slow": 5.0, 
            "Medium": 2.0, 
            "Fast": 1.0, 
            "Very Fast": 0.1
        }
        delay = speed_map[simulation_speed]
        
        # Approval workflow
        if not st.session_state.approval_requested:
            if st.button("Request Simulation Approval"):
                st.session_state.approval_requested = True
                st.success("Approval requested. Please confirm to proceed.")
                st.rerun()
    
    with col2:
        st.subheader("Status")
        if st.session_state.simulation_running:
            st.error("⚠️ Simulation In Progress")
        elif st.session_state.approval_requested:
            st.warning("⏳ Approval Pending")
        else:
            st.success("✅ Ready to Run")
    
    # Approval confirmation
    if st.session_state.approval_requested and not st.session_state.simulation_running:
        st.info("⚠️ Chaos experiments can disrupt systems. Confirm to proceed.")
        
        confirm_col1, confirm_col2 = st.columns(2)
        
        with confirm_col1:
            if st.button("✅ Approve Simulation"):
                st.session_state.simulation_running = True
                st.rerun()
        
        with confirm_col2:
            if st.button("❌ Deny Simulation"):
                st.session_state.approval_requested = False
                st.rerun()
    
    # Run simulation if approved
    if st.session_state.simulation_running:
        st.subheader("Simulation Progress")
        progress_bar = st.progress(0)
        
        # Load environments
        chaos_env, remediation_env = load_agents()
        
        # Initialize simulation state
        if 'simulation_state' not in st.session_state:
            st.session_state.simulation_state = chaos_env.reset()
            st.session_state.chaos_actions = []
            st.session_state.remediation_actions = []
            st.session_state.current_step = 0
        
        # Status display
        status_container = st.empty()
        metrics_container = st.empty()
        chart_container = st.empty()
        
        # Simulation loop
        try:
            for step in range(st.session_state.current_step, num_actions):
                st.session_state.current_step = step
                progress_bar.progress((step + 1) / num_actions)
                
                # Select and apply chaos action
                chaos_action = chaos_env.select_action(st.session_state.simulation_state)
                action_id = chaos_action.item()
                action_description = chaos_env.get_action_description(action_id)
                
                status_container.info(f"Step {step+1}/{num_actions}: Executing {action_description}")
                
                # Apply chaos action
                next_state, chaos_reward, chaos_done, chaos_info = chaos_env.step(action_id)
                
                # Record action
                st.session_state.chaos_actions.append({
                    'step': step,
                    'action': action_id,
                    'description': action_description,
                    'reward': chaos_reward,
                    'anomaly_score': chaos_info.get('anomaly_score', 0)
                })
                
                # Display state metrics
                metrics_container.write({
                    'Anomaly Score': chaos_info.get('anomaly_score', 0),
                    'Chaos Reward': chaos_reward
                })
                
                # Check for anomaly and apply remediation if needed
                import random
                anomaly_score = random.uniform(0.0, 0.3)
                
                if anomaly_score > 0.1:  # Threshold for remediation
                    status_container.warning(f"Anomaly detected (score: {anomaly_score:.4f}). Applying remediation...")
                    
                    # Select and apply remediation action
                    remediation_action = remediation_env.select_action(next_state)
                    remediation_id = remediation_action.item()
                    remediation_description = remediation_env.get_action_description(remediation_id)
                    
                    # Apply remediation
                    remediated_state, remediation_reward, remediation_done, remediation_info = remediation_env.step(remediation_id)
                    
                    # Record remediation action
                    st.session_state.remediation_actions.append({
                        'step': step,
                        'action': remediation_id,
                        'description': remediation_description,
                        'reward': remediation_reward,
                        'anomaly_before': anomaly_score,
                        'anomaly_after': remediation_info.get('anomaly_after', 0)
                    })
                    
                    status_container.success(f"Applied remediation: {remediation_description}")
                    st.session_state.simulation_state = remediated_state
                else:
                    st.session_state.simulation_state = next_state
                
                # Delay for visualization
                time.sleep(delay)
                
                if chaos_done:
                    status_container.warning("Simulation ended early due to critical failure.")
                    break
            
            # Simulation completed
            progress_bar.progress(1.0)
            status_container.success("Simulation completed!")
            
            # Reset simulation state
            st.session_state.simulation_running = False
            st.session_state.approval_requested = False
            if 'simulation_state' in st.session_state:
                del st.session_state.simulation_state
            if 'current_step' in st.session_state:
                del st.session_state.current_step
            
            st.rerun()
        
        except Exception as e:
            st.error(f"Simulation error: {str(e)}")
            st.session_state.simulation_running = False
            st.session_state.approval_requested = False

# Anomaly detection page
def display_anomaly_detection():
    st.header("Anomaly Detection")
    
    st.info("This page would display anomaly detection capabilities, including model configuration and real-time alerts.")
    
    # Add sample content
    st.subheader("Anomaly Detection Model")
    st.write("The system uses an LSTM Autoencoder to detect anomalies in AWS infrastructure metrics.")
    
    # Sample configuration
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Model Configuration**")
        st.code("""
        model = LSTMAutoencoder(
            timesteps=5,
            features=25,
            hidden_size=64
        )
        """)
    
    with col2:
        st.write("**Detection Threshold**")
        threshold = st.slider("Anomaly Threshold", min_value=0.01, max_value=0.5, value=0.1, step=0.01)
        st.write(f"Current threshold: {threshold} (higher = fewer alerts)")
    
    # Sample anomaly chart
    st.subheader("Sample Anomaly Timeline")
    
    # Generate mock anomaly data
    import random
    from datetime import datetime, timedelta
    dates = [datetime.now() - timedelta(hours=i) for i in range(48, 0, -1)]
    anomaly_scores = [random.uniform(0.01, 0.08) for _ in range(40)] + [random.uniform(0.15, 0.3) for _ in range(8)]
    
    # Create a simple chart using st.line_chart
    chart_data = {"time": dates, "anomaly_score": anomaly_scores}
    
    # Add horizontal line for threshold
    st.line_chart({"anomaly_score": anomaly_scores})
    st.write(f"The red points indicate anomaly scores above the threshold of {threshold}")

# Model training page
def display_model_training():
    import random
    from datetime import datetime, timedelta
    
    st.header("Model Training")
    
    st.info("This page would allow you to train and evaluate machine learning models for anomaly detection and remediation.")
    
    # Model selection
    model_type = st.selectbox(
        "Select Model Type",
        ["LSTM Autoencoder (Anomaly Detection)", "RL Agent (Chaos)", "RL Agent (Remediation)"]
    )
    
    # Training parameters in session state to persist values
    if 'training_params' not in st.session_state:
        st.session_state.training_params = {
            'epochs': 100,
            'batch_size': 32,
            'learning_rate_lstm': 0.005,
            'total_timesteps': 50000,
            'learning_rate_rl': 0.0001,
            'use_existing': True,
            'num_samples': 5000,
            'anomaly_prob': 0.3,
            'use_local': True,
            'exploration_rate': 0.2
        }
    
    # Training parameters
    st.subheader("Training Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if model_type == "LSTM Autoencoder (Anomaly Detection)":
            st.session_state.training_params['epochs'] = st.slider(
                "Training Epochs", 
                min_value=10, 
                max_value=500, 
                value=st.session_state.training_params['epochs'], 
                step=10
            )
            st.session_state.training_params['batch_size'] = st.slider(
                "Batch Size", 
                min_value=8, 
                max_value=128, 
                value=st.session_state.training_params['batch_size'], 
                step=8
            )
            st.session_state.training_params['learning_rate_lstm'] = st.select_slider(
                "Learning Rate",
                options=[0.001, 0.005, 0.01, 0.05, 0.1],
                value=st.session_state.training_params['learning_rate_lstm']
            )
        else:  # RL Agents
            st.session_state.training_params['total_timesteps'] = st.slider(
                "Total Timesteps", 
                min_value=1000, 
                max_value=100000, 
                value=st.session_state.training_params['total_timesteps'], 
                step=1000
            )
            st.session_state.training_params['learning_rate_rl'] = st.select_slider(
                "Learning Rate",
                options=[0.0001, 0.0005, 0.001, 0.005],
                value=st.session_state.training_params['learning_rate_rl']
            )
    
    with col2:
        st.write("**Data Configuration**")
        if model_type == "LSTM Autoencoder (Anomaly Detection)":
            st.session_state.training_params['use_existing'] = st.checkbox(
                "Use existing data", 
                value=st.session_state.training_params['use_existing']
            )
            if not st.session_state.training_params['use_existing']:
                st.session_state.training_params['num_samples'] = st.slider(
                    "Generate samples", 
                    min_value=1000, 
                    max_value=10000, 
                    value=st.session_state.training_params['num_samples'], 
                    step=1000
                )
                st.session_state.training_params['anomaly_prob'] = st.slider(
                    "Anomaly probability", 
                    min_value=0.1, 
                    max_value=0.5, 
                    value=st.session_state.training_params['anomaly_prob'], 
                    step=0.05
                )
        else:
            st.session_state.training_params['use_local'] = st.checkbox(
                "Use LocalStack for training", 
                value=st.session_state.training_params['use_local']
            )
            st.session_state.training_params['exploration_rate'] = st.slider(
                "Exploration rate", 
                min_value=0.1, 
                max_value=0.5, 
                value=st.session_state.training_params['exploration_rate'], 
                step=0.05
            )
    
    # Container for training logs
    training_log_container = st.empty()
    
    # Training button
    if st.button("Start Training"):
        # Create a container for training logs
        with st.expander("Training Logs", expanded=True):
            log_output = st.empty()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Initialize log data
            logs = []
            
            # Simulate training process using the actual parameters provided
            # Calculate total iterations based on parameters
            if model_type == "LSTM Autoencoder (Anomaly Detection)":
                total_iters = min(st.session_state.training_params['epochs'], 100)  # Limit to 100 for demo
                batch_size = st.session_state.training_params['batch_size']
                learning_rate = st.session_state.training_params['learning_rate_lstm']
                
                # Display configuration being used
                log_output.info(f"Starting training with parameters: epochs={total_iters}, batch_size={batch_size}, learning_rate={learning_rate}")
                if st.session_state.training_params['use_existing']:
                    log_output.info("Using existing dataset for training")
                else:
                    sample_count = st.session_state.training_params['num_samples']
                    anomaly_prob = st.session_state.training_params['anomaly_prob']
                    log_output.info(f"Generating {sample_count} samples with anomaly probability {anomaly_prob}")
            else:
                # Limit to 100 iterations for demo while respecting the timestep scale
                total_iters = min(st.session_state.training_params['total_timesteps'] // 500, 100)
                learning_rate = st.session_state.training_params['learning_rate_rl']
                exploration_rate = st.session_state.training_params['exploration_rate']
                is_chaos = model_type == "RL Agent (Chaos)"
                
                # Display configuration being used
                log_output.info(f"Starting {model_type} training with parameters:")
                log_output.info(f"Total timesteps: {st.session_state.training_params['total_timesteps']}")
                log_output.info(f"Learning rate: {learning_rate}")
                log_output.info(f"Exploration rate: {exploration_rate}")
                if st.session_state.training_params['use_local']:
                    log_output.info("Using LocalStack for environment simulation")
            
            # Initial values for metrics
            best_loss = float('inf')
            best_reward = float('-inf') if model_type == "RL Agent (Chaos)" else float('-inf')
            anomaly_scores = []
            rewards = []
            
            # Progress tracking
            for i in range(total_iters + 1):
                # Update progress bar
                progress = i / total_iters
                progress_bar.progress(progress)
                
                # Generate log entry
                timestamp = datetime.now().strftime("%H:%M:%S")
                
                if model_type == "LSTM Autoencoder (Anomaly Detection)":
                    # LSTM Autoencoder training - goal is to minimize reconstruction error
                    epoch = i
                    max_epochs = total_iters
                    
                    # Simulate batch training
                    batch_losses = []
                    for b in range(5):  # Simulate 5 batches per epoch
                        batch_loss = max(0.01, 1.0 - (i/(total_iters * 0.8)) + random.uniform(-0.05, 0.05))
                        batch_losses.append(batch_loss)
                    
                    # Overall epoch metrics
                    loss = sum(batch_losses) / len(batch_losses)
                    val_loss = loss * (1 + random.uniform(-0.1, 0.1))
                    
                    # Track best model
                    if val_loss < best_loss:
                        best_loss = val_loss
                        log_entry = f"{timestamp} - Epoch {epoch}/{max_epochs} - loss: {loss:.4f} - val_loss: {val_loss:.4f} - ✓ New best model saved"
                    else:
                        log_entry = f"{timestamp} - Epoch {epoch}/{max_epochs} - loss: {loss:.4f} - val_loss: {val_loss:.4f}"
                    
                    status_text.text(f"Training epoch {epoch} of {max_epochs}, loss: {loss:.4f}")
                else:
                    # RL Agent training
                    timestep = i * 500
                    max_timesteps = st.session_state.training_params['total_timesteps']
                    
                    # Get exploration rate from parameters
                    exploration_rate = st.session_state.training_params['exploration_rate']
                    
                    # Different reward functions for chaos vs remediation
                    if model_type == "RL Agent (Chaos)":
                        # For chaos: Higher anomaly score = better reward (maximizing disruption)
                        anomaly_score = min(0.8, (i/total_iters) * exploration_rate + random.uniform(-0.05, 0.05))
                        # Reward increases as anomaly score increases
                        reward = anomaly_score * 10
                        # Occasional failed attempts
                        if random.random() < 0.1:
                            reward = -2.0  # Failed attempts get negative rewards
                            log_entry = f"{timestamp} - Timestep {timestep}/{max_timesteps} - anomaly: {anomaly_score:.2f} - reward: {reward:.2f} - Action failed!"
                        else:
                            log_entry = f"{timestamp} - Timestep {timestep}/{max_timesteps} - anomaly: {anomaly_score:.2f} - reward: {reward:.2f}"
                    else:  # Remediation
                        # For remediation: Lower anomaly score = better reward (fixing issues)
                        # Start with high anomaly scores that get reduced over time
                        initial_anomaly = 0.7 - (0.3 * random.random())
                        anomaly_score = max(0.05, initial_anomaly - (i/total_iters) * exploration_rate)
                        # Reward increases as anomaly score decreases
                        reward = (1 - anomaly_score) * 10
                        # Occasional failed attempts
                        if random.random() < 0.1:
                            reward = -2.0  # Failed attempts get negative rewards
                            log_entry = f"{timestamp} - Timestep {timestep}/{max_timesteps} - anomaly: {anomaly_score:.2f} - reward: {reward:.2f} - Remediation failed!"
                        else:
                            log_entry = f"{timestamp} - Timestep {timestep}/{max_timesteps} - anomaly: {anomaly_score:.2f} - reward: {reward:.2f}"
                    
                    # Track metrics
                    anomaly_scores.append(anomaly_score)
                    rewards.append(reward)
                    
                    # Track best model
                    if (model_type == "RL Agent (Chaos)" and reward > best_reward) or \
                       (model_type == "RL Agent (Remediation)" and reward > best_reward):
                        best_reward = reward
                        log_entry += " - ✓ New best model saved"
                    
                    status_text.text(f"Training timestep {timestep} of {max_timesteps}, reward: {reward:.2f}")
                
                logs.append(log_entry)
                
                # Keep only the last 20 logs to prevent UI slowdown
                if len(logs) > 20:
                    display_logs = [logs[0]] + ["..."] + logs[-19:]
                else:
                    display_logs = logs
                
                # Display logs
                log_output.code("\n".join(display_logs))
                
                # Add small delay to simulate training
                time.sleep(0.05)
                
            # At the end, show a summary of the training
            if model_type == "LSTM Autoencoder (Anomaly Detection)":
                log_output.success(f"Training complete! Best validation loss: {best_loss:.4f}")
            else:
                avg_reward = sum(rewards) / len(rewards) if rewards else 0
                log_output.success(f"Training complete! Best reward: {best_reward:.2f}, Average reward: {avg_reward:.2f}")
                
                # Display a trend chart of performance
                if len(rewards) > 5:
                    # Display training metrics chart outside the expander
                    st.subheader("Training Metrics Trend")
                    metrics_chart_data = {
                        "reward": rewards,
                        "anomaly_score": anomaly_scores
                    }
                    st.line_chart(metrics_chart_data)
            
            # Training complete
            status_text.success("Training complete!")
        
        # Show mock evaluation results
        st.subheader("Training Results")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Performance Metrics")
            if model_type == "LSTM Autoencoder (Anomaly Detection)":
                st.json({
                    "final_loss": 0.0342,
                    "val_loss": 0.0387,
                    "training_time": "1m 24s",
                    "anomaly_threshold": 0.1,
                    "evaluation": {
                        "accuracy": 0.92,
                        "precision": 0.89,
                        "recall": 0.86,
                        "f1_score": 0.87
                    }
                })
            else:
                st.json({
                    "mean_reward": 42.7,
                    "max_reward": 67.3,
                    "training_time": "4m 12s",
                    "successful_remediations": 89,
                    "evaluation": {
                        "average_return": 38.9,
                        "success_rate": 0.82
                    }
                })
        
        with col2:
            st.subheader("Training Configuration Used")
            if model_type == "LSTM Autoencoder (Anomaly Detection)":
                st.json({
                    "model_type": model_type,
                    "epochs": st.session_state.training_params['epochs'],
                    "batch_size": st.session_state.training_params['batch_size'],
                    "learning_rate": st.session_state.training_params['learning_rate_lstm'],
                    "use_existing_data": st.session_state.training_params['use_existing'],
                    "num_samples": st.session_state.training_params['num_samples'] if not st.session_state.training_params['use_existing'] else "N/A",
                    "anomaly_probability": st.session_state.training_params['anomaly_prob'] if not st.session_state.training_params['use_existing'] else "N/A"
                })
            else:
                st.json({
                    "model_type": model_type,
                    "total_timesteps": st.session_state.training_params['total_timesteps'],
                    "learning_rate": st.session_state.training_params['learning_rate_rl'],
                    "use_localstack": st.session_state.training_params['use_local'],
                    "exploration_rate": st.session_state.training_params['exploration_rate']
                })

# Logs and analysis page
def display_logs_analysis():
    from datetime import datetime, timedelta
    
    st.header("Logs & Analysis")
    
    st.info("This page would display logs and analysis of chaos experiments and remediation actions.")
    
    # Date range selection
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
    with col2:
        end_date = st.date_input("End Date", datetime.now())
    
    # Tabs for different log types
    tab1, tab2, tab3 = st.tabs(["Chaos Logs", "Remediation Logs", "Summary"])
    
    with tab1:
        st.subheader("Chaos Actions Log")
        
        # Sample chaos logs
        import random
        from datetime import datetime, timedelta
        
        # Generate sample logs
        logs = []
        actions = [
            "EC2 instance termination",
            "RDS CPU stress",
            "API throttling",
            "Network latency injection",
            "Lambda concurrency limitation"
        ]
        
        for i in range(10):
            timestamp = datetime.now() - timedelta(days=random.randint(0, 7), 
                                                 hours=random.randint(0, 23), 
                                                 minutes=random.randint(0, 59))
            action = random.choice(actions)
            anomaly_score = random.uniform(0.05, 0.3)
            reward = random.uniform(-1.0, 0.5)
            
            logs.append({
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "action": action,
                "anomaly_score": anomaly_score,
                "reward": reward
            })
        
        # Display logs
        logs = sorted(logs, key=lambda x: x["timestamp"], reverse=True)
        st.json(logs)
    
    with tab2:
        st.subheader("Remediation Actions Log")
        
        # Sample remediation logs
        remediation_logs = []
        remediation_actions = [
            "Restore EC2 instance",
            "Relieve RDS CPU stress",
            "Remove API throttling",
            "Remove network latency",
            "Increase Lambda concurrency"
        ]
        
        for i in range(5):
            timestamp = datetime.now() - timedelta(days=random.randint(0, 7), 
                                                 hours=random.randint(0, 23), 
                                                 minutes=random.randint(0, 59))
            action = random.choice(remediation_actions)
            anomaly_before = random.uniform(0.15, 0.4)
            anomaly_after = random.uniform(0.01, 0.1)
            
            remediation_logs.append({
                "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "action": action,
                "anomaly_before": anomaly_before,
                "anomaly_after": anomaly_after,
                "improvement": anomaly_before - anomaly_after
            })
        
        # Display logs
        remediation_logs = sorted(remediation_logs, key=lambda x: x["timestamp"], reverse=True)
        st.json(remediation_logs)
    
    with tab3:
        st.subheader("Experiment Summary")
        
        # Sample summary statistics
        st.json({
            "time_period": f"{start_date} to {end_date}",
            "total_experiments": 8,
            "total_chaos_actions": 47,
            "total_anomalies_detected": 23,
            "total_remediation_actions": 19,
            "successful_remediations": 17,
            "most_common_chaos_actions": [
                {"action": "API throttling", "count": 12},
                {"action": "Network latency injection", "count": 10},
                {"action": "EC2 instance termination", "count": 8}
            ],
            "most_effective_remediations": [
                {"action": "Remove API throttling", "avg_improvement": 0.18},
                {"action": "Restore EC2 instance", "avg_improvement": 0.15},
                {"action": "Remove network latency", "avg_improvement": 0.12}
            ],
            "average_detection_time": "18.3 seconds",
            "average_remediation_time": "42.7 seconds"
        })

# Main app layout
def main():
    # Display header
    dashboard_header()
    
    # Sidebar
    with st.sidebar:
        st.title("Control Panel")
        
        # App navigation
        page = st.radio("Navigation", [
            "Dashboard", 
            "Chaos Simulation", 
            "Anomaly Detection", 
            "Model Training", 
            "Logs & Analysis"
        ])
        
        st.divider()
        
        # Environment settings
        st.subheader("Environment")
        localstack_active = setup_localstack()
        
        if localstack_active:
            st.success("✅ LocalStack is running")
            if st.button("Provision AWS Resources"):
                with st.spinner("Provisioning resources in LocalStack..."):
                    resources = provision_localstack_resources()
                    st.json(resources)
        else:
            st.error("❌ LocalStack is not running")
            st.info("Please start LocalStack with: docker run -p 4566:4566 localstack/localstack")
        
        st.divider()
        
        # LocalStack info
        st.subheader("LocalStack Info")
        st.markdown("- **Endpoint**: http://localhost:4566")
        st.markdown("- **Region**: us-east-1")
        st.markdown("- **Access Key**: dummy")
        st.markdown("- **Secret Key**: dummy")
    
    # Main content based on selected page
    if page == "Dashboard":
        display_dashboard()
    elif page == "Chaos Simulation":
        display_chaos_simulation()
    elif page == "Anomaly Detection":
        display_anomaly_detection()
    elif page == "Model Training":
        display_model_training()
    elif page == "Logs & Analysis":
        display_logs_analysis()

if __name__ == "__main__":
    main()