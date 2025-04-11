import time
import os
import numpy as np
import torch
import logging
import json
import threading
from datetime import datetime
import requests

# Import project modules
from chaos import ChaosEnvironment
from remediation import RemediationEnvironment
from utils import setup_localstack, initialize_slack, send_notification, wait_for_approval

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("orchestration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("orchestration")

# Constants
DEFAULT_SLACK_CHANNEL = "#chaos-engineering"
APPROVAL_TIMEOUT = 3600  # 1 hour timeout for approvals

def run_chaos_simulation(num_actions=5, slack_token=None, is_local=True, 
                        use_collected_states=True, approval_required=True,
                        progress_callback=None):
    """
    Orchestrates a chaos simulation with remediation.
    
    Args:
        num_actions (int): Number of chaos actions to perform.
        slack_token (str): Slack token for notifications.
        is_local (bool): Whether to use LocalStack or real AWS.
        use_collected_states (bool): Whether to use collected states.
        approval_required (bool): Whether to require approval before running.
        progress_callback (callable): Function to call with progress updates.
        
    Returns:
        dict: Summary of simulation results.
    """
    # Initialize results
    results = {
        "status": "preparing",
        "start_time": datetime.now().isoformat(),
        "chaos_actions": [],
        "remediation_actions": [],
        "anomalies_detected": 0,
        "anomalies_remediated": 0
    }
    
    # Initialize Slack if token provided
    slack_client = None
    if slack_token:
        slack_client = initialize_slack(slack_token)
        
    # Initialize environments
    try:
        # Verify LocalStack is running if using it
        if is_local and not setup_localstack():
            error_msg = "LocalStack is not running. Cannot start simulation."
            logger.error(error_msg)
            results["status"] = "failed"
            results["error"] = error_msg
            
            if slack_client:
                send_notification(slack_client, DEFAULT_SLACK_CHANNEL, 
                                 f"❌ Chaos simulation failed: {error_msg}")
            return results
            
        chaos_env = ChaosEnvironment(is_local=is_local, use_collected_states=use_collected_states, load_model=True)
        remediation_env = RemediationEnvironment(is_local=is_local, use_collected_states=use_collected_states, load_model=True)
        
        # Request approval if needed
        if approval_required and slack_client:
            results["status"] = "awaiting_approval"
            
            # Send approval request
            approval_message = (
                "🧪 *Chaos and remediation simulation is ready to start*\n"
                f"• Number of actions: {num_actions}\n"
                f"• Environment: {'LocalStack' if is_local else 'AWS'}\n\n"
                "Reply with 'approve' to proceed or 'deny' to cancel."
            )
            
            response = send_notification(slack_client, DEFAULT_SLACK_CHANNEL, approval_message)
            
            if response and 'ts' in response:
                thread_ts = response['ts']
                logger.info(f"Approval requested. Waiting for response. Thread TS: {thread_ts}")
                
                # Update progress if callback provided
                if progress_callback:
                    progress_callback(0, "Waiting for approval")
                
                # Wait for approval
                approval_status = wait_for_approval(
                    slack_client, 
                    DEFAULT_SLACK_CHANNEL, 
                    thread_ts, 
                    APPROVAL_TIMEOUT
                )
                
                if approval_status != 'approved':
                    # Approval denied or timed out
                    deny_message = f"⚠️ Chaos simulation cancelled: {approval_status}"
                    send_notification(slack_client, DEFAULT_SLACK_CHANNEL, deny_message)
                    
                    results["status"] = "cancelled"
                    results["reason"] = approval_status
                    return results
                
                # Approval granted
                approved_message = "✅ Chaos simulation approved! Starting now."
                send_notification(slack_client, DEFAULT_SLACK_CHANNEL, approved_message)
            else:
                logger.warning("Failed to send approval request. Proceeding without approval.")
        
        # Start simulation
        results["status"] = "running"
        logger.info(f"Starting chaos simulation with {num_actions} actions")
        
        if slack_client:
            send_notification(slack_client, DEFAULT_SLACK_CHANNEL, 
                            f"🚀 Chaos simulation started with {num_actions} actions")
        
        # Reset environments to get initial state
        state = chaos_env.reset()
        
        # Run simulation steps
        for step in range(num_actions):
            # Update progress if callback provided
            if progress_callback:
                progress_callback((step + 1) / num_actions, f"Running chaos action {step + 1}/{num_actions}")
            
            # Select and execute chaos action
            action = chaos_env.select_action(state)
            action_int = int(action.item())
            action_desc = chaos_env.get_action_description(action_int)
            
            logger.info(f"Step {step + 1}/{num_actions}: Executing chaos action: {action_desc}")
            
            # Execute chaos action
            next_state, chaos_reward, done, chaos_info = chaos_env.step(action_int)
            
            # Record chaos action details
            anomaly_score = chaos_info.get('anomaly_score', 0)
            chaos_action_data = {
                "step": step + 1,
                "action": action_int,
                "description": action_desc,
                "reward": float(chaos_reward),
                "anomaly_score": float(anomaly_score),
                "timestamp": datetime.now().isoformat()
            }
            results["chaos_actions"].append(chaos_action_data)
            
            # Notify about chaos action
            action_message = (
                f"🔥 *Chaos Action {step+1}/{num_actions}*: {action_desc}\n"
                f"• Anomaly Score: {anomaly_score:.4f}\n"
                f"• Reward: {chaos_reward:.4f}"
            )
            
            if slack_client:
                send_notification(slack_client, DEFAULT_SLACK_CHANNEL, action_message)
            
            # Check if remediation is needed
            if anomaly_score > 0.1:  # Threshold for remediation
                results["anomalies_detected"] += 1
                
                logger.info(f"Anomaly detected (score: {anomaly_score:.4f}). Applying remediation.")
                
                # Select and apply remediation action
                remediation_action = remediation_env.select_action(next_state)
                remediation_action_int = int(remediation_action.item())
                remediation_desc = remediation_env.get_action_description(remediation_action_int)
                
                # Execute remediation
                remediated_state, remediation_reward, remediation_done, remediation_info = remediation_env.step(remediation_action_int)
                
                # Calculate effectiveness
                anomaly_after = remediation_info.get('anomaly_after', 0)
                improvement = anomaly_score - anomaly_after
                
                # Record remediation action
                remediation_data = {
                    "step": step + 1,
                    "action": remediation_action_int,
                    "description": remediation_desc,
                    "reward": float(remediation_reward),
                    "anomaly_before": float(anomaly_score),
                    "anomaly_after": float(anomaly_after),
                    "improvement": float(improvement),
                    "timestamp": datetime.now().isoformat()
                }
                results["remediation_actions"].append(remediation_data)
                
                # Notify about remediation
                remediation_message = (
                    f"🔧 *Remediation Applied*: {remediation_desc}\n"
                    f"• Anomaly Before: {anomaly_score:.4f}\n"
                    f"• Anomaly After: {anomaly_after:.4f}\n"
                    f"• Improvement: {improvement:.4f}\n"
                    f"• Reward: {remediation_reward:.4f}"
                )
                
                if slack_client:
                    send_notification(slack_client, DEFAULT_SLACK_CHANNEL, remediation_message)
                
                # Check if remediation was successful
                if anomaly_after < 0.1:
                    results["anomalies_remediated"] += 1
                
                # Use remediated state as the new state
                state = remediated_state
            else:
                # No remediation needed
                state = next_state
            
            # Check if simulation should end early
            if done:
                logger.warning("Simulation ended early due to critical failure.")
                
                if slack_client:
                    send_notification(slack_client, DEFAULT_SLACK_CHANNEL, 
                                     "⚠️ Simulation ended early due to critical failure.")
                break
            
            # Add a delay between steps for real-time monitoring
            time.sleep(1)
        
        # Simulation completed
        results["status"] = "completed"
        results["end_time"] = datetime.now().isoformat()
        
        # Calculate summary statistics
        results["summary"] = {
            "total_chaos_actions": len(results["chaos_actions"]),
            "total_remediation_actions": len(results["remediation_actions"]),
            "anomaly_detection_rate": results["anomalies_detected"] / num_actions if num_actions > 0 else 0,
            "remediation_success_rate": results["anomalies_remediated"] / results["anomalies_detected"] if results["anomalies_detected"] > 0 else 0
        }
        
        logger.info(f"Simulation completed. {results['anomalies_remediated']}/{results['anomalies_detected']} anomalies remediated.")
        
        # Send completion notification
        if slack_client:
            completion_message = (
                "✅ *Chaos simulation completed*\n"
                f"• Actions performed: {len(results['chaos_actions'])}\n"
                f"• Anomalies detected: {results['anomalies_detected']}\n"
                f"• Anomalies remediated: {results['anomalies_remediated']}\n"
                f"• Success rate: {results['summary']['remediation_success_rate']:.2%}"
            )
            send_notification(slack_client, DEFAULT_SLACK_CHANNEL, completion_message)
        
        return results
    
    except Exception as e:
        error_msg = f"Error during chaos simulation: {str(e)}"
        logger.exception(error_msg)
        
        results["status"] = "failed"
        results["error"] = error_msg
        results["end_time"] = datetime.now().isoformat()
        
        if slack_client:
            send_notification(slack_client, DEFAULT_SLACK_CHANNEL, 
                             f"❌ Chaos simulation failed: {error_msg}")
        
        return results

def run_simulation_in_thread(num_actions=5, slack_token=None, is_local=True, 
                           use_collected_states=True, approval_required=True,
                           callback=None):
    """
    Run chaos simulation in a separate thread.
    
    Args:
        num_actions (int): Number of chaos actions to perform.
        slack_token (str): Slack token for notifications.
        is_local (bool): Whether to use LocalStack or real AWS.
        use_collected_states (bool): Whether to use collected states.
        approval_required (bool): Whether to require approval before running.
        callback (callable): Function to call with results when complete.
    
    Returns:
        threading.Thread: The simulation thread.
    """
    def run_simulation_thread():
        results = run_chaos_simulation(
            num_actions=num_actions,
            slack_token=slack_token,
            is_local=is_local,
            use_collected_states=use_collected_states,
            approval_required=approval_required
        )
        
        if callback:
            callback(results)
    
    simulation_thread = threading.Thread(target=run_simulation_thread)
    simulation_thread.daemon = True
    simulation_thread.start()
    
    return simulation_thread

if __name__ == "__main__":
    # Get Slack token from environment
    slack_token = os.environ.get("SLACK_TOKEN")
    
    # Run simulation with 5 actions
    results = run_chaos_simulation(
        num_actions=5,
        slack_token=slack_token,
        is_local=True,
        use_collected_states=True,
        approval_required=True
    )
    
    # Save results to file
    with open("simulation_results.json", "w") as f:
        json.dump(results, f, indent=2)
