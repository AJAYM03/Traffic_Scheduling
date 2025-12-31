# fog_layer.py
import time
import config

class Task:
    def __init__(self, lane_id, queue_length, waiting_time):
        self.id = lane_id
        # The logic: More cars = More data to process = Heavier Task
        self.length = config.BASE_TASK_SIZE + (queue_length * config.COMPLEXITY_FACTOR)
        self.priority = waiting_time
        self.arrival_time = time.time()

    def __repr__(self):
        return f"Task({self.id}, Load:{self.length:.1f})"


class FogNode:
    def __init__(self, node_id, capacity):
        self.id = node_id
        self.capacity = capacity  # Instructions per millisecond
        self.current_load = 0     

    def compute_processing_time(self, task):
        """
        Calculates how long this node takes to finish the task.
        Formula: Time = Task Size / Node Speed
        """
        return task.length / self.capacity

    def __repr__(self):
        return f"Node_{self.id}(Cap:{self.capacity})"