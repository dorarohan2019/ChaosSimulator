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
    dates = [datetime.now() - timedelta(hours=i) for i in range(48, 0, -1)]
    anomaly_scores = [random.uniform(0.01, 0.08) for _ in range(40)] + [random.uniform(0.15, 0.3) for _ in range(8)]
    
    # Create a simple chart using st.line_chart
    chart_data = {"time": dates, "anomaly_score": anomaly_scores}
    
    # Add horizontal line for threshold
    st.line_chart({"anomaly_score": anomaly_scores})
    st.write(f"The red points indicate anomaly scores above the threshold of {threshold}")

# Model training page
def display_model_training():
    st.header("Model Training")
    
    st.info("This page would allow you to train and evaluate machine learning models for anomaly detection and remediation.")
    
    # Model selection
    model_type = st.selectbox(
        "Select Model Type",
        ["LSTM Autoencoder (Anomaly Detection)", "RL Agent (Chaos)", "RL Agent (Remediation)"]
    )
    
    # Training parameters
    st.subheader("Training Parameters")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if model_type == "LSTM Autoencoder (Anomaly Detection)":
            epochs = st.slider("Training Epochs", min_value=10, max_value=500, value=100, step=10)
            batch_size = st.slider("Batch Size", min_value=8, max_value=128, value=32, step=8)
            learning_rate = st.select_slider(
                "Learning Rate",
                options=[0.001, 0.005, 0.01, 0.05, 0.1],
                value=0.005
            )
        else:  # RL Agents
            total_timesteps = st.slider("Total Timesteps", min_value=1000, max_value=100000, value=50000, step=1000)
            learning_rate = st.select_slider(
                "Learning Rate",
                options=[0.0001, 0.0005, 0.001, 0.005],
                value=0.0001
            )
    
    with col2:
        st.write("**Data Configuration**")
        if model_type == "LSTM Autoencoder (Anomaly Detection)":
            use_existing = st.checkbox("Use existing data", value=True)
            if not use_existing:
                num_samples = st.slider("Generate samples", min_value=1000, max_value=10000, value=5000, step=1000)
                anomaly_prob = st.slider("Anomaly probability", min_value=0.1, max_value=0.5, value=0.3, step=0.05)
        else:
            use_local = st.checkbox("Use LocalStack for training", value=True)
            exploration_rate = st.slider("Exploration rate", min_value=0.1, max_value=0.5, value=0.2, step=0.05)
    
    # Training button
    if st.button("Start Training"):
        # Mock training progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i in range(101):
            # Update progress bar
            progress_bar.progress(i / 100)
            
            # Update status text (different based on model type)
            if model_type == "LSTM Autoencoder (Anomaly Detection)":
                status_text.text(f"Training epoch {i} of 100, loss: {1.0 - (i/150):.4f}")
            else:
                status_text.text(f"Training timestep {i*500} of 50000, reward: {i/50:.2f}")
            
            # Add small delay to simulate training
            time.sleep(0.05)
        
        # Training complete
        status_text.success("Training complete!")
        
        # Show mock evaluation results
        st.subheader("Training Results")
        
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

# Logs and analysis page
def display_logs_analysis():
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