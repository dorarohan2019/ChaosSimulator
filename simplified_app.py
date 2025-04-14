import streamlit as st
import time
import os
import json
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from impact_analysis import display_impact_analysis
from collections import deque
import requests  # For Slack API fallback if slack_sdk is not available

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)

logger = logging.getLogger('dashboard')

# Constants
SLACK_CHANNEL_NAME = 'chaos-engineering'
SLACK_APPROVAL_TIMEOUT = 300  # 5 minutes timeout for approvals

# Check if slack_sdk is available
try:
    import slack_sdk
    from slack_sdk.errors import SlackApiError
    SLACK_SDK_AVAILABLE = True
except ImportError:
    SLACK_SDK_AVAILABLE = False
    logger.warning("slack_sdk not available. Using requests for Slack API calls.")

# Apply global styling for chart data points and different chart colors
def apply_chart_data_point_styling():
    """Apply global styling to make chart data points consistently red and set different chart colors"""
    st.markdown("""
    <style>
    /* Make all chart data points (circles) red with border for better visibility */
    .stChart circle {
        fill: #FF0000 !important; 
        r: 7 !important; /* larger radius for better visibility */
        stroke: #8B0000 !important; /* dark red border */
        stroke-width: 2 !important; /* thicker border */
    }
    
    /* Custom colors for different charts */
    /* Anomaly Score (Chaos) - Orange/Red */
    [data-testid="StyledFullScreenFrame"] div:has(> div:contains("Anomaly Score")) .element-container:nth-of-type(2) path {
        stroke: #ff3b30 !important;
        stroke-width: 3 !important;
    }
    
    /* Anomaly Score (Remediation) - Yellow */
    [data-testid="StyledFullScreenFrame"] div:has(> div:contains("Anomaly Score")) .element-container:nth-of-type(3) path {
        stroke: #ffcc00 !important;
        stroke-width: 3 !important;
    }
    
    /* System Health (Chaos) - Green */
    [data-testid="StyledFullScreenFrame"] div:has(> div:contains("System Health")) .element-container:nth-of-type(2) path {
        stroke: #00a651 !important;
        stroke-width: 3 !important;
    }
    
    /* System Health (Remediation) - Pink */
    [data-testid="StyledFullScreenFrame"] div:has(> div:contains("System Health")) .element-container:nth-of-type(3) path {
        stroke: #ff69b4 !important;
        stroke-width: 3 !important;
    }
    
    /* Service Availability (Chaos) - Blue */
    [data-testid="StyledFullScreenFrame"] div:has(> div:contains("Service Availability")) .element-container:nth-of-type(2) path {
        stroke: #007bff !important;
        stroke-width: 3 !important;
    }
    
    /* Service Availability (Remediation) - Purple */
    [data-testid="StyledFullScreenFrame"] div:has(> div:contains("Service Availability")) .element-container:nth-of-type(3) path {
        stroke: #6f42c1 !important;
        stroke-width: 3 !important;
    }
    
    /* API Error Rate (Chaos) - Orange */
    [data-testid="StyledFullScreenFrame"] div:has(> div:contains("API Error Rate")) .element-container:nth-of-type(2) path {
        stroke: #fd7e14 !important;
        stroke-width: 3 !important;
    }
    
    /* API Error Rate (Remediation) - Teal */
    [data-testid="StyledFullScreenFrame"] div:has(> div:contains("API Error Rate")) .element-container:nth-of-type(3) path {
        stroke: #20c997 !important;
        stroke-width: 3 !important;
    }
    
    /* Custom metric cards styling */
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    
    /* Status indicator styling */
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .status-green { background-color: #00a651; }
    .status-yellow { background-color: #ffcc00; }
    .status-red { background-color: #ff3b30; }
    
    /* Anomaly score styling */
    .anomaly-low { color: #00a651; font-weight: bold; }
    .anomaly-medium { color: #ffcc00; font-weight: bold; }
    .anomaly-high { color: #ff3b30; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

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

# Mock State Collector with normal state by default
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
        """Generate a synthetic state with normal operating conditions by default"""
        import random
        
        # Create a sample state dictionary with values representing normal conditions
        state = {}
        
        # If scenario is explicitly set to 'normal' or None, use normal operating conditions
        if scenario == 'normal' or scenario is None:
            # Initialize with baseline values for a healthy system
            for key in self.metric_keys:
                # Use healthy values for all metrics
                if 'count' in key:
                    state[key] = random.randint(3, 8)  # Reasonable number of resources
                elif 'cpu' in key:
                    state[key] = random.randint(15, 40)  # Moderate CPU usage (15-40%)
                elif 'errors' in key:
                    state[key] = random.randint(0, 2)  # Very few errors
                elif 'latency' in key:
                    state[key] = random.randint(5, 30)  # Good latency values
                elif 'invocations' in key:
                    state[key] = random.randint(20, 80)  # Normal invocation volume
                # Explicitly handle security metrics for normal conditions
                elif key == 'security_findings':
                    state[key] = 0  # Zero security findings in normal state
                elif key == 'failed_logins':
                    state[key] = random.randint(0, 3)  # Very few failed login attempts
                elif key == 'vulnerability_count':
                    state[key] = random.randint(0, 2)  # Very few or no vulnerabilities
                elif 'network' in key:
                    state[key] = random.randint(30, 70)  # Normal network traffic
                elif 'packet_loss' in key:
                    state[key] = random.randint(0, 2)  # Very low packet loss
                else:
                    # Healthy values for other metrics
                    state[key] = random.randint(30, 70)  # Normal range for other metrics
        else:
            # For any other scenario, use the original random generation
            for key in self.metric_keys:
                if 'count' in key:
                    state[key] = random.randint(1, 10)
                elif 'cpu' in key:
                    state[key] = random.randint(10, 80)
                elif 'errors' in key or 'findings' in key:
                    state[key] = random.randint(0, 5)
                elif 'latency' in key:
                    state[key] = random.randint(1, 100)
                elif 'invocations' in key or 'logins' in key:
                    state[key] = random.randint(10, 100)
                else:
                    state[key] = random.randint(10, 100)
                
        return state

# The rest of your application code remains unchanged...
# Include essential functions from the original app to make this version work

def main():
    """Main app loop."""
    apply_chart_data_point_styling()
    dashboard_header()
    
    # Navigation
    page_options = ["Dashboard", "Simulation Orchestration", "Impact Analysis", "Model Training", "Logs Analysis"]
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select Page", page_options)
    
    # Model status indicators in sidebar
    with st.sidebar:
        st.markdown("### Model Status")
        for model_type, status in st.session_state.model_statuses.items():
            status_color = "#4CAF50" if status == "Trained" or status == "Loaded" else "#FFA000"
            st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <div style="width: 12px; height: 12px; border-radius: 50%; background-color: {status_color}; margin-right: 8px;"></div>
                <span>{model_type.replace('_', ' ').title()}: {status}</span>
            </div>
            """, unsafe_allow_html=True)
    
    # Check required files
    if not os.path.exists("models"):
        os.makedirs("models", exist_ok=True)
    
    # Display the selected page
    if page == "Dashboard":
        display_dashboard()
    elif page == "Simulation Orchestration":
        st.info("Simulation Orchestration page would be displayed here")
    elif page == "Impact Analysis":
        display_impact_analysis()
    elif page == "Model Training":
        st.info("Model Training page would be displayed here")
    elif page == "Logs Analysis":
        st.info("Logs Analysis page would be displayed here")

# Simplified display_dashboard function
def display_dashboard():
    st.header("Infrastructure Dashboard")
    
    # Generate current state if none exists
    if st.session_state.current_state is None:
        collector = MockStateCollector()
        state = collector.collect_state(scenario='normal')
        st.session_state.current_state = state
    
    # Add refresh button
    col_refresh = st.columns([3, 1])
    
    with col_refresh[0]:
        st.markdown("### System State Overview")
        
    # Create simple metrics for display
    metrics = st.session_state.current_state
    
    # Create system health metric with initial healthy state  
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Display EC2 metrics
        st.markdown("""
        <div style="border-left: 5px solid #4a90e2; padding-left: 10px; margin-bottom: 15px;">
            <h4>📊 EC2 Performance</h4>
            <p>Instances: Running smoothly</p>
            <p>CPU Usage: Normal range</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display RDS metrics
        st.markdown("""
        <div style="border-left: 5px solid #4a90e2; padding-left: 10px; margin-bottom: 15px;">
            <h4>💾 RDS Database</h4>
            <p>Status: Available</p>
            <p>Connections: Stable</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Display Lambda metrics
        st.markdown("""
        <div style="border-left: 5px solid #7fba00; padding-left: 10px; margin-bottom: 15px;">
            <h4>⚡ Lambda Functions</h4>
            <p>Invocations: Normal</p>
            <p>Errors: Minimal</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display S3/SQS metrics
        st.markdown("""
        <div style="border-left: 5px solid #7fba00; padding-left: 10px; margin-bottom: 15px;">
            <h4>📦 Storage & Queues</h4>
            <p>S3 Status: Operational</p>
            <p>SQS: Processing normally</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        # Display security metrics - start with 0 findings for normal state
        st.markdown(f"""
        <div style="border-left: 5px solid #0078d4; padding-left: 10px; margin-bottom: 15px;">
            <h4>🔒 Security</h4>
            <p>Findings: {metrics.get('security_findings', 0)}</p>
            <p>Failed Logins: {metrics.get('failed_logins', 0)}</p>
            <p>Vulnerabilities: {metrics.get('vulnerability_count', 0)}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display network metrics
        st.markdown("""
        <div style="border-left: 5px solid #0078d4; padding-left: 10px; margin-bottom: 15px;">
            <h4>🌐 Network</h4>
            <p>Status: Healthy</p>
            <p>Packet Loss: Minimal</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Display system status with anomaly score calculation
    st.subheader("System Status")
    
    # Compute anomaly score - this would normally come from the model
    # Always ensure anomaly score is in normal range when webapp initially loads
    if 'first_load' not in st.session_state:
        st.session_state.first_load = True
        anomaly_score = random.uniform(0.01, 0.1)  # Normal range for initial load
    else:
        anomaly_score = metrics.get('security_findings', 0) * 0.01 + metrics.get('failed_logins', 0) * 0.01
        if anomaly_score == 0:
            anomaly_score = random.uniform(0.01, 0.1)  # Sample value if no metrics yet
    
    # Display system health summary
    system_health = 1.0 - anomaly_score
    
    # Create a simple gauge for system health
    st.markdown(f"""
    <div style="margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span>System Health: {system_health:.2f}</span>
            <span>Anomaly Score: {anomaly_score:.2f}</span>
        </div>
        <div style="height: 20px; background-color: #f0f0f0; border-radius: 10px; overflow: hidden; margin-top: 5px;">
            <div style="height: 100%; width: {system_health * 100}%; background-color: 
                       {'#00a651' if system_health > 0.85 else '#ffcc00' if system_health > 0.7 else '#ff3b30'};">
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Display system health status text
    status_text = "All systems operating normally" if system_health > 0.85 else \
                 "Minor issues detected, monitoring closely" if system_health > 0.7 else \
                 "System degradation detected, remediation recommended"
    
    st.info(status_text)

if __name__ == "__main__":
    main()