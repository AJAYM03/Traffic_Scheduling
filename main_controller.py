# main_controller.py
import traci
import sys
import os
import config
from fog_layer import Task, FogNode
from qiga_scheduler import QIGA

# --- Setup Environment ---
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

# --- MAPPINGS (Fixed for cross.net.xml) ---
LANES_BY_PHASE = {
    0: ["N_in_0", "N_in_1", "S_in_0", "S_in_1"], 
    2: ["E_in_0", "E_in_1", "W_in_0", "W_in_1"]
}
# Only list the Green phases here
ALL_PHASES = [0, 2]
ALL_LANES = ["N_in_0", "N_in_1", "S_in_0", "S_in_1", "E_in_0", "E_in_1", "W_in_0", "W_in_1"]

def get_next_smart_phase(lane_data_map, current_phase):
    """Decides which phase to switch to based on queues."""
    if current_phase == 0:
        return 2
    else:
        return 0

def main():
    # Initialize Fog Nodes
    fog_nodes = [FogNode(i, cap) for i, cap in enumerate(config.FOG_CAPACITIES)]
    print(f"Initialized {len(fog_nodes)} Fog Nodes")

    # Start SUMO
    traci.start(config.SUMO_CMD)
    traci.trafficlight.setProgram(config.TLS_ID, "0") 
    
    # --- Simulation State Variables ---
    step = 0
    current_phase = 0    # We start at Phase 0 (NS Green)
    phase_timer = 0      # Tracks how long we've been Green
    
    reaction_delay = 0   # Delays due to Fog Computation
    yellow_timer = 0     # Tracks how long to stay in Yellow
    next_phase_buffer = -1 # Stores the upcoming green phase during yellow
    
    # DEADLOCK FIX: Flag to ensure we act after waking up
    just_woke_up = False 

    # Set initial phase to North/South Green
    traci.trafficlight.setPhase(config.TLS_ID, current_phase)

    while step < config.STEPS_TO_RUN:
        traci.simulationStep()
        step += 1
        
        # --- LOGIC 1: HANDLE COMPUTATION DELAY ---
        if reaction_delay > 0:
            reaction_delay -= 1
            
            # Allow the yellow light to finish even if we are frozen
            if yellow_timer > 0:
                yellow_timer -= 1
                if yellow_timer == 0:
                    # TIME UP! We must switch to Green even if frozen
                    current_phase = next_phase_buffer
                    traci.trafficlight.setPhase(config.TLS_ID, current_phase)
                    phase_timer = 0
                    next_phase_buffer = -1
            else:
                phase_timer += 1
            
            # DEADLOCK FIX: If delay just finished, mark as awake so we don't think again immediately
            if reaction_delay == 0:
                just_woke_up = True
            
            continue 

        # --- LOGIC 2: HANDLE YELLOW TRANSITION ---
        if yellow_timer > 0:
            yellow_timer -= 1
            if yellow_timer == 0:
                # Yellow is done! Force switch to the pending Green Phase
                current_phase = next_phase_buffer
                traci.trafficlight.setPhase(config.TLS_ID, current_phase)
                phase_timer = 0
                next_phase_buffer = -1
            continue # Skip the rest; we are transitioning

        # If we are here, the light is GREEN and stable.
        phase_timer += 1

        # --- STEP A: SENSING ---
        current_tasks = []
        lane_data_map = {} 
        
        for lane in ALL_LANES:
            q_len = traci.lane.getLastStepHaltingNumber(lane)
            w_time = traci.lane.getWaitingTime(lane)
            lane_data_map[lane] = {'q': q_len, 'w': w_time}
            
            if q_len > 0:
                current_tasks.append(Task(lane, q_len, w_time))

        # --- STEP B: FOG SCHEDULING ---
        if current_tasks:
            # DEADLOCK FIX: If we just woke up from a delay, SKIP scheduling.
            # We must force a decision now based on the queue that built up.
            if just_woke_up:
                just_woke_up = False # Reset flag and fall through to Step C
            else:
                scheduler = QIGA(current_tasks, fog_nodes)
                _, processing_latency = scheduler.run()
                
                calculated_delay = int(processing_latency * config.LATENCY_TO_STEPS_FACTOR)
                
                # TIME MACHINE FIX: Start delay now and skip decision
                if calculated_delay > 0:
                    reaction_delay = calculated_delay
                    continue

        # --- STEP C: DECISION MAKING ---
        # 1. Get queues for current Green side
        active_lanes = LANES_BY_PHASE[current_phase]
        active_queue = sum([lane_data_map[l]['q'] for l in active_lanes])
        
        # 2. Get queues for the Red side
        other_phase = 2 if current_phase == 0 else 0
        other_lanes = LANES_BY_PHASE[other_phase]
        other_queue = sum([lane_data_map[l]['q'] for l in other_lanes])

        switch_needed = False
        
        # Only consider switching if we met Minimum Green Time
        if phase_timer >= config.MIN_GREEN:
            # Rule 1: Max Green Reached
            if phase_timer >= config.MAX_GREEN:
                switch_needed = True
            # Rule 2: Gap Out (Current lane is empty)
            elif active_queue <= config.QUEUE_THRESHOLD:
                switch_needed = True
            # Rule 3: Pressure (Other side has much more traffic)
            elif other_queue > (active_queue + 2): 
                switch_needed = True

        # --- STEP D: ACTUATION (Start Yellow) ---
        if switch_needed:
            # 1. Decide where to go (Toggle)
            next_green = get_next_smart_phase(lane_data_map, current_phase)
            
            # 2. Trigger Yellow Phase
            yellow_phase_index = current_phase + 1 
            
            traci.trafficlight.setPhase(config.TLS_ID, yellow_phase_index)
            traci.trafficlight.setPhaseDuration(config.TLS_ID, config.YELLOW_TIME)
            
            # 3. Set State Variables
            yellow_timer = config.YELLOW_TIME
            next_phase_buffer = next_green
            # (We do NOT update current_phase yet. We wait for yellow to finish.)

    traci.close()
    print("QIGA Simulation Complete.")

if __name__ == "__main__":
    main()