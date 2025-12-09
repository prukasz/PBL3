import os
from datetime import datetime

class FileHandler:
    def __init__(self, whitelist_file="whitelist.txt", output_file="scan_results.txt"):
        self.whitelist_file = whitelist_file
        self.output_file = output_file

    def load_whitelist(self):
        if not os.path.exists(self.whitelist_file):
            print(f"[FileManager] Warning: {self.whitelist_file} not found. Returning empty list.")
            return []
        
        with open(self.whitelist_file, "r") as f:
            macs = [line.strip() for line in f.readlines() if line.strip()]
        return macs

    def save_point_header(self, point_number, header):
        _header = f"{header} {point_number}\n"
        self._append_to_file(_header)

    def save_scan_data(self, beacons):
        if not beacons:
            line = "None\n"
        else:
            # List comprehension to format: MAC:RSSI
            formatted_data = [f"{b['mac']}:{b['rssi']}" for b in beacons]
            line = ", ".join(formatted_data) + "\n"
        
        self._append_to_file(line)

    def _append_to_file(self, text):
        try:
            with open(self.output_file, "a") as f:
                f.write(text)
                f.flush()
        except Exception as e:
            print(f"[FileManager] Error saving to file: {e}")