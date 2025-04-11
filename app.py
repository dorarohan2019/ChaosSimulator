import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import time
import os
import json
import torch
from datetime import datetime, timedelta
import logging
from collections import deque

# Import project modules
from environment import StateCollector
from models.predictive_model import LSTMAutoencoder
from chaos import ChaosEnvironment
from remediation import RemediationEnvironment
from utils import setup_localstack, provision_localstack_resources, parse_logs, summarize_experiment
from visualizations import (
    dashboard_header, 
    display_anomaly_threshold_chart, 
    display_state_timeseries, 
    display_chaos_action_distribution,
    display_remediation_effectiveness,
    display_live_metrics_chart,
    plot_service_health,
    plot_confusion_matrix,
    visualize_model_training
)
from orchestration import run_chaos_simulation

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

# Load models
@st.cache_resource
def load_predictive_model():
    try:
        model = LSTMAutoencoder(timesteps=5, features=25)
        model.load('lstm_autoencoder.pth', 'mean.npy', 'std.npy')
        return model
    except FileNotFoundError:
        return None

@st.cache_resource
def load_agents():
    chaos_env = ChaosEnvironment(is_local=True, use_collected_states=True, load_model=True)
    remediation_env = RemediationEnvironment(is_local=True, use_collected_states=True, load_model=True)
    return chaos_env, remediation_env

# Function to check if required files exist
def check_required_files():
    required_files = [
        'lstm_autoencoder.pth',
        'mean.npy',
        'std.npy',
        'environment_states.npy'
    ]
    
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        st.warning(f"Missing required files: {', '.join(missing_files)}")
        return False
    return True

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

# Dashboard page
def display_dashboard():
    st.header("Infrastructure Dashboard")
    
    # System status cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.info("**LocalStack Status**: Running" if setup_localstack() else "**LocalStack Status**: Not Running")
        
    with col2:
        model = load_predictive_model()
        st.info("**Anomaly Model**: Loaded" if model else "**Anomaly Model**: Not Loaded")
        
    with col3:
        chaos_env, _ = load_agents()
        st.info("**Chaos Agent**: Loaded" if chaos_env.model else "**Chaos Agent**: Not Trained")
        
    with col4:
        _, remediation_env = load_agents()
        st.info("**Remediation Agent**: Loaded" if remediation_env.model else "**Remediation Agent**: Not Trained")
    
    # Generate current state if none exists
    if st.session_state.current_state is None:
        collector = StateCollector()
        state = collector.collect_state(scenario='normal')
        st.session_state.current_state = state
    
    # Service health gauges
    st.subheader("Service Health")
    health_fig = plot_service_health(st.session_state.current_state)
    st.plotly_chart(health_fig, use_container_width=True)
    
    # Add refresh button
    if st.button("Refresh Metrics"):
        collector = StateCollector()
        state = collector.collect_state()
        st.session_state.current_state = state
        
        # Update metrics history
        for key in st.session_state.metrics_history:
            if key in state:
                st.session_state.metrics_history[key].append(state[key])
            elif key == 'anomaly_score' and model:
                # Convert state to format expected by model
                state_array = np.array([state[k] for k in collector.metric_keys])
                # For simplicity, create a sequence of 5 of the same state
                state_seq = np.tile(state_array, (5, 1))
                # Get anomaly score
                anomaly_score = model.get_anomaly_score(state_seq)
                st.session_state.metrics_history[key].append(anomaly_score)
        
        st.experimental_rerun()
    
    # Live metrics chart
    st.subheader("Live Metrics")
    
    # Convert deques to lists for plotting
    history_dict = {k: list(v) for k, v in st.session_state.metrics_history.items()}
    if any(len(v) > 0 for v in history_dict.values()):
        metrics_fig = display_live_metrics_chart(history_dict)
        st.plotly_chart(metrics_fig, use_container_width=True)
    else:
        st.info("No metrics data available yet. Click 'Refresh Metrics' to collect data.")
    
    # Raw metrics
    with st.expander("Current Metrics"):
        if st.session_state.current_state:
            metrics_df = pd.DataFrame([st.session_state.current_state])
            st.dataframe(metrics_df, use_container_width=True)

# Chaos simulation page
def display_chaos_simulation():
    st.header("Chaos Simulation")
    
    if not check_required_files():
        st.error("Cannot run chaos simulation. Required models or data are missing.")
        return
    
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
                st.experimental_rerun()
    
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
                # Start simulation in a new thread or process
                st.experimental_rerun()
        
        with confirm_col2:
            if st.button("❌ Deny Simulation"):
                st.session_state.approval_requested = False
                st.experimental_rerun()
    
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
                action_description = chaos_env.get_action_description(int(chaos_action.item()))
                
                status_container.info(f"Step {step+1}/{num_actions}: Executing {action_description}")
                
                # Apply chaos action
                next_state, chaos_reward, chaos_done, chaos_info = chaos_env.step(int(chaos_action.item()))
                
                # Record action
                st.session_state.chaos_actions.append({
                    'step': step,
                    'action': int(chaos_action.item()),
                    'description': action_description,
                    'reward': chaos_reward,
                    'anomaly_score': chaos_info.get('anomaly_score', 0)
                })
                
                # Display state metrics
                metrics_df = pd.DataFrame([{
                    'Metric': 'Anomaly Score',
                    'Value': chaos_info.get('anomaly_score', 0)
                }, {
                    'Metric': 'Chaos Reward',
                    'Value': chaos_reward
                }])
                metrics_container.dataframe(metrics_df, use_container_width=True, hide_index=True)
                
                # Display current state chart
                if isinstance(next_state, np.ndarray) and next_state.shape[0] > 0:
                    feature_names = [
                        'ec2_count', 'ec2_running', 'ec2_cpu_avg',
                        'rds_count', 'rds_available', 'rds_connections', 'rds_cpu',
                        'elb_count', 'elb_requests', 'elb_latency',
                        'lambda_count', 'lambda_invocations', 'lambda_errors', 'lambda_duration',
                        's3_bucket_count', 's3_object_count', 's3_total_size',
                        'sqs_queue_count', 'sqs_message_count',
                        'security_findings', 'failed_logins', 'vulnerability_count',
                        'network_in', 'network_out', 'packet_loss_percent'
                    ]
                    chart = display_state_timeseries(
                        next_state[-1].reshape(1, -1),  # Just show the latest state
                        feature_names,
                        selected_features=[1, 2, 6, 9, 12, 24]  # Key metrics
                    )
                    chart_container.plotly_chart(chart, use_container_width=True)
                
                # Check for anomaly and apply remediation if needed
                anomaly_score = remediation_env.predictive_model.get_anomaly_score(next_state)
                if anomaly_score > 0.1:  # Threshold for remediation
                    status_container.warning(f"Anomaly detected (score: {anomaly_score:.4f}). Applying remediation...")
                    
                    # Select and apply remediation action
                    remediation_action = remediation_env.select_action(next_state)
                    remediation_description = remediation_env.get_action_description(int(remediation_action.item()))
                    
                    # Apply remediation
                    remediated_state, remediation_reward, remediation_done, remediation_info = remediation_env.step(int(remediation_action.item()))
                    
                    # Record remediation action
                    st.session_state.remediation_actions.append({
                        'step': step,
                        'action': int(remediation_action.item()),
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
            del st.session_state.simulation_state
            del st.session_state.current_step
            
            st.experimental_rerun()
        
        except Exception as e:
            st.error(f"Simulation error: {str(e)}")
            st.session_state.simulation_running = False
            logger.exception("Simulation error")
    
    # Summary of actions (only show if we have actions)
    if st.session_state.chaos_actions:
        st.subheader("Chaos Actions Summary")
        chaos_df = pd.DataFrame(st.session_state.chaos_actions)
        st.dataframe(chaos_df, use_container_width=True)
        
        # Action distribution chart
        action_ids = [a['action'] for a in st.session_state.chaos_actions]
        action_descriptions = {a: d for a, d in [(a['action'], a['description']) for a in st.session_state.chaos_actions]}
        
        if action_ids:
            chaos_chart = display_chaos_action_distribution(action_ids, action_descriptions)
            st.plotly_chart(chaos_chart, use_container_width=True)
    
    # Summary of remediation actions
    if st.session_state.remediation_actions:
        st.subheader("Remediation Actions Summary")
        remediation_df = pd.DataFrame(st.session_state.remediation_actions)
        st.dataframe(remediation_df, use_container_width=True)
        
        # Remediation effectiveness chart
        if len(st.session_state.remediation_actions) > 0:
            effectiveness_chart = display_remediation_effectiveness(st.session_state.remediation_actions)
            st.plotly_chart(effectiveness_chart, use_container_width=True)

# Anomaly detection page
def display_anomaly_detection():
    st.header("Anomaly Detection")
    
    model = load_predictive_model()
    if not model:
        st.error("LSTM Autoencoder model not found. Please train the model first.")
        return
    
    st.subheader("Analyze Infrastructure States")
    
    # Load collected states if they exist
    states_file = "environment_states.npy"
    labels_file = "labels.npy"
    
    if not os.path.exists(states_file):
        st.error(f"State data not found: {states_file}")
        return
    
    states = np.load(states_file)
    labels = np.load(labels_file, allow_pickle=True) if os.path.exists(labels_file) else None
    
    st.info(f"Loaded {len(states)} state samples.")
    
    # Settings
    col1, col2 = st.columns(2)
    
    with col1:
        anomaly_threshold = st.slider(
            "Anomaly Threshold", 
            min_value=0.01, 
            max_value=1.0, 
            value=0.1, 
            step=0.01
        )
    
    with col2:
        sample_size = st.slider(
            "Sample Size", 
            min_value=10, 
            max_value=min(500, len(states)), 
            value=min(100, len(states)),
            step=10
        )
    
    # Prepare sequences for analysis
    sequences = []
    sequence_labels = []
    
    # Create sequences of 5 consecutive states
    for i in range(len(states) - 4):
        if i < sample_size:  # Limit to sample size
            seq = states[i:i+5]
            sequences.append(seq)
            if labels is not None:
                sequence_labels.append(labels[i+4])  # Use the label of the last state in sequence
    
    if not sequences:
        st.warning("No valid sequences found in the data.")
        return
    
    # Calculate anomaly scores
    anomaly_scores = []
    predictions = []
    
    with st.spinner("Calculating anomaly scores..."):
        for seq in sequences:
            score = model.get_anomaly_score(seq)
            anomaly_scores.append(score)
            predictions.append('anomaly' if score > anomaly_threshold else 'normal')
    
    # Display anomaly threshold chart
    st.subheader("Anomaly Scores")
    anomaly_chart = display_anomaly_threshold_chart(anomaly_scores, threshold=anomaly_threshold)
    st.plotly_chart(anomaly_chart, use_container_width=True)
    
    # Metrics about anomalies
    st.subheader("Anomaly Statistics")
    
    metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
    
    with metrics_col1:
        st.metric("Average Score", f"{np.mean(anomaly_scores):.4f}")
    
    with metrics_col2:
        st.metric("Max Score", f"{np.max(anomaly_scores):.4f}")
    
    with metrics_col3:
        anomaly_count = sum(1 for score in anomaly_scores if score > anomaly_threshold)
        st.metric("Anomalies Detected", anomaly_count)
    
    with metrics_col4:
        st.metric("Anomaly Rate", f"{(anomaly_count / len(anomaly_scores) * 100):.1f}%")
    
    # Compare with true labels if available
    if labels is not None and sequence_labels:
        st.subheader("Model Evaluation")
        
        # Convert labels to binary for confusion matrix
        binary_labels = ['anomaly' if label != 'normal' else 'normal' for label in sequence_labels]
        
        # Display confusion matrix
        cm_fig = plot_confusion_matrix(binary_labels, predictions)
        st.plotly_chart(cm_fig, use_container_width=True)
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
        
        with metrics_col1:
            accuracy = accuracy_score(binary_labels, predictions)
            st.metric("Accuracy", f"{accuracy:.4f}")
        
        with metrics_col2:
            precision = precision_score(binary_labels, predictions, pos_label='anomaly')
            st.metric("Precision", f"{precision:.4f}")
        
        with metrics_col3:
            recall = recall_score(binary_labels, predictions, pos_label='anomaly')
            st.metric("Recall", f"{recall:.4f}")
        
        with metrics_col4:
            f1 = f1_score(binary_labels, predictions, pos_label='anomaly')
            st.metric("F1 Score", f"{f1:.4f}")
    
    # Display detailed results
    with st.expander("Detailed Anomaly Results"):
        results_df = pd.DataFrame({
            'Sequence': range(len(anomaly_scores)),
            'Anomaly Score': anomaly_scores,
            'Prediction': predictions
        })
        
        if sequence_labels:
            results_df['True Label'] = sequence_labels
        
        st.dataframe(results_df, use_container_width=True)

# Model training page
def display_model_training():
    st.header("Model Training")
    
    # Use tabs for different training options
    training_tab, data_tab, evaluation_tab = st.tabs([
        "Train Models", 
        "Generate Data", 
        "Evaluate Models"
    ])
    
    with training_tab:
        st.subheader("Train Machine Learning Models")
        
        # Model selection
        model_type = st.selectbox(
            "Select Model to Train",
            ["LSTM Autoencoder", "Chaos Agent", "Remediation Agent", "All Models"]
        )
        
        # Training parameters
        if model_type == "LSTM Autoencoder" or model_type == "All Models":
            lstm_col1, lstm_col2 = st.columns(2)
            with lstm_col1:
                lstm_epochs = st.slider("LSTM Epochs", min_value=10, max_value=500, value=100, step=10)
                lstm_batch_size = st.slider("LSTM Batch Size", min_value=8, max_value=128, value=32, step=8)
            with lstm_col2:
                lstm_lr = st.slider("LSTM Learning Rate", min_value=0.0001, max_value=0.01, value=0.005, step=0.0001, format="%.4f")
                lstm_hidden = st.slider("LSTM Hidden Size", min_value=16, max_value=256, value=64, step=16)
        
        if model_type in ["Chaos Agent", "Remediation Agent", "All Models"]:
            rl_col1, rl_col2 = st.columns(2)
            with rl_col1:
                rl_timesteps = st.slider("RL Training Timesteps", min_value=1000, max_value=100000, value=50000, step=1000)
            with rl_col2:
                rl_lr = st.slider("RL Learning Rate", min_value=0.00001, max_value=0.001, value=0.0001, step=0.00001, format="%.5f")
        
        # Start training button
        if st.button("Start Training"):
            # Validate that we have data
            if not os.path.exists("environment_states.npy"):
                st.error("Training data not found. Please generate data first.")
                return
            
            if model_type == "LSTM Autoencoder" or model_type == "All Models":
                with st.spinner("Training LSTM Autoencoder..."):
                    from train import train_lstm_autoencoder
                    
                    # Create a placeholder for progress updates
                    lstm_progress = st.empty()
                    
                    # Track training history
                    history = {'train_loss': [], 'val_loss': []}
                    
                    # Create a function that will update our progress
                    def progress_update(epoch, epochs, loss):
                        progress = (epoch + 1) / epochs
                        lstm_progress.progress(progress)
                        history['train_loss'].append(loss)
                    
                    try:
                        model, hist = train_lstm_autoencoder(
                            data_path="environment_states.npy",
                            epochs=lstm_epochs,
                            batch_size=lstm_batch_size,
                            learning_rate=lstm_lr,
                            hidden_size=lstm_hidden
                        )
                        
                        # Update with actual history
                        history = hist
                        
                        # Display training curve
                        train_curve = visualize_model_training(history)
                        st.plotly_chart(train_curve, use_container_width=True)
                        
                        st.success("LSTM Autoencoder training completed!")
                    except Exception as e:
                        st.error(f"Error training LSTM: {str(e)}")
                        logger.exception("LSTM training error")
            
            if model_type == "Chaos Agent" or model_type == "All Models":
                with st.spinner("Training Chaos Agent..."):
                    from train import train_rl_agent
                    
                    # Create a placeholder for progress updates
                    chaos_progress = st.empty()
                    
                    try:
                        agent = train_rl_agent(
                            agent_type='chaos',
                            total_timesteps=rl_timesteps,
                            learning_rate=rl_lr
                        )
                        st.success("Chaos Agent training completed!")
                    except Exception as e:
                        st.error(f"Error training Chaos Agent: {str(e)}")
                        logger.exception("Chaos agent training error")
            
            if model_type == "Remediation Agent" or model_type == "All Models":
                with st.spinner("Training Remediation Agent..."):
                    from train import train_rl_agent
                    
                    # Create a placeholder for progress updates
                    remediation_progress = st.empty()
                    
                    try:
                        agent = train_rl_agent(
                            agent_type='remediation',
                            total_timesteps=rl_timesteps,
                            learning_rate=rl_lr
                        )
                        st.success("Remediation Agent training completed!")
                    except Exception as e:
                        st.error(f"Error training Remediation Agent: {str(e)}")
                        logger.exception("Remediation agent training error")
    
    with data_tab:
        st.subheader("Generate Training Data")
        
        # Data generation parameters
        data_col1, data_col2 = st.columns(2)
        
        with data_col1:
            num_samples = st.slider("Number of Samples", min_value=100, max_value=10000, value=5000, step=100)
            temporal = st.checkbox("Use Temporal Correlation", value=True)
        
        with data_col2:
            anomaly_prob = st.slider("Anomaly Probability", min_value=0.0, max_value=1.0, value=0.3, step=0.05)
            save_csv = st.checkbox("Save as CSV", value=True)
        
        # Generate data button
        if st.button("Generate Data"):
            with st.spinner("Generating synthetic states..."):
                from environment import StateCollector
                
                # Create progress bar
                progress_bar = st.progress(0)
                
                # Define progress callback
                def update_progress(progress):
                    progress_bar.progress(progress)
                
                # Generate data
                collector = StateCollector()
                states, labels = collector.collect_samples(
                    num_samples=num_samples,
                    temporal=temporal,
                    anomaly_prob=anomaly_prob,
                    progress_callback=update_progress
                )
                
                # Save data
                csv_file = "environment_states.csv" if save_csv else None
                collector.save_states(
                    filename="environment_states.npy",
                    label_filename="labels.npy",
                    csv_filename=csv_file
                )
                
                # Show success message
                st.success(f"Generated and saved {len(states)} synthetic states!")
                
                # Display sample distribution
                label_counts = {}
                for label in labels:
                    label_counts[label] = label_counts.get(label, 0) + 1
                
                # Create bar chart of label distribution
                fig = px.bar(
                    x=list(label_counts.keys()),
                    y=list(label_counts.values()),
                    labels={'x': 'Scenario', 'y': 'Count'},
                    title="Data Distribution by Scenario"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with evaluation_tab:
        st.subheader("Evaluate Models")
        
        # Choose model to evaluate
        eval_model = st.selectbox(
            "Select Model to Evaluate",
            ["LSTM Autoencoder", "Chaos Agent", "Remediation Agent"]
        )
        
        # LSTM evaluation parameters
        if eval_model == "LSTM Autoencoder":
            eval_threshold = st.slider(
                "Anomaly Threshold", 
                min_value=0.01, 
                max_value=1.0, 
                value=0.1, 
                step=0.01
            )
            
            if st.button("Evaluate LSTM Model"):
                with st.spinner("Evaluating LSTM Autoencoder..."):
                    from train import evaluate_model
                    
                    try:
                        metrics = evaluate_model(
                            model_path="lstm_autoencoder.pth",
                            threshold=eval_threshold
                        )
                        
                        if metrics:
                            # Display evaluation metrics
                            metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
                            
                            with metrics_col1:
                                st.metric("Accuracy", f"{metrics.get('accuracy', 'N/A')}")
                            
                            with metrics_col2:
                                st.metric("Precision", f"{metrics.get('precision', 'N/A')}")
                            
                            with metrics_col3:
                                st.metric("Recall", f"{metrics.get('recall', 'N/A')}")
                            
                            with metrics_col4:
                                st.metric("F1 Score", f"{metrics.get('f1_score', 'N/A')}")
                            
                            # Display confusion matrix if available
                            if 'confusion_matrix' in metrics:
                                st.subheader("Confusion Matrix")
                                cm = np.array(metrics['confusion_matrix'])
                                fig = px.imshow(
                                    cm,
                                    labels=dict(x="Predicted", y="True", color="Count"),
                                    x=['normal', 'anomaly'],
                                    y=['normal', 'anomaly'],
                                    text_auto=True,
                                    color_continuous_scale='Blues'
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            
                            # Display additional metrics
                            st.json({k: v for k, v in metrics.items() if k not in ['confusion_matrix']})
                        else:
                            st.error("Evaluation failed. Check logs for details.")
                    except Exception as e:
                        st.error(f"Error during evaluation: {str(e)}")
                        logger.exception("Evaluation error")

# Logs and analysis page
def display_logs_analysis():
    st.header("Logs & Analysis")
    
    # Tabs for different log types
    chaos_tab, remediation_tab, summary_tab = st.tabs([
        "Chaos Logs", 
        "Remediation Logs", 
        "Experiment Summary"
    ])
    
    with chaos_tab:
        st.subheader("Chaos Action Logs")
        
        # Check if log file exists
        chaos_log_file = "chaos_log.txt"
        if not os.path.exists(chaos_log_file):
            st.info(f"No chaos logs found: {chaos_log_file}")
        else:
            # Parse logs
            chaos_logs = parse_logs(chaos_log_file)
            
            if not chaos_logs:
                st.info("No chaos log entries found.")
            else:
                # Display log count
                st.info(f"Found {len(chaos_logs)} chaos log entries.")
                
                # Create dataframe from logs
                logs_df = pd.DataFrame(chaos_logs)
                
                # Convert timestamp to string for display
                if 'timestamp' in logs_df.columns:
                    logs_df['timestamp'] = logs_df['timestamp'].astype(str)
                
                # Display logs table
                st.dataframe(logs_df, use_container_width=True)
                
                # Plot anomaly scores if available
                if 'anomaly' in logs_df.columns:
                    anomaly_scores = logs_df['anomaly'].tolist()
                    
                    fig = display_anomaly_threshold_chart(anomaly_scores, threshold=0.1)
                    st.plotly_chart(fig, use_container_width=True)
    
    with remediation_tab:
        st.subheader("Remediation Action Logs")
        
        # Check if log file exists
        remediation_log_file = "remediation_log.txt"
        if not os.path.exists(remediation_log_file):
            st.info(f"No remediation logs found: {remediation_log_file}")
        else:
            # Parse logs
            remediation_logs = parse_logs(remediation_log_file)
            
            if not remediation_logs:
                st.info("No remediation log entries found.")
            else:
                # Display log count
                st.info(f"Found {len(remediation_logs)} remediation log entries.")
                
                # Create dataframe from logs
                logs_df = pd.DataFrame(remediation_logs)
                
                # Convert timestamp to string for display
                if 'timestamp' in logs_df.columns:
                    logs_df['timestamp'] = logs_df['timestamp'].astype(str)
                
                # Display logs table
                st.dataframe(logs_df, use_container_width=True)
                
                # Plot remediation effectiveness
                st.subheader("Remediation Effectiveness")
                
                # This function needs to be adapted for the log format
                remediation_data = []
                for log in remediation_logs:
                    # Try to extract before/after anomaly scores
                    data = log.get('data', '')
                    match = re.search(r'Anomaly:\s+([\d.]+)\s+->\s+([\d.]+)', data)
                    if match:
                        before, after = float(match.group(1)), float(match.group(2))
                        remediation_data.append({
                            'action': log.get('action'),
                            'anomaly_before': before,
                            'anomaly_after': after
                        })
                
                if remediation_data:
                    effectiveness_chart = display_remediation_effectiveness(remediation_data)
                    st.plotly_chart(effectiveness_chart, use_container_width=True)
    
    with summary_tab:
        st.subheader("Experiment Summary")
        
        # Generate summary button
        if st.button("Generate Experiment Summary"):
            with st.spinner("Analyzing logs and generating summary..."):
                chaos_log_file = "chaos_log.txt"
                remediation_log_file = "remediation_log.txt"
                
                # Check if log files exist
                if not os.path.exists(chaos_log_file) and not os.path.exists(remediation_log_file):
                    st.warning("No log files found. Run experiments to generate logs.")
                    return
                
                # Parse logs
                chaos_logs = parse_logs(chaos_log_file) if os.path.exists(chaos_log_file) else []
                remediation_logs = parse_logs(remediation_log_file) if os.path.exists(remediation_log_file) else []
                
                # Generate summary
                summary = summarize_experiment(chaos_logs, remediation_logs)
                
                # Display summary
                st.json(summary)
                
                # Create visualizations from summary
                if summary.get('chaos_stats') and summary.get('remediation_stats'):
                    # Create a summary chart
                    st.subheader("Experiment Results")
                    
                    # Remediation effectiveness summary
                    if summary['remediation_stats'].get('avg_anomaly') is not None:
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric(
                                "Avg Anomaly Before", 
                                f"{summary['chaos_stats'].get('avg_anomaly', 0):.4f}"
                            )
                        
                        with col2:
                            st.metric(
                                "Avg Anomaly After", 
                                f"{summary['remediation_stats'].get('avg_anomaly', 0):.4f}",
                                delta=f"-{summary['chaos_stats'].get('avg_anomaly', 0) - summary['remediation_stats'].get('avg_anomaly', 0):.4f}"
                            )
                    
                    # Display findings
                    if summary.get('findings'):
                        st.subheader("Key Findings")
                        for finding in summary['findings']:
                            st.info(finding)

# Run the main app
if __name__ == "__main__":
    main()
