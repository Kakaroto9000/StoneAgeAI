import torch
import random
import numpy as np
from game import Game
from collections import deque

MAX_MEMORY = 100000
BATCH_SIZE = 1000
LR = 0.001

class Agent:
    def __init__(self):
        self.n_games = 0
        self.epsilon = 0 #randomness of the game
        self.gamma = 0 #discount rate
        self.memory = deque(maxlen=MAX_MEMORY) #popleft()
        self.model = None
        self.trainer = None
        # TODO: model, trainer 

    def get_state(self, game):
        game.get_state()


    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done)) #pop_left if full memory

    def train_long_memory(self):
        if len(self.memory) > BATCH_SIZE:
            mini_sample = random.sample(self.memory, BATCH_SIZE)
        else:
            mini_sample = self.memory

        states, actions, rewards, next_states, dones = zip(*mini_sample)
        self.trainer.train_step(states, actions, rewards, next_states, dones)

    def train_short_memory(self, state, action, reward, next_state, done):
        self.trainer.train_step(state, action, reward, next_state, done)

    def get_action(self, state, game):
        self.epsilon = 80 - self.n_games
        final_move = [0,0,0,0,0,0,0,0]
        if random.randint(0,200) < self.epsilon:
            final_move = game.get_random_valid_move()
        else:
            state0 = torch.tensor(state, dtype=torch.float)
            prediction = self.model.predict(state0)

def train():
    plot_scores = []
    plot_mean_scores = []
    total_score = 0
    record = 0
    agent = Agent()
    game = Game()
    while True:

        #get old state and old move
        state_old = agent.get_state(game)
        final_move = agent.get_action(state_old, game)

        #perform new and get a new state
        reward, done ,score = game.play_ster(final_move)
        state_new = agent.get_state(game)

        #train short memory
        agent.train_short_memory(state_old,final_move,reward,state_new, done)

        #remember
        agent.remember(state_old,final_move,reward,state_new, done)

        if done:
            #train the long memory and plot results
            game.reset()
            agent.n_games+=1
            agent.train_long_memory(state_old,final_move,reward,state_new, done)
            if score> record:
                record = score
                #agent.model.save()

            print('Game', game.get_final_data, 'score', score, 'record', record)

if __name__ == '__main__':
    train()