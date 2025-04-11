import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import torch
import boto3
import logging
import time
import json
import re
from datetime import datetime, timedelta
import requests
from io import StringIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("utils")

def setup_localstack():
    """
    Initialize LocalStack and verify its status.
    
    Returns:
        bool: True if LocalStack is running properly.
    """
    try:
        endpoint_url = 'http://localhost:4566'
        session = boto3.Session(
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy',
            region_name='us-east-1'
        )
        s3 = session.client('s3', endpoint_url=endpoint_url)
        s3.list_buckets()
        logger.info("LocalStack is running and accessible.")
        return True
    except Exception as e:
        logger.error(f"LocalStack error: {e}")
        return False

def provision_localstack_resources(endpoint_url='http://localhost:4566'):
    """
    Provision minimal AWS resources in LocalStack for chaos testing.
    
    Args:
        endpoint_url (str): LocalStack endpoint URL.
        
    Returns:
        dict: Information about created resources.
    """
    session = boto3.Session(
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy',
        region_name='us-east-1'
    )
    
    created_resources = {}
    
    # Create EC2 instances
    try:
        ec2 = session.client('ec2', endpoint_url=endpoint_url)
        response = ec2.run_instances(
            ImageId='ami-12345678',
            MinCount=1,
            MaxCount=3,
            InstanceType='t2.micro',
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [{'Key': 'Name', 'Value': 'ChaosTest'}]
                }
            ]
        )
        created_resources['ec2_instances'] = [inst['InstanceId'] for inst in response['Instances']]
        logger.info(f"Created EC2 instances: {created_resources['ec2_instances']}")
    except Exception as e:
        logger.error(f"Error creating EC2 instances: {e}")
    
    # Create S3 bucket
    try:
        s3 = session.client('s3', endpoint_url=endpoint_url)
        bucket_name = 'chaos-test-bucket'
        s3.create_bucket(Bucket=bucket_name)
        
        # Upload a few test objects
        for i in range(5):
            object_data = f"Test object {i}"
            s3.put_object(Bucket=bucket_name, Key=f"test-object-{i}.txt", Body=object_data)
        
        created_resources['s3_bucket'] = bucket_name
        logger.info(f"Created S3 bucket: {bucket_name}")
    except Exception as e:
        logger.error(f"Error creating S3 bucket: {e}")
    
    # Create DynamoDB table
    try:
        dynamodb = session.client('dynamodb', endpoint_url=endpoint_url)
        table_name = 'ChaosTable'
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        created_resources['dynamodb_table'] = table_name
        logger.info(f"Created DynamoDB table: {table_name}")
    except Exception as e:
        logger.error(f"Error creating DynamoDB table: {e}")
    
    # Create Lambda function
    try:
        lambda_client = session.client('lambda', endpoint_url=endpoint_url)
        function_name = 'ChaosFunction'
        
        # Create a simple Lambda function
        lambda_code = """
        exports.handler = async (event) => {
            return {
                statusCode: 200,
                body: JSON.stringify('Hello from Lambda!'),
            };
        };
        """
        
        # Create zip file in memory
        import io
        import zipfile
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'a') as zip_file:
            zip_file.writestr('index.js', lambda_code)
        zip_buffer.seek(0)
        
        # Create Lambda function
        lambda_client.create_function(
            FunctionName=function_name,
            Runtime='nodejs14.x',
            Role='arn:aws:iam::123456789012:role/lambda-role',
            Handler='index.handler',
            Code={'ZipFile': zip_buffer.read()},
            Timeout=30,
            MemorySize=128
        )
        created_resources['lambda_function'] = function_name
        logger.info(f"Created Lambda function: {function_name}")
    except Exception as e:
        logger.error(f"Error creating Lambda function: {e}")
    
    return created_resources

def initialize_slack(token=None):
    """
    Initialize the Slack client for notifications.
    
    Args:
        token (str, optional): Slack API token.
        
    Returns:
        object: Slack client or None.
    """
    if token is None:
        token = os.environ.get("SLACK_TOKEN")
    
    if not token:
        logger.warning("Slack token not provided. Notifications will be disabled.")
        return None
    
    try:
        from slack_sdk import WebClient
        client = WebClient(token=token)
        client.auth_test()
        logger.info("Slack client initialized successfully.")
        return client
    except Exception as e:
        logger.error(f"Error initializing Slack client: {e}")
        return None

def send_notification(client, channel, message, blocks=None):
    """
    Send a notification to Slack.
    
    Args:
        client: Slack client.
        channel (str): Channel to send the message to.
        message (str): Message text.
        blocks (list, optional): Message blocks for rich formatting.
        
    Returns:
        dict: Response from Slack API.
    """
    if client is None:
        logger.warning(f"Slack notification not sent: {message}")
        return None
    
    try:
        if blocks:
            response = client.chat_postMessage(channel=channel, text=message, blocks=blocks)
        else:
            response = client.chat_postMessage(channel=channel, text=message)
        
        logger.info(f"Notification sent to {channel}")
        return response
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return None

def wait_for_approval(client, channel, thread_ts, timeout=3600):
    """
    Wait for user approval in Slack.
    
    Args:
        client: Slack client.
        channel (str): Channel where the approval message was sent.
        thread_ts (str): Timestamp of the approval message.
        timeout (int): Maximum time to wait in seconds.
        
    Returns:
        str: 'approved', 'denied', or 'timeout'.
    """
    if client is None:
        logger.warning("Approval request skipped - no Slack client.")
        return 'approved'  # Auto-approve if no Slack
    
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        try:
            # Get replies to the thread
            response = client.conversations_replies(
                channel=channel,
                ts=thread_ts
            )
            
            # Check replies for approval/denial
            for message in response.get('messages', []):
                if message.get('ts') != thread_ts:  # Skip the original message
                    text = message.get('text', '').lower()
                    if 'approve' in text:
                        return 'approved'
                    elif 'deny' in text or 'reject' in text:
                        return 'denied'
            
            # Wait before checking again
            time.sleep(30)
        
        except Exception as e:
            logger.error(f"Error checking for approval: {e}")
            time.sleep(60)
    
    return 'timeout'

def parse_logs(log_file, timeframe=None):
    """
    Parse log files and extract structured data.
    
    Args:
        log_file (str): Path to log file.
        timeframe (tuple, optional): (start_time, end_time) as datetime objects.
        
    Returns:
        list: Parsed log entries.
    """
    if not os.path.exists(log_file):
        logger.warning(f"Log file not found: {log_file}")
        return []
    
    entries = []
    
    try:
        with open(log_file, 'r') as f:
            for line in f:
                # Extract timestamp and log data
                match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+),\s+(.*)', line)
                if match:
                    timestamp_str, data = match.groups()
                    timestamp = datetime.fromisoformat(timestamp_str)
                    
                    # Apply timeframe filter if provided
                    if timeframe:
                        start_time, end_time = timeframe
                        if timestamp < start_time or timestamp > end_time:
                            continue
                    
                    # Extract action, anomaly score, reward info
                    action_match = re.search(r'Action:\s+(\d+)', data)
                    anomaly_match = re.search(r'Anomaly:\s+([\d.]+)', data)
                    reward_match = re.search(r'Reward:\s+([-\d.]+)', data)
                    
                    entry = {
                        'timestamp': timestamp,
                        'data': data
                    }
                    
                    if action_match:
                        entry['action'] = int(action_match.group(1))
                    
                    if anomaly_match:
                        entry['anomaly'] = float(anomaly_match.group(1))
                    
                    if reward_match:
                        entry['reward'] = float(reward_match.group(1))
                    
                    entries.append(entry)
    
    except Exception as e:
        logger.error(f"Error parsing log file {log_file}: {e}")
    
    return entries

def summarize_experiment(chaos_logs, remediation_logs):
    """
    Summarize chaos and remediation experiment results.
    
    Args:
        chaos_logs (list): Parsed chaos log entries.
        remediation_logs (list): Parsed remediation log entries.
        
    Returns:
        dict: Summary statistics and insights.
    """
    if not chaos_logs and not remediation_logs:
        return {"error": "No log data available"}
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_chaos_actions": len(chaos_logs),
        "total_remediation_actions": len(remediation_logs),
        "chaos_stats": {},
        "remediation_stats": {},
        "findings": []
    }
    
    # Chaos action statistics
    if chaos_logs:
        chaos_actions = {}
        chaos_rewards = []
        chaos_anomalies = []
        
        for log in chaos_logs:
            action = log.get('action')
            if action is not None:
                chaos_actions[action] = chaos_actions.get(action, 0) + 1
            
            reward = log.get('reward')
            if reward is not None:
                chaos_rewards.append(reward)
            
            anomaly = log.get('anomaly')
            if anomaly is not None:
                chaos_anomalies.append(anomaly)
        
        summary["chaos_stats"] = {
            "most_common_actions": sorted(chaos_actions.items(), key=lambda x: x[1], reverse=True)[:5],
            "avg_reward": np.mean(chaos_rewards) if chaos_rewards else None,
            "max_reward": max(chaos_rewards) if chaos_rewards else None,
            "avg_anomaly": np.mean(chaos_anomalies) if chaos_anomalies else None,
            "max_anomaly": max(chaos_anomalies) if chaos_anomalies else None
        }
    
    # Remediation action statistics
    if remediation_logs:
        remediation_actions = {}
        remediation_rewards = []
        remediation_anomalies = []
        
        for log in remediation_logs:
            action = log.get('action')
            if action is not None:
                remediation_actions[action] = remediation_actions.get(action, 0) + 1
            
            reward = log.get('reward')
            if reward is not None:
                remediation_rewards.append(reward)
            
            anomaly = log.get('anomaly')
            if anomaly is not None:
                remediation_anomalies.append(anomaly)
        
        summary["remediation_stats"] = {
            "most_common_actions": sorted(remediation_actions.items(), key=lambda x: x[1], reverse=True)[:5],
            "avg_reward": np.mean(remediation_rewards) if remediation_rewards else None,
            "max_reward": max(remediation_rewards) if remediation_rewards else None,
            "avg_anomaly": np.mean(remediation_anomalies) if remediation_anomalies else None,
            "min_anomaly": min(remediation_anomalies) if remediation_anomalies else None
        }
    
    # Generate insights
    findings = []
    
    if chaos_logs and remediation_logs:
        # Check if remediation was effective
        if (summary["remediation_stats"].get("avg_anomaly", 0) < 
            summary["chaos_stats"].get("avg_anomaly", float('inf'))):
            findings.append("Remediation actions were effective at reducing anomaly scores")
        else:
            findings.append("Remediation actions were not effective at reducing anomaly scores")
        
        # Check most problematic actions
        if summary["chaos_stats"].get("most_common_actions"):
            top_chaos = summary["chaos_stats"]["most_common_actions"][0]
            findings.append(f"Most frequent chaos action was {top_chaos[0]} (used {top_chaos[1]} times)")
        
        # Check most effective remediation
        if summary["remediation_stats"].get("most_common_actions"):
            top_remediation = summary["remediation_stats"]["most_common_actions"][0]
            findings.append(f"Most frequent remediation action was {top_remediation[0]} (used {top_remediation[1]} times)")
    
    summary["findings"] = findings
    return summary

def format_summary_for_slack(summary):
    """
    Format experiment summary for Slack notification.
    
    Args:
        summary (dict): Experiment summary.
        
    Returns:
        list: Slack blocks for formatting.
    """
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Chaos Engineering Experiment Summary"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Experiment completed at:* {summary.get('timestamp')}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Total Chaos Actions:* {summary.get('total_chaos_actions', 0)}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Total Remediation Actions:* {summary.get('total_remediation_actions', 0)}"
                }
            ]
        }
    ]
    
    # Add findings
    if summary.get('findings'):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Key Findings:*"
            }
        })
        
        findings_text = "\n".join([f"• {finding}" for finding in summary.get('findings', [])])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": findings_text
            }
        })
    
    return blocks
