from sys import exit
#import boto3
import json
import re
import utils
#from botocore.exceptions import ClientError
import agents
import inspect
import numpy as np
import random
import requests

def add_child(n):
    n.add_child()
    


class node:
    def __init__(self, name, other_name, statement, level,
                 roles, initial_conversation, parent=None):
        self.name = name
        self.other_name = other_name
        self.statement = statement
        self.children = []
        self.parent = parent
        self.mu = 0
        self.level = level
        self.sigma = 0
        self.roles = roles
        self.embedding = None
        self.initial_conversation = initial_conversation
        transcript = "\n".join(initial_conversation) + self.read()
        self.evaluation = utils.extract_json(agents.evaluator(transcript))

    def get_embedding(self):
        
        if not self.embedding:
            self.embedding = agents.embedding("\n".join(self.initial_conversation) + "\n" + self.read())
        return self.embedding
        
    def add_child(self, rag=None, statement=None):
        if statement:
            self.children.append(node(self.other_name, self.name, turn, self.level+1, self.roles, self.initial_conversation, self))
        else:
            transcript = "\n".join(self.initial_conversation) + self.read()
            f = self.roles[self.other_name]
            if len(inspect.getfullargspec(f).args) == 2:
                self.response = f(transcript, rag)
            else:
                self.response = f(transcript)
            response = utils.remove_name(self.other_name, self.response)
            self.children.append(node(self.other_name, self.name, response, self.level+1, self.roles, self.initial_conversation, self))

    def score_lineage(self):

        if self.parent:
            chain = self.parent.score_lineage()
            chain[self.name].append(self.score[self.name])
            chain[self.other_name].append(self.score[self.other_name])
        else:
            chain = {self.name: [self.score[self.name]],
                     self.other_name: [self.score[self.other_name]]}

        return chain.copy()
    
    def print_tree(self):
        if len(self.children) > 0:
            for c in self.children:
                c.print_tree()
        print('-' * self.level + "\n".join(self.statement.split("\n")[:2]))
        
    def read(self):

        previous_chain = ""
        if self.parent:
            previous_chain = self.parent.read()

        return previous_chain + self.name + ': ' + self.statement + "\n"

    def stat(self):
        value = {'very high': .9, 'high': .7, 'medium': .5, 'low': .3, 'very low': .05}
        for child in self.children:
            child.score = 0
            for item in child.evaluation.keys():
                child.score += value[child.evaluation[item]]

        self.mu = np.mean([c.score for c in self.children])
        self.sigma = np.std([c.score for c in self.children])
        return self.mu, self.sigma


    def flatten(self):

        flat = [self]
        for c in self.children:
            flat += c.flatten()
        return flat


def create_batches(gpr, rollout_embeddings, n_batches):
    batch_mu = []
    batch_sigma = []
    batches = []
    batch_idx = []
    n_to_choose_from = len(rollout_embeddings)
    for z in range(n_batches):
        batch = [random.randint(0, n_to_choose_from-1) for x in range(4)]
        batch_idx.append(batch)
        m, s = gpr.predict([rollout_embeddings[i] for i in batch], return_cov=True)
        batch_mu.append(','.join([str(x) for x in m]))
        sigma = []
        for x in s:
            sigma.append(','.join([str(y) for y in x]))
        batch_sigma.append(';'.join(sigma))
    return batch_idx, batch_mu, batch_sigma

def get_best_batch(batch_mu, batch_sigma):
    url = 'https://boaz.onrender.com/qei?y_best=.02&n=4'
    data = {'k': ';'.join(batch_mu),
            'sigma': '|'.join(batch_sigma)}
    response = requests.post(url, json.dumps(data))
    boaz = eval(response.content.decode('utf-8'))
    
    fboaz = [float(x) for x in boaz['scores'].split(',')]
    best = -1
    for i, mx in enumerate(fboaz):
        if mx > best:
            best = float(mx)
            best_idx = i
    return best_idx