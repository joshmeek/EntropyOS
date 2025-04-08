# run_ubi_simulation.py

import requests
import time
import json
import sys

# --- Configuration ---
BASE_URL = "http://localhost:8000" # Adjust if your backend runs elsewhere
SIMULATION_NAME = "UBI Policy Test"
POPULATION_SIZE = 10
NUM_TICKS_TO_RUN = 5 # Number of ticks to simulate after setup
SEED_CHECK_INTERVAL = 5 # Seconds between checking if seeding is complete
MAX_SEED_WAIT_TIME = 180 # Maximum seconds to wait for seeding

# --- API Endpoints ---
SIMULATIONS_URL = f"{BASE_URL}/simulations/"
AGENTS_URL = f"{BASE_URL}/agents/"

# --- Helper Functions ---

def handle_response(response: requests.Response, description: str):
    """Checks response status and prints info."""
    try:
        response.raise_for_status()
        print(f"SUCCESS: {description} - Status {response.status_code}")
        try:
            return response.json()
        except json.JSONDecodeError:
            print("WARNING: Response was not JSON, but status code was OK.")
            return response.text
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: {description} failed - Status {response.status_code}")
        print(f"       Reason: {response.text}")
        raise e
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Network error during {description}: {e}")
        raise e

def create_simulation() -> str:
    """Creates a new simulation and returns its ID."""
    print(f"Creating simulation '{SIMULATION_NAME}'...")
    payload = {"name": SIMULATION_NAME, "description": f"Testing UBI effect on {POPULATION_SIZE} agents."}
    response = requests.post(SIMULATIONS_URL, json=payload)
    data = handle_response(response, "Create simulation")
    sim_id = data.get("id")
    if not sim_id:
        raise ValueError("Could not get simulation ID from response.")
    print(f"Simulation created with ID: {sim_id}")
    return sim_id

def seed_simulation(sim_id: str):
    """Triggers seeding for the simulation."""
    print(f"Requesting seeding for {POPULATION_SIZE} agents in simulation {sim_id}...")
    seed_url = f"{SIMULATIONS_URL}{sim_id}/seed"
    payload = {"config": {"population_size": POPULATION_SIZE}}
    response = requests.post(seed_url, json=payload)
    handle_response(response, f"Seed request for simulation {sim_id}")
    print("Seeding started in background. Waiting for completion...")

def wait_for_seeding(sim_id: str):
    """Waits until the target population size is reached."""
    start_time = time.time()
    while True:
        elapsed_time = time.time() - start_time
        if elapsed_time > MAX_SEED_WAIT_TIME:
            raise TimeoutError(f"Seeding did not complete within {MAX_SEED_WAIT_TIME} seconds.")

        print(f"Checking agent count for simulation {sim_id}...")
        try:
            params = {"simulation_id": sim_id, "limit": POPULATION_SIZE + 10} # Fetch slightly more just in case
            response = requests.get(AGENTS_URL, params=params)
            if response.status_code == 200:
                agents = response.json()
                current_pop = len(agents)
                print(f"Current agent count: {current_pop}/{POPULATION_SIZE}")
                if current_pop >= POPULATION_SIZE:
                    print("Seeding complete.")
                    return
            else:
                 print(f"Agent count check failed (Status {response.status_code}), retrying...")

        except requests.exceptions.RequestException as e:
            print(f"Network error checking agent count: {e}, retrying...")

        time.sleep(SEED_CHECK_INTERVAL)


def inject_ubi_event(sim_id: str):
    """Injects a UBI event into the simulation."""
    print(f"Injecting UBI event into simulation {sim_id}...")
    event_url = f"{SIMULATIONS_URL}{sim_id}/events/"
    # Note: The structure depends on what event_service expects.
    # Assuming a simple type and name/description for now.
    payload = {
        "event_type": "ubi_distribution", # Needs to match backend event handler (Schema: EventCreate)
        "name": "Initial UBI Distribution",
        "description": "A one-time UBI payment to all agents at the start.",
        "data": {"amount": 1000} # Example data, if backend uses it
    }
    response = requests.post(event_url, json=payload)
    handle_response(response, f"Inject UBI event for simulation {sim_id}")

def run_simulation_ticks(sim_id: str, num_ticks: int):
    """Advances the simulation by the specified number of ticks."""
    print(f"Running simulation {sim_id} for {num_ticks} ticks...")
    tick_url = f"{SIMULATIONS_URL}{sim_id}/tick"
    for i in range(num_ticks):
        current_tick = i + 1 # Assuming we start from tick 1 after setup
        print(f"--- Advancing to Tick {current_tick}/{num_ticks} ---")
        try:
            response = requests.post(tick_url)
            handle_response(response, f"Advance to tick {current_tick}")
            time.sleep(0.5) # Small delay between ticks if needed
        except Exception as e:
            print(f"ERROR: Failed during tick {current_tick}. Stopping simulation run. Error: {e}")
            break
    print(f"Finished running {num_ticks} ticks.")

def get_metrics(sim_id: str):
    """Fetches all metric snapshots for the simulation."""
    print(f"Fetching metrics for simulation {sim_id}...")
    metrics_url = f"{SIMULATIONS_URL}{sim_id}/metrics/"
    params = {"limit": NUM_TICKS_TO_RUN + 5} # Get all expected metrics + buffer
    try:
        response = requests.get(metrics_url, params=params)
        return handle_response(response, f"Get metrics for simulation {sim_id}")
    except Exception as e:
        print(f"Could not fetch metrics: {e}")
        return []

# --- Main Execution ---
if __name__ == "__main__":
    simulation_id = None
    try:
        # 1. Create Simulation
        simulation_id = create_simulation()

        # 2. Seed Simulation (and wait)
        seed_simulation(simulation_id)
        wait_for_seeding(simulation_id)

        # 3. Get Initial Metrics (after seeding, before UBI/ticks)
        initial_metrics = get_metrics(simulation_id)
        initial_gini = None
        if initial_metrics:
             # Find the most recent snapshot (highest tick, likely 0)
             latest_initial = max(initial_metrics, key=lambda x: x['tick'])
             initial_gini = latest_initial.get('metrics', {}).get('gini_coefficient', 'N/A')
             print(f"Initial Gini Coefficient (Tick {latest_initial['tick']}): {initial_gini}")
        else:
            print("Could not get initial metrics.")


        # 4. Inject UBI Event (before first tick runs)
        inject_ubi_event(simulation_id)

        # 5. Run Simulation Ticks
        run_simulation_ticks(simulation_id, NUM_TICKS_TO_RUN)

        # 6. Get Final Metrics
        final_metrics = get_metrics(simulation_id)
        final_gini = None
        last_tick_processed = -1
        if final_metrics:
            # Find the most recent snapshot
            latest_final = max(final_metrics, key=lambda x: x['tick'])
            last_tick_processed = latest_final['tick']
            final_gini = latest_final.get('metrics', {}).get('gini_coefficient', 'N/A')
            print(f"Final Gini Coefficient (Tick {last_tick_processed}): {final_gini}")
        else:
             print("Could not get final metrics.")

        # 7. Report Summary
        print("\n--- Simulation Report ---")
        print(f"Simulation ID: {simulation_id}")
        print(f"Population: {POPULATION_SIZE}")
        print(f"Ticks Run: {NUM_TICKS_TO_RUN} (Last recorded metric at tick {last_tick_processed})")
        print(f"UBI Event Injected: Yes")
        print(f"Initial Gini Coefficient: {initial_gini}")
        print(f"Final Gini Coefficient:   {final_gini}")

        if initial_gini != 'N/A' and final_gini != 'N/A':
             try:
                 change = float(final_gini) - float(initial_gini)
                 print(f"Change in Gini: {change:+.4f}")
                 if change < 0:
                     print("Observation: Income inequality (measured by Gini) decreased.")
                 elif change > 0:
                     print("Observation: Income inequality (measured by Gini) increased.")
                 else:
                     print("Observation: No significant change in income inequality.")
             except ValueError:
                 print("Could not calculate Gini change numerically.")
        print("--- End Report ---")


    except Exception as e:
        print(f"\nAn error occurred during the script execution: {e}")
        if simulation_id:
            print(f"Simulation {simulation_id} might be in an intermediate state.")
        sys.exit(1)

    print("\nScript finished.")
