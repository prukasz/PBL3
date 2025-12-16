import time
from datetime import datetime
import influxdb_client
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

class InfluxHandler:
    def __init__(self, url, token, org, bucket):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        
        # Initialize Client
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()

    def write_position(self, mac_address: str, x: float, y: float):
        """
        Stores the X, Y position for a specific Tag MAC.
        Measurement name is 'TagPosition'.
        """
        try:
            point = (
                Point("TagPosition")
                .tag("mac", mac_address)  # Indexed for fast searching
                .field("x", float(x))
                .field("y", float(y))
                .time(datetime.utcnow(), WritePrecision.MS)
            )
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            print(f"[Influx] Written: MAC={mac_address} X={x} Y={y}")
            return True
        except Exception as e:
            print(f"[Influx] Write Error: {e}")
            return False

    def get_history(self, mac_address: str, time_range: str = "-1h"):
        """
        Retrieves the location history for a specific MAC.
        time_range examples: "-10m", "-1h", "-24h", "-30d"
        """
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: {time_range})
            |> filter(fn: (r) => r["_measurement"] == "TagPosition")
            |> filter(fn: (r) => r["mac"] == "{mac_address}")
            |> filter(fn: (r) => r["_field"] == "x" or r["_field"] == "y")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> keep(columns: ["_time", "x", "y"])
            |> sort(columns: ["_time"], desc: true)
        '''
        
        try:
            tables = self.query_api.query(query, org=self.org)
            history = []
            
            for table in tables:
                for record in table.records:
                    history.append({
                        "time": record.get_time(),
                        "x": record.values.get("x"),
                        "y": record.values.get("y")
                    })
            
            return history
        except Exception as e:
            print(f"[Influx] Query Error: {e}")
            return []

    def close(self):
        self.client.close()

# --- Example Usage ---
if __name__ == "__main__":
    # Configuration
    TOKEN = "HnJNerjV3H5ay1g8oPvyWqc6A3L4Rucl5SBjHZ8rRWC-8nJVKqeEMYjKB1qJ40Jwst8xvj05AdTCG6qTi2jNEQ=="
    ORG = "PBL3"
    URL = "http://192.168.1.19:8086"
    BUCKET = "Position"

    db = InfluxHandler(URL, TOKEN, ORG, BUCKET)

    # 1. Write Data (Simulate a moving tag)
    my_mac = "AA:BB:CC:11:22:33"
    
    print("Writing dummy data...")
    db.write_position(my_mac, 10.5, 5.2)
    time.sleep(1)
    db.write_position(my_mac, 12.0, 6.8)
    time.sleep(1)
    db.write_position(my_mac, 14.2, 8.1)

    # 2. Read Data
    print(f"\nRetrieving history for {my_mac}...")
    history = db.get_history(my_mac, time_range="-5m")
    
    for record in history:
        print(f"Time: {record['time']} | Pos: ({record['x']}, {record['y']})")
    
    db.close()