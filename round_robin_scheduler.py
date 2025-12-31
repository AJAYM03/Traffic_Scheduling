# round_robin_scheduler.py
import config

class RoundRobin:
    def __init__(self, tasks, fog_nodes):
        self.tasks = tasks
        self.fog_nodes = fog_nodes
        self.num_nodes = len(fog_nodes)

    def run(self):
        """
        Assigns tasks sequentially (Task 0->Node 0, Task 1->Node 1...).
        This is inefficient because it gives heavy tasks to slow nodes.
        """
        schedule = []
        node_finish_times = [0.0] * self.num_nodes
        
        for i, task in enumerate(self.tasks):
            node_idx = i % self.num_nodes
            schedule.append(node_idx)
            
            node = self.fog_nodes[node_idx]
            processing_time = node.compute_processing_time(task)
            node_finish_times[node_idx] += processing_time
            
        makespan = max(node_finish_times)
        return schedule, makespan