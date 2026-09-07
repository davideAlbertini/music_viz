import numpy as np
from collections import deque

class CircularBuffer(object):
    def __init__(self, size):
        self.buffer = deque(maxlen=size)

    def append(self, data):
        self.buffer.append(data)

    def get(self):
        return np.concatenate(self.buffer, axis=0)