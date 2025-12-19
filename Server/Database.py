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
        Stores the X, Y position for a specific Tag MAC
        Measurement name is 'TagPosition'
        """
        try:
            point = (
                Point("TagPosition")
                .tag("mac", mac_address) 
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
        Retrieves the location history for a specific MAC
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