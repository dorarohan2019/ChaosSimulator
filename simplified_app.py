import streamlit as st
import time
import os
import json
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from collections import deque
# Import infrastructure topology module
from infrastructure_topology import InfrastructureTopology, display_infrastructure_topology

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

# Initialize session state for model tracking
if 'model_statuses' not in st.session_state:
    st.session_state.model_statuses = {
        'anomaly_model': 'Not Loaded',
        'chaos_agent': 'Not Trained',
        'remediation_agent': 'Not Trained'
    }

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
def save_model(model_type, model_data):
    """
    Save a trained model to file
    
    Args:
        model_type (str): Type of model ('anomaly_model', 'chaos_agent', or 'remediation_agent')
        model_data (object): The model data to save
    """
    # Create models directory if it doesn't exist
    os.makedirs("models", exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"models/{model_type}_{timestamp}.pkl"
    
    try:
        # Save the model data
        import pickle
        with open(filename, 'wb') as f:
            pickle.dump(model_data, f)
        
        # Update latest model link
        latest_link = f"models/{model_type}_latest.pkl"
        if os.path.exists(latest_link):
            os.remove(latest_link)
        os.symlink(filename, latest_link)
        
        # Update session state
        st.session_state.model_statuses[model_type] = 'Trained'
        
        logger.info(f"Saved {model_type} to {filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to save {model_type}: {str(e)}")
        return False

def load_predictive_model():
    """Load the latest trained anomaly detection model"""
    try:
        latest_model_path = "models/anomaly_model_latest.pkl"
        if os.path.exists(latest_model_path):
            import pickle
            with open(latest_model_path, 'rb') as f:
                model = pickle.load(f)
            st.session_state.model_statuses['anomaly_model'] = 'Loaded'
            logger.info("Loaded anomaly detection model")
            return model
        else:
            logger.warning("No anomaly detection model found")
            return None
    except Exception as e:
        logger.error(f"Failed to load anomaly detection model: {str(e)}")
        return None

def load_agents():
    """Load the trained chaos and remediation agents"""
    chaos_env = MockEnvironment()
    remediation_env = MockEnvironment()
    
    try:
        # Try to load chaos agent
        chaos_path = "models/chaos_agent_latest.pkl"
        if os.path.exists(chaos_path):
            import pickle
            with open(chaos_path, 'rb') as f:
                chaos_model = pickle.load(f)
            chaos_env.model = chaos_model
            st.session_state.model_statuses['chaos_agent'] = 'Trained'
            logger.info("Loaded chaos agent model")
    except Exception as e:
        logger.error(f"Failed to load chaos agent: {str(e)}")
    
    try:
        # Try to load remediation agent
        remediation_path = "models/remediation_agent_latest.pkl"
        if os.path.exists(remediation_path):
            import pickle
            with open(remediation_path, 'rb') as f:
                remediation_model = pickle.load(f)
            remediation_env.model = remediation_model
            st.session_state.model_statuses['remediation_agent'] = 'Trained'
            logger.info("Loaded remediation agent model")
    except Exception as e:
        logger.error(f"Failed to load remediation agent: {str(e)}")
    
    return chaos_env, remediation_env

def check_required_files():
    """Check if required files for simulation exist"""
    required_dirs = ['models']
    
    # Create required directories if they don't exist
    for directory in required_dirs:
        os.makedirs(directory, exist_ok=True)
    
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
        model_status = st.session_state.model_statuses['anomaly_model']
        if model_status == 'Not Loaded':
            st.info(f"**Anomaly Model**: {model_status}")
        else:
            st.success(f"**Anomaly Model**: {model_status}")
        
    with col3:
        agent_status = st.session_state.model_statuses['chaos_agent']
        if agent_status == 'Not Trained':
            st.info(f"**Chaos Agent**: {agent_status}")
        else:
            st.success(f"**Chaos Agent**: {agent_status}")
        
    with col4:
        agent_status = st.session_state.model_statuses['remediation_agent']
        if agent_status == 'Not Trained':
            st.info(f"**Remediation Agent**: {agent_status}")
        else:
            st.success(f"**Remediation Agent**: {agent_status}")
    
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
        
        # Mark agents as loaded/trained when simulation starts
        if st.session_state.model_statuses['chaos_agent'] == 'Not Trained':
            st.session_state.model_statuses['chaos_agent'] = 'Trained'
            
        if st.session_state.model_statuses['remediation_agent'] == 'Not Trained':
            st.session_state.model_statuses['remediation_agent'] = 'Trained'
        
        # Initialize simulation state
        if 'simulation_state' not in st.session_state:
            st.session_state.simulation_state = chaos_env.reset()
            st.session_state.chaos_actions = []
            st.session_state.remediation_actions = []
            st.session_state.current_step = 0
            
            # Initialize infrastructure topology
            if 'infra_topology' not in st.session_state:
                st.session_state.infra_topology = InfrastructureTopology()
        
        # Status display
        status_container = st.empty()
        metrics_container = st.empty()
        chart_container = st.empty()
        
        # Initialize metrics history for visualization
        if 'simulation_metrics' not in st.session_state:
            st.session_state.simulation_metrics = {
                'timestamps': [],
                'anomaly_score': [],
                'system_health': [],
                'cpu_utilization': [],
                'memory_usage': [],
                'network_latency': [],
                'api_error_rate': [],
                'service_availability': [],
                'action_type': [],
                'action_description': []
            }
            # Initialize empty lists for all metrics to avoid issues with "any(val != 0)"
            for key in st.session_state.simulation_metrics:
                st.session_state.simulation_metrics[key] = []
        elif st.session_state.simulation_running and 'clear_metrics' not in st.session_state:
            # Only clear metrics when first starting a simulation, not when returning to page
            st.session_state.clear_metrics = True
            # Clear previous metrics
            for key in st.session_state.simulation_metrics:
                st.session_state.simulation_metrics[key] = []
        
        # Create persistent chart containers if they don't exist
        if 'primary_metrics_chart' not in st.session_state:
            st.session_state.primary_metrics_chart = st.empty()
        if 'infra_metrics_chart' not in st.session_state:
            st.session_state.infra_metrics_chart = st.empty()
        
        # Prepare timeseries chart data function
        def update_metrics_chart():
            # Create a dataframe from the metrics
            import pandas as pd
            if len(st.session_state.simulation_metrics['timestamps']) > 0:
                df = pd.DataFrame(st.session_state.simulation_metrics)
                
                # Create separate dataframes for visualization
                # First chart: Primary metrics (anomaly score and system health)
                primary_metrics_df = df[['timestamps', 'anomaly_score', 'system_health']]
                primary_metrics_df = primary_metrics_df.set_index('timestamps')
                
                # Show the primary metrics chart in the same container
                with st.session_state.primary_metrics_chart.container():
                    st.subheader("System Status Metrics")
                    st.line_chart(primary_metrics_df)
                
                # Second chart: Infrastructure metrics
                # Filter out columns that don't have data yet
                infra_columns = ['timestamps']
                for col in ['cpu_utilization', 'memory_usage', 'network_latency', 'api_error_rate', 'service_availability']:
                    if any(val != 0 for val in df[col]) or len(df[col]) == 0:
                        infra_columns.append(col)
                
                if len(infra_columns) > 1:  # If we have any data beyond timestamps
                    infra_metrics_df = df[infra_columns]
                    infra_metrics_df = infra_metrics_df.set_index('timestamps')
                    
                    # Show the infrastructure metrics chart in the same container
                    with st.session_state.infra_metrics_chart.container():
                        st.subheader("Infrastructure Metrics")
                        st.line_chart(infra_metrics_df)
                
                # Get the most recent action details
                latest_idx = len(df) - 1
                latest_action_type = df.iloc[latest_idx]['action_type']
                latest_action_desc = df.iloc[latest_idx]['action_description']
                
                # Single persistent infrastructure topology visualization
                if 'topology_container' not in st.session_state:
                    st.session_state.topology_container = st.empty()
                
                # Update the topology based on the latest action
                if latest_action_type == "Chaos":
                    st.session_state.infra_topology.apply_chaos_action(latest_action_desc)
                elif latest_action_type == "Remediation":
                    st.session_state.infra_topology.apply_remediation_action(latest_action_desc)
                    
                # Display the updated infrastructure visualization in the same container
                with st.session_state.topology_container.container():
                    display_infrastructure_topology(st.session_state.infra_topology, width=800, height=500, show_controls=False)
                
                # Show action log below chart
                actions_df = df[['timestamps', 'action_type', 'action_description']]
                actions_df = actions_df.sort_values('timestamps', ascending=False)
                
                # Format the action log as a table
                st.subheader("Action Timeline")
                action_table = ""
                for idx, row in actions_df.iterrows():
                    time_str = row['timestamps'].strftime("%H:%M:%S")
                    action_type = row['action_type']
                    action_desc = row['action_description']
                    
                    # Icon based on action type
                    icon = "🔴" if action_type == "Chaos" else "🟢"
                    action_table += f"**{time_str}** {icon} **{action_type}**: {action_desc}\n\n"
                
                st.markdown(action_table)
        
        # Simulation loop
        try:
            for step in range(st.session_state.current_step, num_actions):
                st.session_state.current_step = step
                progress_bar.progress((step + 1) / (num_actions * 2))  # Account for both chaos and remediation steps
                
                # Step 1: Select and apply chaos action
                chaos_action = chaos_env.select_action(st.session_state.simulation_state)
                action_id = chaos_action.item()
                action_description = chaos_env.get_action_description(action_id)
                
                status_container.info(f"Step {step+1}.A: Executing chaos action: {action_description}")
                
                # Apply chaos action
                next_state, chaos_reward, chaos_done, chaos_info = chaos_env.step(action_id)
                
                # Generate metrics for visualization
                import random
                from datetime import datetime
                anomaly_score = chaos_info.get('anomaly_score', random.uniform(0.1, 0.4))
                system_health = max(0, 1.0 - anomaly_score)  # Health decreases as anomaly score increases
                
                # Generate infrastructure metrics based on chaos action
                cpu_util = random.uniform(60, 95) if "CPU" in action_description else random.uniform(30, 70)
                memory_usage = random.uniform(70, 90) if "memory" in action_description else random.uniform(40, 75)
                network_latency = random.uniform(500, 2000) if "network" in action_description else random.uniform(50, 200) 
                api_error_rate = random.uniform(0.1, 0.4) if "API" in action_description else random.uniform(0.01, 0.1)
                availability = max(0.5, 1.0 - anomaly_score)  # Service availability drops with high anomaly score
                
                # Record metrics
                st.session_state.simulation_metrics['timestamps'].append(datetime.now())
                st.session_state.simulation_metrics['anomaly_score'].append(anomaly_score)
                st.session_state.simulation_metrics['system_health'].append(system_health)
                st.session_state.simulation_metrics['cpu_utilization'].append(cpu_util)
                st.session_state.simulation_metrics['memory_usage'].append(memory_usage)
                st.session_state.simulation_metrics['network_latency'].append(network_latency)
                st.session_state.simulation_metrics['api_error_rate'].append(api_error_rate) 
                st.session_state.simulation_metrics['service_availability'].append(availability)
                st.session_state.simulation_metrics['action_type'].append("Chaos")
                st.session_state.simulation_metrics['action_description'].append(action_description)
                
                # Record action
                st.session_state.chaos_actions.append({
                    'step': step,
                    'action': action_id,
                    'description': action_description,
                    'reward': chaos_reward,
                    'anomaly_score': anomaly_score,
                    'timestamp': datetime.now()
                })
                
                # Display state metrics
                metrics_container.write({
                    'Anomaly Score': f"{anomaly_score:.4f}",
                    'System Health': f"{system_health:.4f}",
                    'Chaos Reward': f"{chaos_reward:.4f}"
                })
                
                # Update visualization
                update_metrics_chart()
                
                # Delay for visualization
                time.sleep(delay)
                
                if chaos_done:
                    status_container.warning("Simulation ended early due to critical failure.")
                    break
                
                # Step 2: Apply remediation action
                progress_bar.progress((step + 1.5) / (num_actions * 2))  # Halfway between steps
                
                # Select and apply remediation action
                remediation_action = remediation_env.select_action(next_state)
                remediation_id = remediation_action.item()
                remediation_description = remediation_env.get_action_description(remediation_id)
                
                status_container.warning(f"Step {step+1}.B: Applying remediation: {remediation_description}")
                
                # Apply remediation
                remediated_state, remediation_reward, remediation_done, remediation_info = remediation_env.step(remediation_id)
                
                # Generate metrics after remediation
                anomaly_after = remediation_info.get('anomaly_after', max(0.01, anomaly_score - random.uniform(0.05, 0.2)))
                system_health_after = max(0, 1.0 - anomaly_after)
                
                # Improve infrastructure metrics based on remediation action
                # CPU utilization improves
                cpu_util_after = max(20, st.session_state.simulation_metrics['cpu_utilization'][-1] * 0.7) if "CPU" in remediation_description else st.session_state.simulation_metrics['cpu_utilization'][-1] * 0.9
                
                # Memory usage improves
                memory_usage_after = max(30, st.session_state.simulation_metrics['memory_usage'][-1] * 0.8) if "memory" in remediation_description else st.session_state.simulation_metrics['memory_usage'][-1] * 0.95
                
                # Network latency improves
                network_latency_after = max(20, st.session_state.simulation_metrics['network_latency'][-1] * 0.3) if "network" in remediation_description else st.session_state.simulation_metrics['network_latency'][-1] * 0.7
                
                # API error rate improves
                api_error_rate_after = max(0.01, st.session_state.simulation_metrics['api_error_rate'][-1] * 0.4) if "API" in remediation_description else st.session_state.simulation_metrics['api_error_rate'][-1] * 0.8
                
                # Service availability improves
                availability_after = min(0.99, system_health_after + random.uniform(0.05, 0.15))
                
                # Record metrics after remediation
                st.session_state.simulation_metrics['timestamps'].append(datetime.now())
                st.session_state.simulation_metrics['anomaly_score'].append(anomaly_after)
                st.session_state.simulation_metrics['system_health'].append(system_health_after)
                st.session_state.simulation_metrics['cpu_utilization'].append(cpu_util_after)
                st.session_state.simulation_metrics['memory_usage'].append(memory_usage_after)
                st.session_state.simulation_metrics['network_latency'].append(network_latency_after)
                st.session_state.simulation_metrics['api_error_rate'].append(api_error_rate_after)
                st.session_state.simulation_metrics['service_availability'].append(availability_after)
                st.session_state.simulation_metrics['action_type'].append("Remediation")
                st.session_state.simulation_metrics['action_description'].append(remediation_description)
                
                # Record remediation action
                st.session_state.remediation_actions.append({
                    'step': step,
                    'action': remediation_id,
                    'description': remediation_description,
                    'reward': remediation_reward,
                    'anomaly_before': anomaly_score,
                    'anomaly_after': anomaly_after,
                    'improvement': anomaly_score - anomaly_after,
                    'timestamp': datetime.now()
                })
                
                # Display updated metrics
                metrics_container.write({
                    'Anomaly Before': f"{anomaly_score:.4f}",
                    'Anomaly After': f"{anomaly_after:.4f}",
                    'System Health': f"{system_health_after:.4f}",
                    'Improvement': f"{anomaly_score - anomaly_after:.4f}"
                })
                
                # Update visualization
                update_metrics_chart()
                
                # Set the state for next iteration
                st.session_state.simulation_state = remediated_state
                
                # Delay for visualization
                time.sleep(delay)
                
                if remediation_done:
                    status_container.warning("Remediation completed the simulation early.")
                    break
            
            # Simulation completed
            progress_bar.progress(1.0)
            status_container.success("Simulation completed!")
            
            # Reset only the simulation running flag but keep metrics and other data
            st.session_state.simulation_running = False
            st.session_state.approval_requested = False
            st.session_state.simulation_complete = True
            if 'simulation_state' in st.session_state:
                del st.session_state.simulation_state
            if 'current_step' in st.session_state:
                del st.session_state.current_step
            
            # Do not rerun to keep the visualization displayed
            # Display summary of simulation results
            st.subheader("Simulation Results Summary")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("### Chaos Actions")
                st.write(f"**Total chaos actions:** {len(st.session_state.chaos_actions)}")
                st.write("**Average anomaly score:** {:.4f}".format(
                    sum(action['anomaly_score'] for action in st.session_state.chaos_actions) / 
                    max(1, len(st.session_state.chaos_actions))
                ))
            
            with col2:
                st.write("### Remediation Actions")
                st.write(f"**Total remediation actions:** {len(st.session_state.remediation_actions)}")
                if st.session_state.remediation_actions:
                    avg_improvement = sum(action['improvement'] for action in st.session_state.remediation_actions) / len(st.session_state.remediation_actions)
                    st.write(f"**Average improvement:** {avg_improvement:.4f}")
                    
                    # Calculate effectiveness percentage
                    effectiveness = sum(1 for action in st.session_state.remediation_actions 
                                      if action['anomaly_after'] < action['anomaly_before']) / len(st.session_state.remediation_actions) * 100
                    st.write(f"**Remediation effectiveness:** {effectiveness:.1f}%")
            
            # Show infrastructure topology with animation controls when simulation is complete
            if 'infra_topology' in st.session_state and 'simulation_complete' in st.session_state:
                st.subheader("Infrastructure Topology Animation")
                st.write("Watch how AWS infrastructure changed during the simulation:")
                display_infrastructure_topology(st.session_state.infra_topology, width=800, height=500, show_controls=True)
        
        except Exception as e:
            st.error(f"Simulation error: {str(e)}")
            st.session_state.simulation_running = False
            st.session_state.approval_requested = False

# Anomaly detection page
def display_anomaly_detection():
    st.header("Anomaly Detection")
    
    # Update model status when accessing the anomaly detection page
    # This simulates loading the model when needed
    if st.session_state.model_statuses['anomaly_model'] == 'Not Loaded':
        st.session_state.model_statuses['anomaly_model'] = 'Loaded'
    
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
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    dates = [datetime.now() - timedelta(hours=i) for i in range(48, 0, -1)]
    anomaly_scores = [random.uniform(0.01, 0.08) for _ in range(40)] + [random.uniform(0.15, 0.3) for _ in range(8)]
    random.shuffle(anomaly_scores)  # Mix them up for a more realistic pattern
    
    # Create pandas DataFrame for plotting
    df = pd.DataFrame({
        "timestamp": dates,
        "anomaly_score": anomaly_scores
    })
    
    # Create two separate series for normal and anomaly points
    normal_points = df[df["anomaly_score"] <= threshold]
    anomaly_points = df[df["anomaly_score"] > threshold]
    
    # Display the threshold line
    st.line_chart({"anomaly_score": anomaly_scores, "threshold": [threshold] * len(dates)})
    
    # Create visualization to show points above and below threshold
    st.subheader("Anomaly Detection")
    
    # Create custom charts that works with available libraries
    col1, col2 = st.columns(2)
    
    with col1:
        # Normal points information
        st.markdown("### Normal Points")
        st.write(f"**Count:** {len(normal_points)} points")
        st.write("**Average score:** {:.4f}".format(normal_points["anomaly_score"].mean() if not normal_points.empty else 0))
        
        # Show sample normal points
        if not normal_points.empty:
            st.write("**Sample normal points:**")
            sample_normal = normal_points.sample(min(5, len(normal_points)))
            for idx, row in sample_normal.iterrows():
                score = row["anomaly_score"]
                time_str = row["timestamp"].strftime("%H:%M")
                st.write(f"• {time_str}: {score:.4f} ✓")
    
    with col2:
        # Anomaly points information
        st.markdown("### Anomaly Points")
        st.write(f"**Count:** {len(anomaly_points)} points")
        st.write("**Average score:** {:.4f}".format(anomaly_points["anomaly_score"].mean() if not anomaly_points.empty else 0))
        
        # Show sample anomaly points
        if not anomaly_points.empty:
            st.write("**Sample anomaly points:**")
            sample_anomalies = anomaly_points.sample(min(5, len(anomaly_points)))
            for idx, row in sample_anomalies.iterrows():
                score = row["anomaly_score"]
                time_str = row["timestamp"].strftime("%H:%M")
                st.write(f"• {time_str}: {score:.4f} ⚠️")
    
    # Create visual representation of anomaly distribution
    st.subheader("Score Distribution")
    
    # Use histogram with two colors
    bins = np.linspace(0, max(anomaly_scores) + 0.05, 20)
    hist_data = np.histogram(anomaly_scores, bins=bins)
    bin_edges = hist_data[1][:-1]  # Remove the last edge
    bin_heights = hist_data[0]
    bin_colors = ['blue' if edge <= threshold else 'red' for edge in bin_edges]
    
    # Convert to chart format
    chart_data = {f"bin_{i}": [height if bin_colors[i] == color else 0] 
                 for i, (height, color) in enumerate(zip(bin_heights, bin_colors)) 
                 for color in ['blue', 'red']}
    
    # Display chart
    st.bar_chart(chart_data)
    
    # Add clear legend
    st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 20px;">
        <div style="width: 20px; height: 20px; background-color: blue; margin-right: 10px;"></div>
        <div style="margin-right: 30px;">Normal (≤ {0})</div>
        <div style="width: 20px; height: 20px; background-color: red; margin-right: 10px;"></div>
        <div>Anomaly (> {0})</div>
    </div>
    """.format(threshold), unsafe_allow_html=True)
    
    st.write(f"The highlighted red values indicate anomaly scores above the threshold of {threshold:.4f}")

# Model training page
def display_model_training():
    import random
    import math
    import numpy as np
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
            'exploration_rate': 0.2,
            'is_validated': False
        }
    
    # Helper for real-time parameter feedback
    def get_parameter_assessment(param_name, param_value):
        """Generate real-time feedback for parameter values"""
        assessments = {
            'epochs': {
                'low': "Few epochs may lead to underfitting. Training will be quick but model might not learn patterns well.",
                'medium': "Good balance between training time and model performance.",
                'high': "Many epochs may lead to longer training time, but could improve accuracy. Watch for overfitting."
            },
            'batch_size': {
                'low': "Small batch size provides more stochastic gradient updates but may be slower and less stable.",
                'medium': "Good balance between training speed and gradient precision.",
                'high': "Large batch size speeds up training but may reduce model generalization ability."
            },
            'learning_rate_lstm': {
                'low': "Low learning rate ensures stable training but converges slowly.",
                'medium': "Balanced learning rate for good convergence speed.",
                'high': "High learning rate may converge quickly but risks overshooting the optimal solution."
            },
            'learning_rate_rl': {
                'low': "Low learning rate helps agent learn stable policies but requires more training steps.",
                'medium': "Balanced learning rate for good policy learning.",
                'high': "High learning rate allows faster exploration but may result in unstable policies."
            },
            'total_timesteps': {
                'low': "Few timesteps may not allow the agent to fully explore the environment.",
                'medium': "Sufficient timesteps for moderately complex environments.",
                'high': "Many timesteps allow thorough environment exploration but take longer to train."
            },
            'exploration_rate': {
                'low': "Low exploration rate favors exploitation over exploration, may miss optimal policies.",
                'medium': "Balanced exploration vs. exploitation trade-off.",
                'high': "High exploration rate encourages discovering diverse strategies but may be inefficient."
            },
            'anomaly_prob': {
                'low': "Few anomalies make detection harder but dataset more realistic.",
                'medium': "Balanced anomaly distribution for good training.",
                'high': "Many anomalies may make detection easier but less representative of real scenarios."
            },
            'num_samples': {
                'low': "Few samples may limit model's learning ability.",
                'medium': "Sufficient data for moderate complexity modeling.",
                'high': "Large dataset improves learning but increases training time."
            }
        }
        
        thresholds = {
            'epochs': [50, 200],
            'batch_size': [16, 64],
            'learning_rate_lstm': [0.001, 0.01],
            'learning_rate_rl': [0.0001, 0.001],
            'total_timesteps': [10000, 50000],
            'exploration_rate': [0.15, 0.3],
            'anomaly_prob': [0.15, 0.35],
            'num_samples': [2000, 8000]
        }
        
        if param_name in thresholds:
            low, high = thresholds[param_name]
            level = 'low' if param_value < low else 'high' if param_value > high else 'medium'
            return assessments[param_name][level]
        return ""
    
    # Generate impact prediction based on parameter combination
    def predict_training_impact(params, model_type):
        """Predict the impact of parameter combinations on training"""
        if model_type == "LSTM Autoencoder (Anomaly Detection)":
            # Key factors for LSTM: learning rate, epochs, batch size
            lr = params['learning_rate_lstm']
            epochs = params['epochs']
            batch = params['batch_size']
            
            # Calculate predicted training time (arbitrary formula for demo)
            est_time_mins = math.ceil((epochs * 5000) / (batch * 1000) * (1 + lr * 10))
            
            # Calculate predicted performance metrics
            est_accuracy = min(0.95, 0.75 + (epochs/500) * 0.1 + (lr/0.01) * 0.05)
            est_f1 = est_accuracy - random.uniform(0.02, 0.08)
            
            # Risk assessment
            overfitting_risk = "Low"
            if epochs > 200 and batch < 32:
                overfitting_risk = "Moderate"
            elif epochs > 300 and batch < 16:
                overfitting_risk = "High"
            
            # Generate recommendation
            recommendation = ""
            if epochs < 50:
                recommendation = "Consider increasing epochs for better learning."
            elif lr > 0.05:
                recommendation = "Consider reducing learning rate for more stable training."
            elif batch > 64 and epochs > 200:
                recommendation = "Large batch size with many epochs may lead to overfitting."
            else:
                recommendation = "Parameter configuration looks balanced."
                
            return {
                "est_training_time": f"{est_time_mins} minutes",
                "est_accuracy": f"{est_accuracy:.2f}",
                "est_f1_score": f"{est_f1:.2f}",
                "overfitting_risk": overfitting_risk,
                "recommendation": recommendation
            }
            
        else:  # RL Agents
            # Key factors: timesteps, learning rate, exploration rate
            timesteps = params['total_timesteps']
            lr = params['learning_rate_rl']
            exploration = params['exploration_rate']
            
            # Calculate predicted training time
            est_time_mins = math.ceil(timesteps / 12000)
            
            # Initialize risk variables to avoid "possibly unbound" errors
            instability_risk = "Low"
            inefficiency_risk = "Low"
            
            # Different metrics for chaos vs remediation
            if model_type == "RL Agent (Chaos)":
                # Chaos: higher exploration = better for finding disruptions
                est_success = min(0.9, 0.6 + (timesteps/100000) * 0.2 + exploration * 0.3)
                est_mean_reward = 30 + (timesteps/10000) * 5 + exploration * 40
                
                # Risk assessment
                instability_risk = "Low"
                if exploration > 0.4:
                    instability_risk = "Moderate"
                elif exploration > 0.45 and lr > 0.001:
                    instability_risk = "High"
                
                # Generate recommendation
                if timesteps < 10000:
                    recommendation = "Consider increasing timesteps for more thorough exploration."
                elif exploration < 0.15:
                    recommendation = "Consider increasing exploration rate to find more diverse disruptions."
                elif lr > 0.001 and exploration > 0.4:
                    recommendation = "High exploration with high learning rate may lead to unstable training."
                else:
                    recommendation = "Parameter configuration looks suitable for chaos agent."
                    
            else:  # Remediation
                # Remediation: lower exploration = better for focused remediation
                est_success = min(0.95, 0.65 + (timesteps/100000) * 0.25 + (0.5 - exploration) * 0.2)
                est_mean_reward = 35 + (timesteps/10000) * 6 + (0.5 - exploration) * 20
                
                # Risk assessment
                inefficiency_risk = "Low"
                if exploration < 0.15:
                    inefficiency_risk = "Moderate"
                elif exploration < 0.1 and timesteps < 20000:
                    inefficiency_risk = "High"
                
                # Generate recommendation
                if timesteps < 10000:
                    recommendation = "Consider increasing timesteps for more thorough remediation learning."
                elif exploration > 0.35:
                    recommendation = "Consider reducing exploration rate for more focused remediation."
                elif lr < 0.0001 and timesteps < 30000:
                    recommendation = "Low learning rate with few timesteps may result in slow convergence."
                else:
                    recommendation = "Parameter configuration looks suitable for remediation agent."
            
            return {
                "est_training_time": f"{est_time_mins} minutes",
                "est_success_rate": f"{est_success:.2f}",
                "est_mean_reward": f"{est_mean_reward:.1f}",
                "stability_risk": instability_risk if model_type == "RL Agent (Chaos)" else inefficiency_risk,
                "recommendation": recommendation
            }
    
    # Training parameters
    st.subheader("Training Parameters")
    
    # Add parameter validation toggle
    enable_validation = st.toggle("Enable Real-time Parameter Validation", value=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if model_type == "LSTM Autoencoder (Anomaly Detection)":
            epochs = st.slider(
                "Training Epochs", 
                min_value=10, 
                max_value=500, 
                value=st.session_state.training_params['epochs'], 
                step=10,
                help="Number of complete passes through the training dataset"
            )
            if enable_validation:
                st.info(get_parameter_assessment('epochs', epochs))
            st.session_state.training_params['epochs'] = epochs
            
            batch_size = st.slider(
                "Batch Size", 
                min_value=8, 
                max_value=128, 
                value=st.session_state.training_params['batch_size'], 
                step=8,
                help="Number of samples processed before model weights are updated"
            )
            if enable_validation:
                st.info(get_parameter_assessment('batch_size', batch_size))
            st.session_state.training_params['batch_size'] = batch_size
            
            learning_rate = st.select_slider(
                "Learning Rate",
                options=[0.001, 0.005, 0.01, 0.05, 0.1],
                value=st.session_state.training_params['learning_rate_lstm'],
                help="Step size for weight updates during training"
            )
            if enable_validation:
                st.info(get_parameter_assessment('learning_rate_lstm', learning_rate))
            st.session_state.training_params['learning_rate_lstm'] = learning_rate
            
        else:  # RL Agents
            timesteps = st.slider(
                "Total Timesteps", 
                min_value=1000, 
                max_value=100000, 
                value=st.session_state.training_params['total_timesteps'], 
                step=1000,
                help="Total number of steps the agent will interact with the environment"
            )
            if enable_validation:
                st.info(get_parameter_assessment('total_timesteps', timesteps))
            st.session_state.training_params['total_timesteps'] = timesteps
            
            learning_rate = st.select_slider(
                "Learning Rate",
                options=[0.0001, 0.0005, 0.001, 0.005],
                value=st.session_state.training_params['learning_rate_rl'],
                help="Step size for policy updates during training"
            )
            if enable_validation:
                st.info(get_parameter_assessment('learning_rate_rl', learning_rate))
            st.session_state.training_params['learning_rate_rl'] = learning_rate
            
            exploration = st.slider(
                "Exploration Rate", 
                min_value=0.1, 
                max_value=0.5, 
                value=st.session_state.training_params['exploration_rate'], 
                step=0.05,
                help="Controls the trade-off between exploration (trying new actions) and exploitation (using known good actions)"
            )
            if enable_validation:
                st.info(get_parameter_assessment('exploration_rate', exploration))
            st.session_state.training_params['exploration_rate'] = exploration
    
    with col2:
        st.write("**Data Configuration**")
        if model_type == "LSTM Autoencoder (Anomaly Detection)":
            use_existing = st.checkbox(
                "Use existing data", 
                value=st.session_state.training_params['use_existing'],
                help="Use pre-collected environment state data instead of generating new samples"
            )
            st.session_state.training_params['use_existing'] = use_existing
            
            if not use_existing:
                num_samples = st.slider(
                    "Generate samples", 
                    min_value=1000, 
                    max_value=10000, 
                    value=st.session_state.training_params['num_samples'], 
                    step=1000,
                    help="Number of synthetic samples to generate for training"
                )
                if enable_validation:
                    st.info(get_parameter_assessment('num_samples', num_samples))
                st.session_state.training_params['num_samples'] = num_samples
                
                anomaly_prob = st.slider(
                    "Anomaly probability", 
                    min_value=0.1, 
                    max_value=0.5, 
                    value=st.session_state.training_params['anomaly_prob'], 
                    step=0.05,
                    help="Probability of generating anomalous (vs normal) samples in the dataset"
                )
                if enable_validation:
                    st.info(get_parameter_assessment('anomaly_prob', anomaly_prob))
                st.session_state.training_params['anomaly_prob'] = anomaly_prob
        else:
            use_local = st.checkbox(
                "Use LocalStack for training", 
                value=st.session_state.training_params['use_local'],
                help="Use LocalStack for simulating AWS environment instead of real AWS resources"
            )
            st.session_state.training_params['use_local'] = use_local
        
        # Add parameter validation feedback
        if enable_validation:
            st.subheader("Parameter Impact Analysis")
            impact = predict_training_impact(st.session_state.training_params, model_type)
            
            # Show impact with visual indicators
            st.write("**Estimated Training Time:**", impact["est_training_time"])
            
            if model_type == "LSTM Autoencoder (Anomaly Detection)":
                # For LSTM, show accuracy metrics
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Est. Accuracy", impact["est_accuracy"])
                with col2:
                    st.metric("Est. F1 Score", impact["est_f1_score"])
                
                st.write("**Overfitting Risk:**", impact["overfitting_risk"])
            else:
                # For RL, show reward metrics
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Est. Success Rate", impact["est_success_rate"])
                with col2:
                    st.metric("Est. Mean Reward", impact["est_mean_reward"])
                
                risk_label = "Instability Risk" if model_type == "RL Agent (Chaos)" else "Inefficiency Risk"
                st.write(f"**{risk_label}:**", impact["stability_risk"])
            
            # Recommendation
            st.info(f"💡 **Recommendation:** {impact['recommendation']}")
            
            # Add parameter comparison visualization
            st.subheader("Parameters Comparison")
            
            # Store historical parameter sets in session state for comparison
            if 'parameter_history' not in st.session_state:
                st.session_state.parameter_history = []
            
            # Get the parameters from session state to avoid unbound variables
            current_epochs = st.session_state.training_params['epochs']
            current_batch_size = st.session_state.training_params['batch_size']
            current_learning_rate_lstm = st.session_state.training_params['learning_rate_lstm']
            current_total_timesteps = st.session_state.training_params['total_timesteps']
            current_learning_rate_rl = st.session_state.training_params['learning_rate_rl']
            current_exploration_rate = st.session_state.training_params['exploration_rate']
            
            # Create comparison chart based on model type
            if model_type == "LSTM Autoencoder (Anomaly Detection)":
                # Chart showing relationship between epochs, learning rate and accuracy
                chart_data = {
                    "Parameter": [],
                    "Value": [],
                    "Impact": []
                }
                
                # Add current parameters
                chart_data["Parameter"].append("Epochs")
                chart_data["Value"].append(current_epochs)
                chart_data["Impact"].append(min(1.0, 0.3 + (current_epochs/500) * 0.6))
                
                chart_data["Parameter"].append("Batch Size")
                chart_data["Value"].append(current_batch_size)
                normalized_batch = min(1.0, current_batch_size/128)
                chart_data["Impact"].append(0.5 + normalized_batch * 0.25)
                
                chart_data["Parameter"].append("Learning Rate")
                chart_data["Value"].append(current_learning_rate_lstm)
                normalized_lr = min(1.0, (current_learning_rate_lstm/0.1) * 0.9)
                chart_data["Impact"].append(normalized_lr)
                
                # Create a visual representation of parameter impacts
                st.write("Parameter Impact on Training (higher = stronger effect)")
                chart_df = pd.DataFrame(chart_data)
                st.bar_chart(chart_df.set_index("Parameter")["Impact"])
                
                # Show overfitting risk graph
                if current_epochs > 300 and current_batch_size < 32:
                    overfitting_risk = 0.8
                elif current_epochs > 200 and current_batch_size < 64:
                    overfitting_risk = 0.6
                elif current_epochs > 100:
                    overfitting_risk = 0.4
                else:
                    overfitting_risk = 0.2
                    
                underfitting_risk = 0.8 if current_epochs < 50 else 0.5 if current_epochs < 100 else 0.2
                
                risk_data = {
                    "Risk Type": ["Overfitting", "Underfitting"],
                    "Risk Level": [overfitting_risk, underfitting_risk]
                }
                risk_df = pd.DataFrame(risk_data)
                st.write("Training Risk Assessment")
                st.bar_chart(risk_df.set_index("Risk Type")["Risk Level"])
                
            else:  # RL agents
                # Different visualization for RL agents
                chart_data = {
                    "Parameter": [],
                    "Value": [],
                    "Impact": []
                }
                
                # Add current parameters
                chart_data["Parameter"].append("Timesteps")
                chart_data["Value"].append(current_total_timesteps)
                chart_data["Impact"].append(min(1.0, current_total_timesteps/100000))
                
                chart_data["Parameter"].append("Learning Rate")
                chart_data["Value"].append(current_learning_rate_rl)
                normalized_lr = min(1.0, (current_learning_rate_rl/0.001) * 0.8)
                chart_data["Impact"].append(normalized_lr)
                
                chart_data["Parameter"].append("Exploration")
                chart_data["Value"].append(current_exploration_rate)
                chart_data["Impact"].append(current_exploration_rate * 2)
                
                # Create a visual representation of parameter impacts
                st.write("Parameter Impact on Training (higher = stronger effect)")
                chart_df = pd.DataFrame(chart_data)
                st.bar_chart(chart_df.set_index("Parameter")["Impact"])
                
                # Show success probability vs training time
                training_time = current_total_timesteps * 0.005
                success_prob = 0.3 + min(0.6, current_total_timesteps/100000 * 0.6)
                
                if model_type == "RL Agent (Chaos)":
                    # For chaos agents, add exploration bonus
                    success_prob += current_exploration_rate * 0.2
                else:
                    # For remediation agents, lower exploration helps
                    success_prob += (0.5 - current_exploration_rate) * 0.15
                
                trade_data = {
                    "Metric": ["Training Time", "Success Probability"],
                    "Value": [min(1.0, training_time/500), min(1.0, success_prob)]
                }
                trade_df = pd.DataFrame(trade_data)
                st.write("Training Time vs Success Probability")
                st.bar_chart(trade_df.set_index("Metric")["Value"])
            
            # Parameter validation button
            if st.button("Validate Parameters"):
                st.session_state.training_params['is_validated'] = True
                
                # Add current parameter set to history for comparison
                param_snapshot = st.session_state.training_params.copy()
                param_snapshot['model_type'] = model_type
                param_snapshot['timestamp'] = datetime.now().strftime("%H:%M:%S")
                st.session_state.parameter_history.append(param_snapshot)
                
                st.success("✅ Parameters validated! You can now proceed with training.")
                st.balloons()
    
    # Container for training logs
    training_log_container = st.empty()
    
    # Show parameter history comparison if available
    if 'parameter_history' in st.session_state and len(st.session_state.parameter_history) > 0:
        with st.expander("Parameter History Comparison", expanded=False):
            st.write("Compare your current parameters with previously validated configurations")
            
            # Create a comparison table
            history_data = []
            
            # Get parameters from session state
            current_epochs = st.session_state.training_params['epochs']
            current_batch_size = st.session_state.training_params['batch_size']
            current_learning_rate_lstm = st.session_state.training_params['learning_rate_lstm']
            current_total_timesteps = st.session_state.training_params['total_timesteps']
            current_learning_rate_rl = st.session_state.training_params['learning_rate_rl']
            current_exploration_rate = st.session_state.training_params['exploration_rate']
            current_use_existing = st.session_state.training_params['use_existing']
            current_num_samples = st.session_state.training_params['num_samples']
            current_use_local = st.session_state.training_params['use_local']
            
            # Add current parameters to compare
            current_params = {
                "Configuration": "Current (Not Validated)",
                "Time": datetime.now().strftime("%H:%M:%S"),
                "Model Type": model_type
            }
            
            # Reuse values from session state instead of local variables
            if model_type == "LSTM Autoencoder (Anomaly Detection)":
                # Using session state values directly
                current_params.update({
                    "Epochs": st.session_state.training_params['epochs'],
                    "Batch Size": st.session_state.training_params['batch_size'],
                    "Learning Rate": st.session_state.training_params['learning_rate_lstm'],
                    "Data Source": "Existing" if st.session_state.training_params['use_existing'] else 
                                  f"Generated ({st.session_state.training_params['num_samples']} samples)"
                })
            else:
                # Using session state values directly
                current_params.update({
                    "Timesteps": st.session_state.training_params['total_timesteps'],
                    "Learning Rate": st.session_state.training_params['learning_rate_rl'],
                    "Exploration": st.session_state.training_params['exploration_rate'],
                    "Environment": "LocalStack" if st.session_state.training_params['use_local'] else "Real AWS"
                })
            
            history_data.append(current_params)
            
            # Add parameter history
            for i, param_set in enumerate(st.session_state.parameter_history):
                history_entry = {
                    "Configuration": f"Config #{i+1}",
                    "Time": param_set.get('timestamp', ''),
                    "Model Type": param_set.get('model_type', '')
                }
                
                if param_set.get('model_type', '') == "LSTM Autoencoder (Anomaly Detection)":
                    history_entry.update({
                        "Epochs": param_set.get('epochs', ''),
                        "Batch Size": param_set.get('batch_size', ''),
                        "Learning Rate": param_set.get('learning_rate_lstm', ''),
                        "Data Source": "Existing" if param_set.get('use_existing', True) else f"Generated ({param_set.get('num_samples', '')} samples)"
                    })
                else:
                    history_entry.update({
                        "Timesteps": param_set.get('total_timesteps', ''),
                        "Learning Rate": param_set.get('learning_rate_rl', ''),
                        "Exploration": param_set.get('exploration_rate', ''),
                        "Environment": "LocalStack" if param_set.get('use_local', True) else "Real AWS"
                    })
                
                history_data.append(history_entry)
            
            # Display as a table
            st.table(pd.DataFrame(history_data))
            
            # Option to clear history
            if st.button("Clear Parameter History"):
                st.session_state.parameter_history = []
                st.info("Parameter history cleared")
                st.rerun()
    
    # Training button with validation check
    train_button_disabled = enable_validation and not st.session_state.training_params['is_validated']
    train_button_label = "Start Training"
    
    if train_button_disabled:
        train_button_label = "Validate Parameters First"
        st.warning("⚠️ Please validate your parameters before starting training")
    
    start_training = st.button(train_button_label, disabled=train_button_disabled)
    
    if start_training:
        # Create a container for training logs
        with st.expander("Training Logs", expanded=True):
            log_output = st.empty()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Initialize log data
            logs = []
            
            # Simulate training process using the actual parameters provided
            # Extract all parameters from session state
            epochs = st.session_state.training_params['epochs']
            batch_size = st.session_state.training_params['batch_size']
            learning_rate_lstm = st.session_state.training_params['learning_rate_lstm']
            total_timesteps = st.session_state.training_params['total_timesteps']
            learning_rate_rl = st.session_state.training_params['learning_rate_rl']
            exploration_rate = st.session_state.training_params['exploration_rate']
            use_existing = st.session_state.training_params['use_existing']
            num_samples = st.session_state.training_params['num_samples']
            anomaly_prob = st.session_state.training_params['anomaly_prob']
            use_local = st.session_state.training_params['use_local']
            
            # Calculate iterations based on parameters (with reasonable limits for UI responsiveness)
            # We'll scale down for demo purposes but preserve the ratio
            if model_type == "LSTM Autoencoder (Anomaly Detection)":
                # Use the full number of epochs specified by the user without capping
                total_iters = epochs
                # Scale factors to make the simulation reflect parameter changes
                learning_factor = learning_rate_lstm * 20  # Higher rate = faster convergence
                batch_factor = batch_size / 32  # Larger batch = fewer steps but less noise
                
                # Display configuration being used
                log_output.info(f"Starting training with parameters: epochs={epochs}, batch_size={batch_size}, learning_rate={learning_rate_lstm}")
                
                # Log data source configuration
                if use_existing:
                    log_output.info("Using existing dataset for training")
                    data_size = 5000  # Default size for existing data
                else:
                    log_output.info(f"Generating {num_samples} samples with anomaly probability {anomaly_prob}")
                    data_size = num_samples
                    
                # Log data preprocessing steps
                log_output.info(f"Preprocessing {data_size} data points...")
                time.sleep(0.2)  # Simulate data loading time
                
                # Simulate different training behavior based on batch size
                # Calculate batches per epoch based on data size and batch size
                batches_per_epoch = max(1, int(data_size / batch_size)) 
                # This is a key variable used later in the simulation
                log_output.info(f"Training will use {batches_per_epoch} batches per epoch")
                
            else:  # RL Agents
                # For RL: Use the full number of timesteps specified by the user
                timesteps_per_iter = 500  # Each iteration represents this many timesteps
                total_iters = total_timesteps // timesteps_per_iter  # Use all timesteps without capping
                
                # Different learning parameters for RL
                learning_factor = learning_rate_rl * 2500  # Higher learning rate = faster convergence
                is_chaos = model_type == "RL Agent (Chaos)"
                
                # Log configuration
                log_output.info(f"Starting {model_type} training with parameters:")
                log_output.info(f"Total timesteps: {total_timesteps}")
                log_output.info(f"Learning rate: {learning_rate_rl}")
                log_output.info(f"Exploration rate: {exploration_rate}")
                
                # Infrastructure configuration
                if use_local:
                    log_output.info("Using LocalStack for environment simulation")
                    # Simulate environment setup time
                    log_output.info("Setting up LocalStack environment...")
                    time.sleep(0.3)  # Simulate environment initialization
                else:
                    log_output.info("Using real AWS environment")
                    log_output.info("Initializing AWS SDK clients...")
                    time.sleep(0.3)  # Simulate initialization
                
                # Log additional configuration steps specific to RL
                if is_chaos:
                    log_output.info("Configuring chaos agent policy with PPO algorithm")
                    log_output.info(f"Exploration configuration: epsilon={exploration_rate}")
                else:
                    log_output.info("Configuring remediation agent policy with A2C algorithm")
                    log_output.info(f"Exploitation focus: epsilon={exploration_rate}")
            
            # Initial values for metrics
            best_loss = float('inf')
            best_reward = float('-inf') if model_type == "RL Agent (Chaos)" else float('-inf')
            anomaly_scores = []
            rewards = []
            
            # Initialize counters for later use
            successful_disruptions = 0
            successful_remediations = 0
            
            # Initialize other variables that might be referenced later
            if 'batches_per_epoch' not in locals():
                batches_per_epoch = 5  # Default value
                
            if 'timesteps_per_iter' not in locals():
                timesteps_per_iter = 500  # Default value
            
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
                    max_epochs = epochs  # Use actual epoch count from parameters
                    
                    # Calculate training progress - different learning curves based on parameters
                    # Higher learning rate = faster initial drop, but potential plateaus
                    # Larger batch size = smoother curve but potentially slower initial progress
                    progress_factor = (i / total_iters)
                    # Learning rate affects convergence speed (higher = faster convergence)
                    lr_factor = learning_rate_lstm * 20
                    # Batch size affects noise level (larger = less noise)
                    noise_factor = 0.1 * (32 / batch_size)
                    
                    # Simulate batch training with actual batch size affecting behavior
                    batch_losses = []
                    # Ensure batches_per_epoch is available from outer scope
                    # Default to 5 if not defined (shouldn't happen, but prevents errors)
                    actual_batches = batches_per_epoch if 'batches_per_epoch' in locals() else 5
                    for b in range(actual_batches):  # Use actual batches per epoch based on batch size
                        # Complex learning curve simulation that respects parameters:
                        # - Higher learning rates cause faster initial drop but may plateau
                        # - Smaller batch sizes increase noise/variance
                        # - More epochs allow for continued refinement
                        base_loss = max(0.01, 1.0 - (progress_factor * lr_factor))
                        batch_noise = random.uniform(-noise_factor, noise_factor)
                        
                        # Apply anomaly probability if using generated data
                        if not use_existing and anomaly_prob > 0:
                            # Higher anomaly probability makes learning harder (increases loss)
                            anomaly_factor = anomaly_prob * 0.2
                            batch_loss = base_loss * (1 + anomaly_factor) + batch_noise
                        else:
                            batch_loss = base_loss + batch_noise
                            
                        batch_losses.append(batch_loss)
                    
                    # Overall epoch metrics
                    loss = sum(batch_losses) / len(batch_losses)
                    # Validation loss simulation - affected by data size and other factors
                    if not use_existing and num_samples < 3000:
                        # Small datasets lead to more overfitting (higher val loss)
                        val_factor = 1.2
                    else:
                        val_factor = 1.05
                    val_loss = loss * val_factor + random.uniform(-0.02, 0.02)
                    
                    # Track best model
                    if val_loss < best_loss:
                        best_loss = val_loss
                        log_entry = f"{timestamp} - Epoch {epoch+1}/{max_epochs} - loss: {loss:.4f} - val_loss: {val_loss:.4f} - ✓ New best model saved"
                    else:
                        log_entry = f"{timestamp} - Epoch {epoch+1}/{max_epochs} - loss: {loss:.4f} - val_loss: {val_loss:.4f}"
                    
                    status_text.text(f"Training epoch {epoch+1} of {max_epochs}, loss: {loss:.4f}")
                else:
                    # RL Agent training
                    # Default timesteps_per_iter to 500 if not defined
                    steps_per_iter = 500  # Default value 
                    timestep = i * steps_per_iter  # Scale by steps per iteration
                    max_timesteps = total_timesteps  # Use actual total timesteps from parameters
                    
                    # RL training simulation that respects parameters:
                    # For both agent types:
                    # - Higher learning rate = faster policy updates
                    # - More timesteps = more thorough learning
                    # Additionally:
                    # - Chaos agent: higher exploration = better at finding anomalies
                    # - Remediation agent: lower exploration = better at focused remediation
                    
                    progress_factor = i / total_iters
                    # Learning rate affects policy update speed
                    lr_convergence = learning_rate_rl * 2000
                    
                    # Different reward functions for chaos vs remediation
                    if model_type == "RL Agent (Chaos)":
                        # For chaos: Higher anomaly score = better reward (maximizing disruption)
                        # Use exploration rate to determine how quickly agent finds disruptive actions
                        exploration_impact = exploration_rate * 1.5  # Higher exploration = quicker discovery
                        
                        # Learning curve - starts low, increases as agent learns to cause chaos
                        base_score = min(0.8, progress_factor * exploration_impact)
                        # Apply learning rate effect - higher rates accelerate learning
                        learning_effect = min(0.3, progress_factor * lr_convergence)
                        anomaly_score = min(0.9, base_score + learning_effect)
                        
                        # Add random noise based on exploration rate
                        noise_level = exploration_rate * 0.2
                        anomaly_score += random.uniform(-noise_level, noise_level)
                        anomaly_score = max(0.01, min(0.95, anomaly_score))  # Clamp to valid range
                        
                        # Reward increases as anomaly score increases
                        reward = anomaly_score * 10
                        
                        # Occasional failed attempts - use exploration rate to determine frequency
                        # Higher exploration = more failures at start but fewer later
                        failure_chance = 0.2 * (1 - progress_factor) if exploration_rate > 0.3 else 0.1
                        if random.random() < failure_chance:
                            reward = -2.0  # Failed attempts get negative rewards
                            log_entry = f"{timestamp} - Timestep {timestep}/{max_timesteps} - anomaly: {anomaly_score:.2f} - reward: {reward:.2f} - Action failed!"
                        else:
                            log_entry = f"{timestamp} - Timestep {timestep}/{max_timesteps} - anomaly: {anomaly_score:.2f} - reward: {reward:.2f}"
                    else:  # Remediation
                        # For remediation: Lower anomaly score = better reward (fixing issues)
                        # Start with high anomaly scores that get reduced over time
                        
                        # Lower exploration = better focus on successful remediation strategies
                        focus_factor = (0.5 - exploration_rate) * 2  # Invert: lower exploration = higher focus
                        
                        # Initially high anomaly that decreases as agent learns to fix problems
                        initial_anomaly = 0.7
                        remediation_speed = min(0.8, progress_factor * (1 + focus_factor) * lr_convergence)
                        anomaly_score = max(0.05, initial_anomaly - remediation_speed)
                        
                        # Add random noise based on exploration rate
                        noise_level = exploration_rate * 0.15
                        anomaly_score += random.uniform(-noise_level, noise_level)
                        anomaly_score = max(0.01, min(0.95, anomaly_score))  # Clamp to valid range
                        
                        # Reward increases as anomaly score decreases
                        reward = (1 - anomaly_score) * 10
                        
                        # Occasional failed attempts - more likely early on
                        failure_chance = 0.15 * (1 - progress_factor)
                        if random.random() < failure_chance:
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
            
            # Create mock model data for persistence
            import numpy as np
            import pickle
            import os
            
            # Generate model data based on the type
            if model_type == "LSTM Autoencoder (Anomaly Detection)":
                # Create a mock LSTM model (simplified as a dict with weights and config)
                model_data = {
                    'weights': np.random.randn(10, 10).tolist(),  # Mock weights
                    'config': {
                        'input_shape': (5, 25),
                        'latent_dim': 8,
                        'epochs': epochs,
                        'batch_size': batch_size,
                        'learning_rate': learning_rate_lstm,
                        'timestamp': datetime.now().isoformat()
                    },
                    'training_history': logs
                }
                model_type_key = 'anomaly_model'
                
            elif model_type == "RL Agent (Chaos)":
                # Create a mock RL model for chaos simulation
                model_data = {
                    'policy': np.random.randn(5, 36).tolist(),  # Mock policy weights
                    'config': {
                        'state_shape': (5, 25),
                        'action_space': 36,
                        'total_timesteps': total_timesteps,
                        'exploration_rate': exploration_rate,
                        'learning_rate': learning_rate_rl,
                        'timestamp': datetime.now().isoformat()
                    },
                    'training_history': logs
                }
                model_type_key = 'chaos_agent'
                
            elif model_type == "RL Agent (Remediation)":
                # Create a mock RL model for remediation
                model_data = {
                    'policy': np.random.randn(5, 25).tolist(),  # Mock policy weights
                    'config': {
                        'state_shape': (5, 25),
                        'action_space': 25,
                        'total_timesteps': total_timesteps,
                        'exploration_rate': exploration_rate,
                        'learning_rate': learning_rate_rl,
                        'timestamp': datetime.now().isoformat()
                    },
                    'training_history': logs
                }
                model_type_key = 'remediation_agent'
            
            # Save the trained model
            if save_model(model_type_key, model_data):
                # Update status with success message
                st.success(f"✅ Model saved successfully: {model_type_key}")
                
                # Update model status in session state based on model type
                if model_type == "LSTM Autoencoder (Anomaly Detection)":
                    st.session_state.model_statuses['anomaly_model'] = f"Trained (Epochs: {epochs})"
                elif model_type == "RL Agent (Chaos)":
                    st.session_state.model_statuses['chaos_agent'] = f"Trained (Steps: {total_timesteps})"
                elif model_type == "RL Agent (Remediation)":
                    st.session_state.model_statuses['remediation_agent'] = f"Trained (Steps: {total_timesteps})"
            else:
                # Show error message if saving failed
                st.error("Failed to save model. Check logs for details.")
        
        # Show evaluation results based on actual training parameters
        st.subheader("Training Results")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Performance Metrics")
            if model_type == "LSTM Autoencoder (Anomaly Detection)":
                # Calculate metrics based on parameters
                # Lower is better for loss metrics
                final_loss = max(0.01, best_loss)
                val_loss = final_loss * 1.1
                
                # Higher learning rate and epochs improve accuracy but risk overfitting
                base_accuracy = min(0.95, 0.75 + (epochs/500) * 0.15 + (learning_rate_lstm/0.01) * 0.05)
                
                # Penalty for very small datasets or high anomaly probability
                if not use_existing and num_samples < 3000:
                    dataset_penalty = 0.05
                elif not use_existing and anomaly_prob > 0.35:
                    dataset_penalty = 0.03
                else:
                    dataset_penalty = 0
                
                accuracy = max(0.7, base_accuracy - dataset_penalty)
                precision = accuracy - random.uniform(0.01, 0.03)
                recall = accuracy - random.uniform(0.02, 0.05)
                f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                
                # Calculate training time based on epochs and batch size
                training_time_secs = epochs * 5 + (num_samples if not use_existing else 5000) / batch_size * 0.1
                training_mins = int(training_time_secs // 60)
                training_secs = int(training_time_secs % 60)
                
                st.json({
                    "final_loss": f"{final_loss:.4f}",
                    "val_loss": f"{val_loss:.4f}",
                    "training_time": f"{training_mins}m {training_secs}s",
                    "anomaly_threshold": f"{max(0.05, min(0.2, best_loss * 2)):.3f}",
                    "evaluation": {
                        "accuracy": f"{accuracy:.2f}",
                        "precision": f"{precision:.2f}",
                        "recall": f"{recall:.2f}",
                        "f1_score": f"{f1_score:.2f}"
                    }
                })
            else:
                # For RL agents, calculate metrics based on training parameters
                # Mean reward calculation
                if model_type == "RL Agent (Chaos)":
                    # For chaos: higher exploration generally increases reward ceiling
                    exploration_bonus = exploration_rate * 30
                    timestep_factor = min(1.0, total_timesteps / 50000) * 40
                    lr_factor = learning_rate_rl * 2000
                    mean_reward = 20 + timestep_factor + exploration_bonus
                    max_reward = mean_reward * (1.2 + random.uniform(0.1, 0.3))
                    
                    # Success is measured by ability to cause anomalies
                    success_rate = min(0.95, 0.6 + exploration_rate * 0.4 + (total_timesteps/100000) * 0.2)
                    
                    # Successful disruptions calculation
                    successful_disruptions = int(success_rate * (total_timesteps / 1000))
                    
                else:  # Remediation
                    # For remediation: lower exploration can help with focused remediation
                    focus_bonus = (0.5 - exploration_rate) * 20
                    timestep_factor = min(1.0, total_timesteps / 50000) * 40
                    lr_factor = learning_rate_rl * 2000
                    mean_reward = 25 + timestep_factor + focus_bonus
                    max_reward = mean_reward * (1.3 + random.uniform(0.1, 0.4))
                    
                    # Success is measured by ability to fix anomalies
                    success_rate = min(0.95, 0.65 + (0.5 - exploration_rate) * 0.3 + (total_timesteps/100000) * 0.25)
                    
                    # Successful remediations calculation
                    successful_remediations = int(success_rate * (total_timesteps / 1000))
                
                # Calculate training time based on timesteps and environment
                time_multiplier = 1.2 if not use_local else 1.0  # Real AWS is slightly slower
                training_time_secs = total_timesteps * 0.005 * time_multiplier
                training_mins = int(training_time_secs // 60)
                training_secs = int(training_time_secs % 60)
                
                if model_type == "RL Agent (Chaos)":
                    success_key = "successful_disruptions"
                    success_value = successful_disruptions
                else:
                    success_key = "successful_remediations"
                    success_value = successful_remediations
                
                st.json({
                    "mean_reward": f"{mean_reward:.1f}",
                    "max_reward": f"{max_reward:.1f}",
                    "training_time": f"{training_mins}m {training_secs}s",
                    success_key: success_value,
                    "evaluation": {
                        "average_return": f"{mean_reward * 0.9:.1f}",
                        "success_rate": f"{success_rate:.2f}"
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
def display_infrastructure_topology():
    st.header("AWS Infrastructure Topology")
    
    # Create/retrieve topology from session state
    if 'infra_topology' not in st.session_state:
        st.session_state.infra_topology = InfrastructureTopology()
    
    # Clean, simplified infrastructure view
    st.write("This view shows the current state of your AWS infrastructure components and their connections.")
    
    # Add some manual test actions for demonstration
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Reset Infrastructure"):
            st.session_state.infra_topology.reset()
            st.rerun()
    
    with col2:
        if st.button("Simulate Chaos Event"):
            actions = [
                "EC2 instance termination",
                "RDS CPU stress",
                "API throttling",
                "Network latency injection",
                "Lambda concurrency limitation",
                "S3 access throttling"
            ]
            # Select a random chaos action
            action = random.choice(actions)
            st.session_state.infra_topology.apply_chaos_action(action)
            st.success(f"Applied chaos action: {action}")
            st.rerun()
    
    with col3:
        if st.button("Apply Remediation"):
            if st.session_state.infra_topology.state_history:
                # Get the last chaos action
                last_action = None
                for event in reversed(st.session_state.infra_topology.state_history):
                    if event['action'] == 'chaos':
                        last_action = event['description']
                        break
                
                if last_action:
                    remedy = f"Fix {last_action.lower()}"
                    st.session_state.infra_topology.apply_remediation_action(remedy)
                    st.success(f"Applied remediation: {remedy}")
                else:
                    st.warning("No chaos event to remediate")
            else:
                st.warning("No chaos event to remediate")
            st.rerun()
    
    # Display the infrastructure topology - use the imported function
    from infrastructure_topology import display_infrastructure_topology as display_topology
    display_topology(st.session_state.infra_topology)
    
    # Information about the visualization
    with st.expander("About this visualization"):
        st.write("""
        This simplified AWS infrastructure topology shows the relationship between different AWS services
        and their current operational status. The colors indicate:
        
        - 🟢 **Healthy**: Service is operating normally
        - 🟠 **Degraded**: Service is experiencing issues but still functional
        - 🔴 **Failed**: Service is not operational
        
        When a chaos event is applied, it affects specific services and may propagate to dependent services.
        The remediation actions aim to restore the affected services to their healthy state.
        """)

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
            "Infrastructure Topology",
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
    elif page == "Infrastructure Topology":
        display_infrastructure_topology()
    elif page == "Logs & Analysis":
        display_logs_analysis()

if __name__ == "__main__":
    main()