import influxdb_client, os, time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

token = "HnJNerjV3H5ay1g8oPvyWqc6A3L4Rucl5SBjHZ8rRWC-8nJVKqeEMYjKB1qJ40Jwst8xvj05AdTCG6qTi2jNEQ=="
org = "PBL3"
url = "http://192.168.114.74:8086"

client = influxdb_client.InfluxDBClient(url=url, token=token, org=org)

bucket="Position"

write_api = client.write_api(write_options=SYNCHRONOUS)
   

point = (
    Point("AABBCCDDEE")
    .tag("Dupa", "val")
    .field("field1", 100)
)
write_api.write(bucket=bucket, org="PBL3", record=point)
time.sleep(1) # separate points by 1 second