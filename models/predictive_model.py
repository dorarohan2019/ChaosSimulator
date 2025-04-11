import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import os

class LSTMAutoencoder(nn.Module):
    def __init__(self, timesteps=5, features=25, hidden_size=64):
        """Initialize the LSTM Autoencoder model.

        Args:
            timesteps (int): Number of timesteps in each sequence.
            features (int): Number of features in the input data.
            hidden_size (int): Size of the hidden layer.
        """
        super(LSTMAutoencoder, self).__init__()
        self.timesteps = timesteps
        self.features = features
        self.hidden_size = hidden_size
        self.mean = 0.0  # Default value
        self.std = 1.0   # Default value
        
        # Encoder: LSTM to compress input
        self.encoder = nn.LSTM(input_size=features, 
                               hidden_size=hidden_size, 
                               batch_first=True)
        
        # Decoder: LSTM to reconstruct from encoded representation
        self.decoder = nn.LSTM(input_size=hidden_size, 
                               hidden_size=hidden_size, 
                               batch_first=True)
        
        # Fully connected layer to map to original features
        self.fc = nn.Linear(hidden_size, features)

    def forward(self, x):
        """Forward pass through the autoencoder.

        Args:
            x (torch.Tensor): Input tensor with shape (batch_size, timesteps, features).

        Returns:
            torch.Tensor: Reconstructed output with shape (batch_size, timesteps, features).
        """
        # Encoder
        _, (h_n, _) = self.encoder(x)  # h_n: (1, batch_size, hidden_size)
        encoded = h_n[-1]  # (batch_size, hidden_size)
        
        # Decoder
        input_to_decoder = encoded.unsqueeze(1).repeat(1, self.timesteps, 1)  # (batch_size, timesteps, hidden_size)
        output, _ = self.decoder(input_to_decoder)  # (batch_size, timesteps, hidden_size)
        output = self.fc(output)  # (batch_size, timesteps, features)
        
        return output

    def prepare_data(self, data, step=1):
        """Prepare overlapping sequences for training.

        Args:
            data (np.ndarray): Input data with shape (samples, features).
            step (int): Step size for overlapping sequences.

        Returns:
            torch.Tensor: Prepared sequences with shape (num_samples, timesteps, features).
        """
        num_samples = (len(data) - self.timesteps) // step + 1
        sequences = np.array([data[i * step:i * step + self.timesteps] for i in range(num_samples)])
        return torch.tensor(sequences, dtype=torch.float32)

    def train_model(self, data, epochs=100, step=1, learning_rate=0.005, batch_size=32, validation_split=0.2):
        """Train the model with standardized data.

        Args:
            data (np.ndarray): Input data with shape (samples, features).
            epochs (int): Number of training epochs.
            step (int): Step size for overlapping sequences.
            learning_rate (float): Learning rate for the optimizer.
            batch_size (int): Batch size for training.
            validation_split (float): Fraction of data to use for validation.
        
        Returns:
            dict: Training history with loss metrics.
        """
        # Compute normalization parameters
        self.mean = np.mean(data, axis=0)
        self.std = np.std(data, axis=0)
        self.std[self.std == 0] = 1.0  # Prevent division by zero
        
        # Standardize the data
        data_std = (data - self.mean) / self.std
        
        # Prepare sequence data
        sequences = self.prepare_data(data_std, step=step)
        
        # Split into train and validation sets
        val_size = int(len(sequences) * validation_split)
        train_sequences = sequences[:-val_size] if val_size > 0 else sequences
        val_sequences = sequences[-val_size:] if val_size > 0 else None
        
        # Setup optimizer and loss function
        optimizer = optim.Adam(self.parameters(), lr=learning_rate)
        criterion = nn.MSELoss()
        
        # Training history
        history = {'train_loss': [], 'val_loss': []}
        
        # Training loop
        for epoch in range(epochs):
            self.train()
            total_loss = 0
            
            # Train on batches
            for i in range(0, len(train_sequences), batch_size):
                batch = train_sequences[i:i + batch_size]
                
                # Forward pass
                optimizer.zero_grad()
                output = self(batch)
                loss = criterion(output, batch)
                
                # Backward pass
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item() * len(batch)
            
            # Calculate average training loss
            avg_train_loss = total_loss / len(train_sequences)
            history['train_loss'].append(avg_train_loss)
            
            # Validation step
            if val_sequences is not None:
                self.eval()
                with torch.no_grad():
                    val_output = self(val_sequences)
                    val_loss = criterion(val_output, val_sequences).item()
                    history['val_loss'].append(val_loss)
                
                print(f"Epoch {epoch+1}/{epochs}, Loss: {avg_train_loss:.6f}, Val Loss: {val_loss:.6f}")
            else:
                print(f"Epoch {epoch+1}/{epochs}, Loss: {avg_train_loss:.6f}")
        
        return history

    def get_anomaly_score(self, state):
        """Calculate the anomaly score for a given state.

        Args:
            state (np.ndarray or torch.Tensor): Input state with shape (timesteps, features) 
                                           or (batch_size, timesteps, features).

        Returns:
            float: Reconstruction error as the anomaly score.
        """
        # Convert to tensor if numpy array
        if isinstance(state, np.ndarray):
            state = torch.tensor(state, dtype=torch.float32)
        
        # Ensure correct shape for model
        if len(state.shape) == 2:
            state = state.unsqueeze(0)  # Add batch dimension
        elif len(state.shape) != 3:
            raise ValueError(f"Expected 2D or 3D input, got {state.shape}")
        
        # Switch to evaluation mode
        self.eval()
        
        # Calculate reconstruction error
        with torch.no_grad():
            output = self(state)
            reconstruction_error = torch.mean((output - state) ** 2).item()
        
        return reconstruction_error

    def save(self, model_path='lstm_autoencoder.pth', mean_path='mean.npy', std_path='std.npy'):
        """Save the model and normalization parameters."""
        model_dir = os.path.dirname(model_path)
        if model_dir and not os.path.exists(model_dir):
            os.makedirs(model_dir)
            
        torch.save(self.state_dict(), model_path)
        np.save(mean_path, self.mean)
        np.save(std_path, self.std)
        print(f"Model saved to {model_path}")

    def load(self, model_path='lstm_autoencoder.pth', mean_path='mean.npy', std_path='std.npy'):
        """Load the model and normalization parameters."""
        self.load_state_dict(torch.load(model_path))
        self.mean = np.load(mean_path)
        self.std = np.load(std_path)
        self.eval()
        print(f"Model loaded from {model_path}")
        return self
