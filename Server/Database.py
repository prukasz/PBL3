import time
from datetime import datetime
import influxdb_client
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from tag_mapping import get_name_by_mac

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

    def get_all_current_positions(self, time_range: str = "-5m"):
        """
        Retrieves the most recent position for all tags
        Returns list of dicts: [{"mac": "...", "x": ..., "y": ..., "time": ...}, ...]
        """
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: {time_range})
            |> filter(fn: (r) => r["_measurement"] == "TagPosition")
            |> filter(fn: (r) => r["_field"] == "x" or r["_field"] == "y")
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            |> group(columns: ["mac"])
            |> last(column: "_time")
            |> keep(columns: ["_time", "mac", "x", "y"])
        '''
        
        try:
            tables = self.query_api.query(query, org=self.org)
            positions = []
            
            for table in tables:
                for record in table.records:
                    mac = record.values.get("mac")
                    positions.append({
                        "mac": mac,
                        "name": get_name_by_mac(mac),
                        "x": record.values.get("x"),
                        "y": record.values.get("y"),
                        "time": record.get_time()
                    })
            
            return positions
        except Exception as e:
            print(f"[Influx] Query Error: {e}")
            return []

    def get_all_tags(self, time_range: str = "-24h"):
        """
        Retrieves list of all unique MAC addresses seen in the given time range
        """
        query = f'''
        from(bucket: "{self.bucket}")
            |> range(start: {time_range})
            |> filter(fn: (r) => r["_measurement"] == "TagPosition")
            |> keep(columns: ["mac"])
            |> distinct(column: "mac")
        '''
        
        try:
            tables = self.query_api.query(query, org=self.org)
            tags = []
            
            for table in tables:
                for record in table.records:
                    mac = record.values.get("mac")
                    if mac and mac not in tags:
                        tags.append(mac)
            
            return tags
        except Exception as e:
            print(f"[Influx] Query Error: {e}")
            return []

    def close(self):
        self.client.close()
        
    def clear_database(self):
        """
        Deletes ALL data in the bucket for the measurement 'TagPosition'.
        Caution: This action is irreversible.
        """
        try:
            # Initialize Delete API
            delete_api = self.client.delete_api()

            # Define the start and stop time for deletion
            # To clear everything, we use a very old start date and the current time
            start = "1970-01-01T00:00:00Z"
            stop = datetime.utcnow().isoformat() + "Z"
            
            # Predicate: filters what to delete. 
            # '_measurement="TagPosition"' deletes only your tracking data.
            # If you want to delete EVERYTHING in the bucket, remove the predicate arg entirely (use predicate="").
            predicate = '_measurement="TagPosition"'

            delete_api.delete(
                start=start,
                stop=stop,
                predicate=predicate,
                bucket=self.bucket,
                org=self.org
            )
            print("[Influx] Database cleared successfully.")
            return True
        except Exception as e:
            print(f"[Influx] Delete Error: {e}")
            return False