# baseline_controller.py
import traci
import sys
import os
import config
from fog_layer import Task, FogNode
from round_robin_scheduler import RoundRobin # Import the Dumb Scheduler

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Please declare environment variable 'SUMO_HOME'")

# --- MAPPINGS (Matched to cross.net.xml) ---
LANES_BY_PHASE = {
    0: ["N_in_0", "N_in_1", "S_in_0", "S_in_1"], 
    2: ["E_in_0", "E_in_1", "W_in_0", "W_in_1"]
}
ALL_PHASES = [0, 2]
ALL_LANES = ["N_in_0", "N_in_1", "S_in_0", "S_in_1", "E_in_0", "E_in_1", "W_in_0", "W_in_1"]

def get_next_smart_phase(lane_data_map, current_phase):
    # Simple toggle for 2 phases
    if current_phase == 0:
        return 2
    else:
        return 0

def main():
    fog_nodes = [FogNode(i, cap) for i, cap in enumerate(config.FOG_CAPACITIES)]
    print(f"Initialized {len(fog_nodes)} Fog Nodes (Baseline Mode)")

    # IMPORTANT: Save to a different file so we don't overwrite QIGA results
    sumo_cmd = list(config.SUMO_CMD)
    sumo_cmd.extend(["--tripinfo-output", "tripinfo_BASELINE.xml"])
    
    traci.start(sumo_cmd)
    traci.trafficlight.setProgram(config.TLS_ID, "0") 
    
    # --- State Variables ---
    step = 0
    current_phase = 0
    phase_timer = 0
    
    reaction_delay = 0 
    yellow_timer = 0      
    next_phase_buffer = -1 
    
    # DEADLOCK FIX: Flag to ensure we act after waking up
    just_woke_up = False

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
                
            # DEADLOCK FIX: If delay just finished, mark as awake
            if reaction_delay == 0:
                just_woke_up = True
            
            continue 

        # --- LOGIC 2: YELLOW TRANSITION ---
        if yellow_timer > 0:
            yellow_timer -= 1
            if yellow_timer == 0:
                # Yellow Finished -> Switch to Green
                current_phase = next_phase_buffer
                traci.trafficlight.setPhase(config.TLS_ID, current_phase)
                phase_timer = 0
                next_phase_buffer = -1
            continue 

        phase_timer += 1

        # --- SENSING ---
        current_tasks = []
        lane_data_map = {} 
        for lane in ALL_LANES:
            q_len = traci.lane.getLastStepHaltingNumber(lane)
            w_time = traci.lane.getWaitingTime(lane)
            lane_data_map[lane] = {'q': q_len, 'w': w_time}
            if q_len > 0:
                current_tasks.append(Task(lane, q_len, w_time))

        # --- ROUND ROBIN SCHEDULING (The "Dumb" Logic) ---
        # --- STEP B: FOG SCHEDULING ---
        if current_tasks:
            # DEADLOCK FIX: If we just woke up from a delay, SKIP scheduling.
            if just_woke_up:
                just_woke_up = False # Reset flag and fall through to Step C
            else:
                scheduler = RoundRobin(current_tasks, fog_nodes) 
                _, processing_latency = scheduler.run()
                
                # Apply processing delay
                calculated_delay = int(processing_latency * config.LATENCY_TO_STEPS_FACTOR)
                
                # TIME MACHINE FIX: Start delay now and skip decision
                if calculated_delay > 0:
                    reaction_delay = calculated_delay
                    continue

        # --- DECISION MAKING ---
        active_lanes = LANES_BY_PHASE[current_phase]
        active_queue = sum([lane_data_map[l]['q'] for l in active_lanes])
        
        other_phase = 2 if current_phase == 0 else 0
        other_lanes = LANES_BY_PHASE[other_phase]
        other_queue = sum([lane_data_map[l]['q'] for l in other_lanes])

        switch_needed = False
        if phase_timer >= config.MIN_GREEN:
            if phase_timer >= config.MAX_GREEN: switch_needed = True
            elif active_queue <= config.QUEUE_THRESHOLD: switch_needed = True
            elif other_queue > (active_queue + 2): switch_needed = True

        # --- ACTUATION ---
        if switch_needed:
            next_green_phase = get_next_smart_phase(lane_data_map, current_phase)
            
            # Trigger Yellow
            yellow_phase = current_phase + 1
            traci.trafficlight.setPhase(config.TLS_ID, yellow_phase)
            traci.trafficlight.setPhaseDuration(config.TLS_ID, config.YELLOW_TIME)
            
            # Set Wait State
            yellow_timer = config.YELLOW_TIME
            next_phase_buffer = next_green_phase
            # Do NOT update current_phase yet

    traci.close()
    print("Baseline (Round Robin) Simulation Complete.")

if __name__ == "__main__":
    main()