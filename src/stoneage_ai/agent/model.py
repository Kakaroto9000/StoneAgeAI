import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
import copy
from stoneage_ai.paths import MODELS_DIR

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

class Linear_QNet(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super().__init__()
        self.fc1 = nn.Linear(input_size, 256)
        self.fc2 = nn.Linear(256, 512)
        self.fc3 = nn.Linear(512, 128)
        self.fc4 = nn.Linear(128, output_size)

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
        """Save weights to ``models/<file_name>``; subfolders are created as needed."""
        path = MODELS_DIR / file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.state_dict(), path)
        return path

class QTrainer():
    """
    DQN updates with a target network, Double DQN and legal-move masking.

    Each transition is an n-step one:
        (state, action, reward, next_state, done, next_mask, discount)
    where ``reward`` is already the discounted sum of up to n rewards,
    ``discount`` is gamma**k for the k steps it covers, and ``next_mask`` is the
    packed (np.packbits) legal-action mask of ``next_state``.

        target = reward + discount * Q_target(s', argmax_{legal a'} Q(s', a'))
    """

    def __init__(self, model, lr, gamma):
        self.lr = lr
        self.gamma = gamma
        self.model = model
        self.num_actions = model.fc4.out_features
        self.target_model = copy.deepcopy(model)
        self.target_model.eval()
        self.optimizer = optim.Adam(model.parameters(), lr=self.lr)
        self.criterion = nn.SmoothL1Loss()  # Huber: robust to occasional large targets

    def sync_target(self):
        """Copy the online network into the target network."""
        self.target_model.load_state_dict(self.model.state_dict())

    def train_step(self, state, action, reward, next_state, done, next_mask, discount):
        if isinstance(done, (bool, np.bool_)):  # single transition -> batch of 1
            state, action, reward = [state], [action], [reward]
            next_state, done, next_mask, discount = [next_state], [done], [next_mask], [discount]

        state = torch.tensor(np.array(state), dtype=torch.float, device=device)
        next_state = torch.tensor(np.array(next_state), dtype=torch.float, device=device)
        action = torch.tensor(np.array(action), dtype=torch.long, device=device)
        reward = torch.tensor(np.array(reward), dtype=torch.float, device=device)
        done = torch.tensor(np.array(done), dtype=torch.bool, device=device)
        discount = torch.tensor(np.array(discount), dtype=torch.float, device=device)
        legal = np.unpackbits(np.array(next_mask), axis=-1, count=self.num_actions).astype(bool)
        legal = torch.tensor(legal, device=device)

        batch = torch.arange(len(action), device=device)
        q_taken = self.model(state)[batch, action]

        with torch.no_grad():
            # Double DQN: online net picks the best LEGAL next move, target net scores it.
            online_next = self.model(next_state).masked_fill(~legal, float("-inf"))
            best_next = online_next.argmax(dim=1)
            next_value = self.target_model(next_state)[batch, best_next]
            no_future = done | ~legal.any(dim=1)
            next_value = torch.where(no_future, torch.zeros_like(next_value), next_value)
            target = reward + discount * next_value

        loss = self.criterion(q_taken, target)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return loss.item()
