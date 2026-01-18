import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
import os

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

class Linear_QNet(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        self.fc1 = nn.Linear(input_size, 512)
        self.fc2 = nn.Linear(512, 512)
        self.fc3 = nn.Linear(512, 256)
        self.fc4 = nn.Linear(256, output_size)
        
        # Move to GPU AFTER creating layers
        self.to(device)

    def forward(self, x):
        # Ensure input is on same device as model
        x = x.to(next(self.parameters()).device)
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.relu(self.fc3(x))
        x = self.fc4(x)
        return x

    def save(self, file_name='model.pth'):
        model_folder_path = './model'
        if not os.path.exists(model_folder_path):
            os.makedirs(model_folder_path)
        
        file_name = os.path.join(model_folder_path, file_name)
        torch.save(self.state_dict(), file_name)

class QTrainer():
    def __init__(self, model, lr, gamma):
        self.lr = lr
        self.gamma = gamma
        self.model = model
        self.optimizer = optim.Adam(model.parameters(), lr = self.lr)
        self.criterion = nn.MSELoss()

    def train_step(self, state, action, reward, next_state, done):
        # Handle single experience vs batch
        if isinstance(done, bool):
            # Single experience - wrap in lists
            state = [state]
            next_state = [next_state]
            action = [action]
            reward = [reward]
            done = [done]
        
        # Convert to numpy arrays first, then to tensors
        state = torch.tensor(np.array(state), dtype=torch.float).to(device)
        next_state = torch.tensor(np.array(next_state), dtype=torch.float).to(device)
        action = torch.tensor(np.array(action), dtype=torch.long).to(device)
        reward = torch.tensor(np.array(reward), dtype=torch.float).to(device)
        done = torch.tensor(np.array(done), dtype=torch.bool).to(device)

        # Get current Q values
        pred = self.model(state)

        # Get next Q values - VECTORIZED (no Python loop!)
        with torch.no_grad():
            next_q = self.model(next_state)
            max_next_q = torch.max(next_q, dim=1).values

        # Calculate target Q values - VECTORIZED
        # ~done converts True->False, False->True (so we multiply by 0 when done)
        target = pred.clone()
        target_q = reward + self.gamma * max_next_q * (~done).float()
        
        # Update only the actions that were taken
        batch_indices = torch.arange(len(action), device=device)
        target[batch_indices, action] = target_q

        # Backpropagation
        self.optimizer.zero_grad()
        loss = self.criterion(pred, target)
        loss.backward()
        self.optimizer.step()