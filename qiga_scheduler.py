# qiga_scheduler.py
import numpy as np
import random
import math
import config

class QIGA:
    def __init__(self, tasks, fog_nodes):
        self.tasks = tasks
        self.fog_nodes = fog_nodes
        self.num_tasks = len(tasks)
        self.num_nodes = len(fog_nodes)
        
        # Calculate bits needed to represent nodes
        self.bits_per_task = math.ceil(math.log2(self.num_nodes)) if self.num_nodes > 1 else 1
        self.genome_length = self.num_tasks * self.bits_per_task
        
        # Initialize Q-bits with 50% probability (Superposition)
        self.q_population = np.full((config.POPULATION_SIZE, self.genome_length, 2), 1/math.sqrt(2))
        self.best_solution = None
        self.best_fitness = float('inf')

    def observe(self):
        """Collapse Q-bits into binary (0s and 1s)"""
        binary_population = []
        for i in range(config.POPULATION_SIZE):
            chromosome = []
            for j in range(self.genome_length):
                alpha_sq = self.q_population[i][j][0] ** 2
                bit = 0 if random.random() < alpha_sq else 1
                chromosome.append(bit)
            binary_population.append(chromosome)
        return binary_population

    def decode_schedule(self, binary_chromosome):
        """Convert binary to Node IDs"""
        schedule = []
        chunks = [binary_chromosome[i:i + self.bits_per_task] for i in range(0, len(binary_chromosome), self.bits_per_task)]
        
        for bits in chunks:
            node_idx = int("".join(map(str, bits)), 2)
            node_idx = node_idx % self.num_nodes
            schedule.append(node_idx)
        return schedule

    def evaluate_fitness(self, schedule):
        """Calculate Makespan: When does the busiest node finish?"""
        node_finish_times = [0.0] * self.num_nodes
        
        for task_idx, node_idx in enumerate(schedule):
            task = self.tasks[task_idx]
            node = self.fog_nodes[node_idx]
            proc_time = node.compute_processing_time(task)
            node_finish_times[node_idx] += proc_time
            
        return max(node_finish_times)

    def update_qbits(self, binary_pop, fitness_scores):
        """Rotate Q-bits towards the best solution found"""
        min_fitness = min(fitness_scores)
        best_idx = fitness_scores.index(min_fitness)
        
        if min_fitness < self.best_fitness:
            self.best_fitness = min_fitness
            self.best_solution = binary_pop[best_idx]

        for i in range(config.POPULATION_SIZE):
            for j in range(self.genome_length):
                x_best = self.best_solution[j]
                x_current = binary_pop[i][j]
                
                theta = 0
                if x_current == 0 and x_best == 1:
                    theta = config.ALPHA
                elif x_current == 1 and x_best == 0:
                    theta = -config.ALPHA
                
                # Quantum Rotation Gate
                alpha = self.q_population[i][j][0]
                beta = self.q_population[i][j][1]
                
                new_alpha = alpha * math.cos(theta) - beta * math.sin(theta)
                new_beta = alpha * math.sin(theta) + beta * math.cos(theta)
                
                self.q_population[i][j][0] = new_alpha
                self.q_population[i][j][1] = new_beta

    def run(self):
        for _ in range(config.GENERATIONS):
            binary_pop = self.observe()
            fitness_scores = [self.evaluate_fitness(self.decode_schedule(c)) for c in binary_pop]
            self.update_qbits(binary_pop, fitness_scores)
            
        return self.decode_schedule(self.best_solution), self.best_fitness