import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import io
import time
import os
from datetime import datetime, timedelta

def display_anomaly_threshold_chart(anomaly_scores, threshold=0.1):
    """
    Display a chart showing anomaly scores and threshold.
    
    Args:
        anomaly_scores (list): List of anomaly scores.
        threshold (float): Threshold for anomaly detection.
    """
    fig = go.Figure()
    
    # Add anomaly scores
    fig.add_trace(go.Scatter(
        x=list(range(len(anomaly_scores))),
        y=anomaly_scores,
        mode='lines+markers',
        name='Anomaly Score',
        line=dict(color='blue')
    ))
    
    # Add threshold line
    fig.add_trace(go.Scatter(
        x=[0, len(anomaly_scores) - 1],
        y=[threshold, threshold],
        mode='lines',
        name='Threshold',
        line=dict(color='red', dash='dash')
    ))
    
    # Highlight anomalies
    anomaly_indices = [i for i, score in enumerate(anomaly_scores) if score > threshold]
    anomaly_scores_filtered = [anomaly_scores[i] for i in anomaly_indices]
    
    if anomaly_indices:
        fig.add_trace(go.Scatter(
            x=anomaly_indices,
            y=anomaly_scores_filtered,
            mode='markers',
            name='Anomalies',
            marker=dict(color='red', size=10)
        ))
    
    # Set layout
    fig.update_layout(
        title='Anomaly Detection',
        xaxis_title='Time Step',
        yaxis_title='Anomaly Score',
        hovermode='closest',
        template='plotly_white'
    )
    
    return fig

def display_state_timeseries(states, feature_names=None, selected_features=None):
    """
    Display time series chart of selected features from states.
    
    Args:
        states (np.ndarray): Array of states with shape (time_steps, features).
        feature_names (list): Names of features.
        selected_features (list): Indices of features to display.
    """
    if feature_names is None:
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
    
    if selected_features is None:
        selected_features = [1, 2, 6, 9, 12, 19, 24]  # Default important features
    
    # Create time labels
    time_steps = np.arange(states.shape[0])
    
    # Create figure
    fig = go.Figure()
    
    # Add traces for selected features
    for idx in selected_features:
        if idx < states.shape[1]:
            feature_name = feature_names[idx] if idx < len(feature_names) else f"Feature {idx}"
            fig.add_trace(go.Scatter(
                x=time_steps,
                y=states[:, idx],
                mode='lines',
                name=feature_name
            ))
    
    # Set layout
    fig.update_layout(
        title='State Metrics Over Time',
        xaxis_title='Time Step',
        yaxis_title='Value',
        hovermode='x unified',
        template='plotly_white',
        height=500
    )
    
    return fig

def display_chaos_action_distribution(actions, action_descriptions=None):
    """
    Display distribution of chaos actions.
    
    Args:
        actions (list): List of action indices.
        action_descriptions (dict): Mapping of action indices to descriptions.
    """
    if not actions:
        return go.Figure()
    
    # Count actions
    action_counts = {}
    for action in actions:
        action_counts[action] = action_counts.get(action, 0) + 1
    
    # Sort by frequency
    sorted_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Create labels
    labels = []
    for action, _ in sorted_actions:
        if action_descriptions and action in action_descriptions:
            labels.append(f"{action}: {action_descriptions[action]}")
        else:
            labels.append(f"Action {action}")
    
    # Create figure
    fig = go.Figure(go.Bar(
        x=[count for _, count in sorted_actions],
        y=labels,
        orientation='h'
    ))
    
    # Set layout
    fig.update_layout(
        title='Chaos Action Distribution',
        xaxis_title='Count',
        yaxis_title='Action',
        template='plotly_white',
        height=max(400, len(sorted_actions) * 30)
    )
    
    return fig

def display_remediation_effectiveness(remediation_logs):
    """
    Display effectiveness of remediation actions.
    
    Args:
        remediation_logs (list): List of remediation log entries.
    """
    if not remediation_logs:
        return go.Figure()
    
    # Extract data
    actions = []
    before_scores = []
    after_scores = []
    improvements = []
    
    for log in remediation_logs:
        action = log.get('action')
        before = log.get('anomaly_before')
        after = log.get('anomaly_after')
        
        if action is not None and before is not None and after is not None:
            actions.append(action)
            before_scores.append(before)
            after_scores.append(after)
            improvements.append(before - after)
    
    if not actions:
        return go.Figure()
    
    # Create figure with two y-axes
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add before/after scores
    fig.add_trace(
        go.Scatter(
            x=list(range(len(actions))),
            y=before_scores,
            mode='lines+markers',
            name='Before Remediation',
            line=dict(color='red')
        ),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(
            x=list(range(len(actions))),
            y=after_scores,
            mode='lines+markers',
            name='After Remediation',
            line=dict(color='green')
        ),
        secondary_y=False
    )
    
    # Add improvement bars
    fig.add_trace(
        go.Bar(
            x=list(range(len(actions))),
            y=improvements,
            name='Improvement',
            marker_color='blue',
            opacity=0.5
        ),
        secondary_y=True
    )
    
    # Set titles
    fig.update_layout(
        title='Remediation Effectiveness',
        hovermode='x unified',
        template='plotly_white'
    )
    
    # Set x-axis title
    fig.update_xaxes(title_text="Remediation Action Sequence")
    
    # Set y-axes titles
    fig.update_yaxes(title_text="Anomaly Score", secondary_y=False)
    fig.update_yaxes(title_text="Improvement", secondary_y=True)
    
    return fig

def display_live_metrics_chart(history):
    """
    Display live metrics chart from streaming data.
    
    Args:
        history (dict): Dictionary with keys as metric names and values as lists of metric values.
    """
    if not history or not all(history.values()):
        return go.Figure()
    
    # Create time labels
    time_steps = list(range(len(next(iter(history.values())))))
    
    # Create figure
    fig = go.Figure()
    
    # Add traces for all metrics
    for metric_name, values in history.items():
        fig.add_trace(go.Scatter(
            x=time_steps,
            y=values,
            mode='lines',
            name=metric_name
        ))
    
    # Set layout
    fig.update_layout(
        title='Live System Metrics',
        xaxis_title='Time Step',
        yaxis_title='Value',
        hovermode='x unified',
        template='plotly_white',
        height=400
    )
    
    return fig

def plot_confusion_matrix(state_labels, predicted_labels):
    """
    Create a confusion matrix visualization for anomaly detection.
    
    Args:
        state_labels (list): True labels (normal/anomaly).
        predicted_labels (list): Predicted labels (normal/anomaly).
    """
    if not state_labels or not predicted_labels:
        return go.Figure()
    
    # Convert to binary classification for confusion matrix
    # normal = 0, anomaly = 1
    true_binary = [0 if label == 'normal' else 1 for label in state_labels]
    pred_binary = [0 if label == 'normal' else 1 for label in predicted_labels]
    
    # Compute confusion matrix
    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(true_binary, pred_binary)
    
    # Create the heatmap
    labels = ['Normal', 'Anomaly']
    fig = px.imshow(
        cm,
        x=labels,
        y=labels,
        color_continuous_scale='Blues',
        labels=dict(x="Predicted", y="True", color="Count"),
        title="Anomaly Detection Confusion Matrix"
    )
    
    # Add text annotations
    annotations = []
    for i in range(2):
        for j in range(2):
            annotations.append({
                'x': j,
                'y': i,
                'text': str(cm[i, j]),
                'font': {'color': 'white' if cm[i, j] > cm.max() / 2 else 'black'},
                'showarrow': False
            })
    
    fig.update_layout(annotations=annotations)
    
    return fig

def visualize_model_training(history):
    """
    Visualize model training history.
    
    Args:
        history (dict): Training history with loss metrics.
    """
    if not history:
        return go.Figure()
    
    fig = go.Figure()
    
    # Add training loss
    if 'train_loss' in history:
        fig.add_trace(go.Scatter(
            x=list(range(1, len(history['train_loss']) + 1)),
            y=history['train_loss'],
            mode='lines',
            name='Training Loss'
        ))
    
    # Add validation loss if available
    if 'val_loss' in history:
        fig.add_trace(go.Scatter(
            x=list(range(1, len(history['val_loss']) + 1)),
            y=history['val_loss'],
            mode='lines',
            name='Validation Loss'
        ))
    
    # Set layout
    fig.update_layout(
        title='Model Training History',
        xaxis_title='Epoch',
        yaxis_title='Loss',
        hovermode='x unified',
        template='plotly_white'
    )
    
    return fig

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

def plot_service_health(metrics):
    """
    Plot AWS service health metrics.
    
    Args:
        metrics (dict): Dictionary of service metrics.
    """
    # Define service categories and their metrics
    services = {
        "EC2": ["ec2_running", "ec2_cpu_avg"],
        "RDS": ["rds_available", "rds_cpu"],
        "Lambda": ["lambda_errors", "lambda_duration"],
        "S3": ["s3_object_count"],
        "Network": ["packet_loss_percent", "elb_latency"],
        "Security": ["security_findings", "failed_logins"]
    }
    
    # Calculate health score for each service (0-100)
    health_scores = {}
    
    # EC2 health: 100 if all instances running and CPU < 70%
    if "ec2_running" in metrics and "ec2_count" in metrics and "ec2_cpu_avg" in metrics:
        ec2_ratio = metrics["ec2_running"] / max(1, metrics["ec2_count"])
        cpu_factor = max(0, 1 - metrics["ec2_cpu_avg"] / 100)
        health_scores["EC2"] = int(100 * ec2_ratio * (0.5 + 0.5 * cpu_factor))
    else:
        health_scores["EC2"] = 50  # Default if metrics missing
    
    # RDS health: 100 if all instances available and CPU < 70%
    if "rds_available" in metrics and "rds_count" in metrics and "rds_cpu" in metrics:
        rds_ratio = metrics["rds_available"] / max(1, metrics["rds_count"])
        cpu_factor = max(0, 1 - metrics["rds_cpu"] / 100)
        health_scores["RDS"] = int(100 * rds_ratio * (0.5 + 0.5 * cpu_factor))
    else:
        health_scores["RDS"] = 50
    
    # Lambda health: 100 if errors < 1 and duration < 500ms
    if "lambda_errors" in metrics and "lambda_duration" in metrics:
        error_factor = max(0, 1 - metrics["lambda_errors"] / 10)
        duration_factor = max(0, 1 - metrics["lambda_duration"] / 1000)
        health_scores["Lambda"] = int(100 * error_factor * duration_factor)
    else:
        health_scores["Lambda"] = 50
    
    # S3 health: Always 100 unless specific issue
    health_scores["S3"] = 100
    
    # Network health: 100 if no packet loss and low latency
    if "packet_loss_percent" in metrics and "elb_latency" in metrics:
        packet_factor = max(0, 1 - metrics["packet_loss_percent"] / 10)
        latency_factor = max(0, 1 - metrics["elb_latency"] / 1)
        health_scores["Network"] = int(100 * packet_factor * latency_factor)
    else:
        health_scores["Network"] = 50
    
    # Security health: 100 if no findings or failed logins
    if "security_findings" in metrics and "failed_logins" in metrics:
        security_factor = max(0, 1 - metrics["security_findings"] / 20)
        login_factor = max(0, 1 - metrics["failed_logins"] / 50)
        health_scores["Security"] = int(100 * security_factor * login_factor)
    else:
        health_scores["Security"] = 50
    
    # Create the gauge chart
    fig = make_subplots(
        rows=2, 
        cols=3,
        specs=[
            [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}],
            [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]
        ],
        subplot_titles=list(services.keys())
    )
    
    # Add gauge for each service
    service_list = list(services.keys())
    for i, service in enumerate(service_list):
        row = i // 3 + 1
        col = i % 3 + 1
        
        # Determine color based on health score
        if health_scores[service] >= 80:
            color = "green"
        elif health_scores[service] >= 50:
            color = "orange"
        else:
            color = "red"
        
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=health_scores[service],
                domain={'row': row, 'column': col},
                title={'text': service},
                gauge={
                    'axis': {'range': [0, 100]},
                    'bar': {'color': color},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "gray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 50
                    }
                }
            ),
            row=row, col=col
        )
    
    fig.update_layout(
        height=500,
        grid={'rows': 2, 'columns': 3, 'pattern': "independent"},
        template='plotly_white'
    )
    
    return fig
