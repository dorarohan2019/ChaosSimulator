import os
import time
import numpy as np
import torch
import matplotlib.pyplot as plt
import pandas as pd
import argparse
import logging
from datetime import datetime

from models.predictive_model import LSTMAutoencoder
from environment import StateCollector
from stable_baselines3 import DQN
from chaos import ChaosEnvironment
from remediation import RemediationEnvironment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("train")

def train_lstm_autoencoder(data_path=None, epochs=100, batch_size=32, learning_rate=0.005, timesteps=5, hidden_size=64):
    """
    Train the LSTM autoencoder for anomaly detection.
    
    Args:
        data_path (str, optional): Path to saved state data. If None, generate synthetic data.
        epochs (int): Number of training epochs.
        batch_size (int): Batch size for training.
        learning_rate (float): Learning rate for optimizer.
        timesteps (int): Number of timesteps in each sequence.
        hidden_size (int): Size of hidden layer in LSTM.
        
    Returns:
        model: Trained LSTM autoencoder.
        history: Training history.
    """
    # Load or generate data
    if data_path and os.path.exists(data_path):
        logger.info(f"Loading data from {data_path}")
        states = np.load(data_path)
    else:
        logger.info("Generating synthetic training data")
        collector = StateCollector()
        states_dicts, labels = collector.collect_samples(
            num_samples=5000, 
            temporal=True, 
            anomaly_prob=0.3
        )
        collector.save_states("environment_states.npy", "labels.npy")
        states = np.array([[state[key] for key in collector.metric_keys] for state in states_dicts])
    
    logger.info(f"Data shape: {states.shape}")
    
    # Create and train model
    model = LSTMAutoencoder(timesteps=timesteps, features=states.shape[1], hidden_size=hidden_size)
    history = model.train_model(
        states, 
        epochs=epochs, 
        step=1, 
        learning_rate=learning_rate, 
        batch_size=batch_size,
        validation_split=0.2
    )
    
    # Save model
    model.save("lstm_autoencoder.pth", "mean.npy", "std.npy")
    logger.info("Model training completed and saved")
    
    return model, history

def train_rl_agent(agent_type='chaos', total_timesteps=50000, learning_rate=0.0001):
    """
    Train a reinforcement learning agent for chaos or remediation.
    
    Args:
        agent_type (str): Type of agent to train ('chaos' or 'remediation').
        total_timesteps (int): Total number of training timesteps.
        learning_rate (float): Learning rate for the agent.
        
    Returns:
        agent: Trained RL agent.
    """
    if agent_type.lower() == 'chaos':
        env = ChaosEnvironment(is_local=True, use_collected_states=True)
        filename = "chaos_agent"
    else:
        env = RemediationEnvironment(is_local=True, use_collected_states=True)
        filename = "remediation_agent"
    
    logger.info(f"Training {agent_type} agent for {total_timesteps} timesteps")
    
    # Create and train agent
    agent = DQN(
        policy="MlpPolicy",
        env=env,
        learning_rate=learning_rate,
        buffer_size=10000,
        learning_starts=1000,
        batch_size=64,
        tau=0.1,
        gamma=0.99,
        train_freq=4,
        gradient_steps=1,
        target_update_interval=1000,
        exploration_fraction=0.2,
        exploration_final_eps=0.05,
        verbose=1
    )
    
    agent.learn(total_timesteps=total_timesteps, log_interval=100)
    
    # Save agent
    agent.save(filename)
    logger.info(f"{agent_type.capitalize()} agent training completed and saved as {filename}")
    
    return agent

def generate_training_data(num_samples=5000, temporal=True, anomaly_prob=0.3, interval=0):
    """
    Generate synthetic training data.
    
    Args:
        num_samples (int): Number of samples to generate.
        temporal (bool): Whether to generate temporally correlated data.
        anomaly_prob (float): Probability of generating anomalous samples.
        interval (float): Time interval between samples.
        
    Returns:
        tuple: (states, labels) - Generated states and corresponding labels.
    """
    logger.info(f"Generating {num_samples} synthetic states with anomaly probability {anomaly_prob}")
    
    collector = StateCollector()
    states, labels = collector.collect_samples(
        num_samples=num_samples,
        temporal=temporal,
        anomaly_prob=anomaly_prob,
        interval=interval
    )
    
    # Save the generated data
    collector.save_states(
        filename="environment_states.npy", 
        label_filename="labels.npy", 
        csv_filename="environment_states.csv"
    )
    
    logger.info(f"Data generation completed. Created {len(states)} samples.")
    
    return states, labels

def evaluate_model(model_path="lstm_autoencoder.pth", test_data_path=None, threshold=0.1):
    """
    Evaluate the trained LSTM autoencoder on test data.
    
    Args:
        model_path (str): Path to saved model.
        test_data_path (str, optional): Path to test data. If None, use a portion of training data.
        threshold (float): Anomaly detection threshold.
        
    Returns:
        dict: Evaluation metrics.
    """
    # Load model
    model = LSTMAutoencoder(timesteps=5, features=25)
    try:
        model.load(model_path, "mean.npy", "std.npy")
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return None
    
    # Load or generate test data
    if test_data_path and os.path.exists(test_data_path):
        logger.info(f"Loading test data from {test_data_path}")
        test_states = np.load(test_data_path)
        try:
            test_labels = np.load(test_data_path.replace('.npy', '_labels.npy'), allow_pickle=True)
        except:
            logger.warning("Could not load test labels, will use anomaly scores only")
            test_labels = None
    else:
        # Generate a small test set
        logger.info("Generating test data")
        collector = StateCollector()
        test_dicts, test_labels = collector.collect_samples(
            num_samples=500, 
            temporal=True, 
            anomaly_prob=0.5  # Higher anomaly probability for testing
        )
        test_states = np.array([[state[key] for key in collector.metric_keys] for state in test_dicts])
    
    # Prepare sequences
    sequences = []
    for i in range(len(test_states) - 4):
        seq = test_states[i:i+5]
        sequences.append(seq)
    
    true_labels = []
    if test_labels is not None:
        for i in range(len(test_labels) - 4):
            # Only mark as anomaly if majority of sequence is anomalous
            is_anomaly = sum(1 for l in test_labels[i:i+5] if l != 'normal') > 2
            true_labels.append('anomaly' if is_anomaly else 'normal')
    
    # Calculate anomaly scores
    anomaly_scores = []
    for seq in sequences:
        score = model.get_anomaly_score(seq)
        anomaly_scores.append(score)
    
    # Apply threshold for prediction
    predictions = ['anomaly' if score > threshold else 'normal' for score in anomaly_scores]
    
    # Calculate metrics if true labels are available
    metrics = {
        'num_samples': len(sequences),
        'anomaly_threshold': threshold,
        'mean_anomaly_score': np.mean(anomaly_scores),
        'max_anomaly_score': max(anomaly_scores),
        'min_anomaly_score': min(anomaly_scores),
        'std_anomaly_score': np.std(anomaly_scores),
        'anomaly_ratio': sum(1 for p in predictions if p == 'anomaly') / len(predictions)
    }
    
    if true_labels:
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
        
        metrics['accuracy'] = accuracy_score(true_labels, predictions)
        metrics['precision'] = precision_score(true_labels, predictions, pos_label='anomaly')
        metrics['recall'] = recall_score(true_labels, predictions, pos_label='anomaly')
        metrics['f1_score'] = f1_score(true_labels, predictions, pos_label='anomaly')
        metrics['confusion_matrix'] = confusion_matrix(
            true_labels, predictions, labels=['normal', 'anomaly']
        ).tolist()
    
    logger.info(f"Evaluation metrics: {metrics}")
    return metrics

def main():
    parser = argparse.ArgumentParser(description='Train models for AWS chaos simulation')
    parser.add_argument('--mode', type=str, default='all', choices=['data', 'lstm', 'chaos', 'remediation', 'all'], 
                        help='Training mode (data generation, lstm, chaos agent, remediation agent, or all)')
    parser.add_argument('--samples', type=int, default=5000, help='Number of samples for data generation')
    parser.add_argument('--epochs', type=int, default=100, help='Number of epochs for LSTM training')
    parser.add_argument('--timesteps', type=int, default=50000, help='Number of timesteps for RL training')
    
    args = parser.parse_args()
    
    if args.mode in ['data', 'all']:
        generate_training_data(num_samples=args.samples)
    
    if args.mode in ['lstm', 'all']:
        train_lstm_autoencoder(data_path="environment_states.npy", epochs=args.epochs)
    
    if args.mode in ['chaos', 'all']:
        train_rl_agent(agent_type='chaos', total_timesteps=args.timesteps)
    
    if args.mode in ['remediation', 'all']:
        train_rl_agent(agent_type='remediation', total_timesteps=args.timesteps)
    
    if args.mode in ['all']:
        evaluate_model()

if __name__ == '__main__':
    main()
