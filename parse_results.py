import xml.etree.ElementTree as ET

def parse_tripinfo(file_path):
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        total_waiting_time = 0
        total_time_loss = 0
        vehicle_count = 0
        
        for trip in root.findall('tripinfo'):
            total_waiting_time += float(trip.get('waitingTime'))
            total_time_loss += float(trip.get('timeLoss'))
            vehicle_count += 1
            
        if vehicle_count == 0:
            print(f"[{file_path}] No vehicles finished.")
            return

        avg_wait = total_waiting_time / vehicle_count
        avg_loss = total_time_loss / vehicle_count
        
        print("-" * 30)
        print(f"RESULTS FOR: {file_path}")
        print("-" * 30)
        print(f"Total Vehicles: {vehicle_count}")
        print(f"Average Waiting Time: {avg_wait:.2f} seconds")
        print(f"Average Time Loss:    {avg_loss:.2f} seconds")
        print("-" * 30)
        
    except FileNotFoundError:
        print(f"Error: Could not find {file_path}")

if __name__ == "__main__":
    parse_tripinfo("tripinfo_BASELINE.xml")
    parse_tripinfo("tripinfo.xml")