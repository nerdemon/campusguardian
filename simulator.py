import requests
import time
import random
import json

# Your local FastAPI endpoint
API_URL = "http://127.0.0.1:8000/api/sensors"

# The rooms we want to monitor
ROOMS = [
    "Library - Floor 1",
    "Hostel Block A - Corridor",
    "Cafeteria"
]

print("🚀 Starting CampusGuardian Hardware Simulator...")
print("Press Ctrl+C to stop.\n")

tick_count = 0

while True:
    tick_count += 1
    for room in ROOMS:
        # 1. Generate base "normal" data
        if room == "Cafeteria":
            # Simulate dynamic Auto Lights Off sequence for the demo
            if tick_count <= 2:
                # First 10 seconds: People are still in the Cafeteria
                temp = round(random.uniform(22.0, 24.0), 1) 
                humidity = round(random.uniform(40.0, 60.0), 1)
                occupancy = random.randint(15, 30)
                light_level = round(random.uniform(85.0, 100.0), 1)
                motion = True
                if tick_count == 1:
                    print("🚶 [Demo] Cafeteria is currently occupied. Lights are ON.")
            else:
                # After 10 seconds: Room empties out, system autonomously cuts power
                temp = round(random.uniform(26.0, 28.0), 1) # AC turns off
                humidity = round(random.uniform(40.0, 60.0), 1)
                occupancy = 0
                light_level = 0.0
                motion = False
                if tick_count == 3:
                    print("🌙 [Demo] Cafeteria is now empty! AUTONOMOUS POWER SAVING TRIGGERED.")
        else:
            temp = round(random.uniform(20.0, 25.0), 1)
            humidity = round(random.uniform(40.0, 60.0), 1)
            occupancy = random.randint(5, 50)
            light_level = round(random.uniform(70.0, 100.0), 1)
            motion = True

        # 2. Randomly trigger Hackathon "Wow Factor" events
        event_roll = random.randint(1, 15) # 1 in 15 chance of an event per tick
        
        if event_roll == 1 and room == "Library - Floor 1":
            print(f"🔥 Triggering Overcrowding Event in {room}!")
            temp = round(random.uniform(31.0, 35.0), 1)
            occupancy = random.randint(150, 250)
            
        elif event_roll == 2 and room == "Hostel Block A - Corridor":
            print(f"💡 Triggering Energy Waste Event in {room}!")
            occupancy = 0
            light_level = 100.0
            motion = False

        # 3. Build the exact payload your FastAPI server expects
        payload = {
            "room_id": room,
            "temperature": temp,
            "humidity": humidity,
            "occupancy": occupancy,
            "light_level": light_level,
            "motion": motion
        }

        # 4. Fire the data to the backend
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                print(f"✅ Sent data for {room}: Temp {temp}°C, Occ {occupancy}")
            else:
                print(f"❌ Failed to send for {room}: {response.text}")
        except requests.exceptions.ConnectionError:
            print("⚠️ Connection Error: Is your FastAPI server running?")
        
    print("-" * 40)
    # Wait 5 seconds before the next sensor reading (matches your UI polling rate)
    time.sleep(5)