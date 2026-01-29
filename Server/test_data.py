"""
Test Data Generator for BLE Tag Tracking System
Generates random positions for testing the web interface
"""
import asyncio
import random
import time
from datetime import datetime, timedelta
from Database import InfluxHandler

# Configuration - same as in run.py
DB_URL = "10.60.150.176:8086"
DB_TOKEN = "HnJNerjV3H5ay1g8oPvyWqc6A3L4Rucl5SBjHZ8rRWC-8nJVKqeEMYjKB1qJ40Jwst8xvj05AdTCG6qTi2jNEQ=="
DB_ORG = "PBL3"
DB_BUCKET = "Position"

# Test MAC addresses
TEST_MACS = [
    "AABBCCDDEE01",
    "AABBCCDDEE02",
    "AABBCCDDEE03",
    "AABBCCDDEE04",
    "AABBCCDDEE05",
    "DCA632F1D88D"
]

# Map boundaries (based on floor plan coordinates)
MAP_BOUNDS = {
    "x_min": -280,
    "x_max": 590,
    "y_min": 0,
    "y_max": 4500
}

PRESET_MOVE= [[-140, x] for x in range(0, 4500, 100)] 
PRESET_MOVE += [[-70, x] for x in range(4500, 2000, -150)]
PRESET_MOVE += [[250, x] for x in range(2000, 1200, -100)]


def generate_random_position():
    """Generate a random position within map bounds"""
    x = random.uniform(MAP_BOUNDS["x_min"], MAP_BOUNDS["x_max"])
    y = random.uniform(MAP_BOUNDS["y_min"], MAP_BOUNDS["y_max"])
    return round(x, 2), round(y, 2)


def add_single_position(db: InfluxHandler, mac: str = None, x: float = None, y: float = None):
    """Add a single position to the database"""
    if mac is None:
        mac = random.choice(TEST_MACS)
    
    if x is None or y is None:
        x, y = generate_random_position()
    
    success = db.write_position(mac, x, y)
    if success:
        print(f"Added position: MAC={mac}, X={x}, Y={y}")
    else:
        print(f"Failed to add position for {mac}")
    return success


def add_multiple_positions(db: InfluxHandler, count: int = 10):
    """Add multiple random positions"""
    print(f"\nAdding {count} random positions...")
    for i in range(count):
        mac = random.choice(TEST_MACS)
        add_single_position(db, mac)
        time.sleep(0.1)  # Small delay between writes
    print(f"Added {count} positions\n")


def add_positions_for_all_tags(db: InfluxHandler):
    """Add one position for each test tag"""
    print("\n Adding positions for all test tags...")
    for mac in TEST_MACS:
        add_single_position(db, mac)
    print(f"Added positions for {len(TEST_MACS)} tags\n")


def simulate_movement(db: InfluxHandler, mac: str = None, points: int = 20, delay: float = 1.0):
    """Simulate tag movement with gradual position changes"""
    if mac is None:
        mac = TEST_MACS[0]
    
    print(f"\nSimulating movement for {mac} ({points} points, {delay}s delay)...")
    
    # Start position
    x, y = generate_random_position()
    
    for i in range(points):
        # Add some random movement (scaled for larger coordinate system)
        x += random.uniform(-300, 300)
        y += random.uniform(-300, 300)
        
        # Keep within bounds
        x = max(MAP_BOUNDS["x_min"], min(MAP_BOUNDS["x_max"], x))
        y = max(MAP_BOUNDS["y_min"], min(MAP_BOUNDS["y_max"], y))
        
        add_single_position(db, mac, round(x, 2), round(y, 2))
        time.sleep(delay)
    
    print(f"Movement simulation complete\n")


def simulate_preset_movement(db: InfluxHandler, mac: str = None, delay: float = 1.0):
    """Simulate tag movement using preset path (PRESET_MOVE)"""
    if mac is None:
        mac = TEST_MACS[0]
    
    print(f"\nSimulating preset movement for {mac} ({len(PRESET_MOVE)} points, {delay}s delay)...")
    
    for i, (x, y) in enumerate(PRESET_MOVE):
        add_single_position(db, mac, x, y)
        print(f"  Point {i+1}/{len(PRESET_MOVE)}: X={x}, Y={y}")
        time.sleep(delay)
    
    print(f"Preset movement simulation complete\n")


def interactive_mode(db: InfluxHandler):
    """Interactive menu for adding test data"""
    while True:
        print("\n" + "="*50)
        print("="*50)
        print("1. Add single random position")
        print("2. Add position for specific MAC")
        print("3. Add positions for all test tags")
        print("4. Add multiple random positions")
        print("5. Simulate tag movement (random)")
        print("6. Simulate preset movement (PRESET_MOVE)")
        print("7. Add custom position (MAC, X, Y)")
        print("8. Show test MAC addresses")
        print("0. Exit")
        print("-"*50)
        
        choice = input("Choose option: ").strip()
        
        if choice == "1":
            add_single_position(db)
            
        elif choice == "2":
            print("\nAvailable MACs:")
            for i, mac in enumerate(TEST_MACS):
                print(f"  {i+1}. {mac}")
            try:
                idx = int(input("Select MAC (number): ")) - 1
                if 0 <= idx < len(TEST_MACS):
                    add_single_position(db, TEST_MACS[idx])
                else:
                    print("Invalid selection")
            except ValueError:
                print("Invalid input")
                
        elif choice == "3":
            add_positions_for_all_tags(db)
            
        elif choice == "4":
            try:
                count = int(input("How many positions? [10]: ") or "10")
                add_multiple_positions(db, count)
            except ValueError:
                print("Invalid number")
                
        elif choice == "5":
            print("\nAvailable MACs:")
            for i, mac in enumerate(TEST_MACS):
                print(f"  {i+1}. {mac}")
            try:
                idx = int(input("Select MAC (number) [1]: ") or "1") - 1
                points = int(input("Number of points [20]: ") or "20")
                delay = float(input("Delay between points (seconds) [1.0]: ") or "1.0")
                if 0 <= idx < len(TEST_MACS):
                    simulate_movement(db, TEST_MACS[idx], points, delay)
                else:
                    print("Invalid selection")
            except ValueError:
                print("Invalid input")
                
        elif choice == "6":
            print("\nAvailable MACs:")
            for i, mac in enumerate(TEST_MACS):
                print(f"  {i+1}. {mac}")
            try:
                idx = int(input("Select MAC (number) [1]: ") or "1") - 1
                delay = float(input("Delay between points (seconds) [1.0]: ") or "1.0")
                if 0 <= idx < len(TEST_MACS):
                    simulate_preset_movement(db, TEST_MACS[idx], delay)
                else:
                    print("❌ Invalid selection")
            except ValueError:
                print("❌ Invalid input")
                
        elif choice == "7":
            try:
                mac = input("MAC address: ").strip().upper().replace(":", "")
                x = float(input("X coordinate: "))
                y = float(input("Y coordinate: "))
                add_single_position(db, mac, x, y)
            except ValueError:
                print("❌ Invalid input")
                
        elif choice == "8":
            print("\nTest MAC addresses:")
            for mac in TEST_MACS:
                formatted = ':'.join(mac[i:i+2] for i in range(0, len(mac), 2))
                print(f"  • {mac} ({formatted})")
                
        elif choice == "0":
            break
        else:
            print("Invalid option")


def main():
    print("Connecting to InfluxDB...")
    db = InfluxHandler(DB_URL, DB_TOKEN, DB_ORG, DB_BUCKET)
    
    try:
        interactive_mode(db)
    finally:
        db.close()
        print("Database connection closed")


if __name__ == "__main__":
    main()
