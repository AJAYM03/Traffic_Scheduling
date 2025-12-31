# config.py
import os

# --- SUMO Configuration ---
# Ensure you have 'cross.sumocfg' in the same folder
SUMO_CMD = ["sumo-gui", "-c", "cross.sumocfg", "--start"] 
STEPS_TO_RUN = 3600  # Run for 1 hour
TLS_ID = "C"         # The ID of your central traffic light in SUMO

# --- Traffic Light Constraints ---
MIN_GREEN = 10       # Minimum green time (seconds)
MAX_GREEN = 50       # Maximum green time (seconds)
YELLOW_TIME = 3      # Yellow interval
QUEUE_THRESHOLD = 4  # Gap-out threshold (if fewer cars than this, switch)

# --- Fog Layer Configuration ---
# 4 Fog Nodes with different processing speeds (Heterogeneous)
NUM_FOG_NODES = 4
# 1. Keep the "Trap" node slow, but make others fast enough
FOG_CAPACITIES = [20, 100, 150, 200]

# 2. Significant but Manageable Workload
# A task size of 2000-3000 is the "Sweet Spot".
# Fast Node (200) takes: 2000 / 200 = 10ms.
# Slow Node (20) takes: 2000 / 20 = 100ms.
BASE_TASK_SIZE = 2500
COMPLEXITY_FACTOR = 100

# --- QIGA Configuration ---
POPULATION_SIZE = 20
GENERATIONS = 10
ALPHA = 0.05
BETA = 0.01

# --- Simulation Reality Factors ---
# This converts "Computation Time" (ms) into "Traffic Delay" (Steps)
# 100ms computation = 5 steps of delay in the simulation
LATENCY_TO_STEPS_FACTOR = 0.2