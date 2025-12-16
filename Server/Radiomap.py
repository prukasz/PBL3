from abc import ABC, abstractmethod
import os
import math

# Configuration
NOISE_FLOOR_DBM = -100.0 

class RadioMap(ABC):
    """
    Abstract Base Class defining the contract for any Radio Map implementation.
    """
    @abstractmethod
    def load_data(self, filename: str):
        """Loads map data from a file."""
        pass

    @abstractmethod
    def get_position(self, data_string: str):
        """
        Calculates position based on provided data string (e.g., hex packet).
        Returns: tuple (x, y, label) or None
        """
        pass

class BLEPoint:
    def __init__(self, label, x, y, fingerprints):
        self.label = label
        self.x = x
        self.y = y
        # Dictionary format: { 'MAC': rssi_in_dBm }
        self.fingerprints = fingerprints 

    def __repr__(self):
        return f"['{self.label}' @ ({self.x}, {self.y})]"

class BLERadioMap(RadioMap):
    def __init__(self):
        self.points = []

    # --- Implementation of load_data ---
    def load_data(self, filename: str):
        self.points = []
        if not os.path.exists(filename):
            print(f"Error: The file '{filename}' was not found.")
            return

        with open(filename, 'r') as f:
            lines = f.readlines()

        current_label = None
        current_x = 0.0
        current_y = 0.0
        current_point_data = {} 

        for line in lines:
            line = line.strip()
            if not line: continue

            if ':' in line:
                self._process_scan_line(line, current_point_data)
            else:
                # It is a Header. Finalize previous point first.
                if current_label is not None:
                    self._finalize_point(current_label, current_x, current_y, current_point_data)
                
                parts = line.split(',')
                current_label = parts[0].strip()
                try:
                    current_x = float(parts[1].strip()) if len(parts) > 1 else 0.0
                    current_y = float(parts[2].strip()) if len(parts) > 2 else 0.0
                except ValueError:
                    current_x, current_y = 0.0, 0.0
                current_point_data = {}

        if current_label is not None:
            self._finalize_point(current_label, current_x, current_y, current_point_data)
        
        print(f"Loaded {len(self.points)} Map Points\n")

    def _process_scan_line(self, line, data_store):
        items = line.split(',')
        for item in items:
            item = item.strip()
            if not item: continue
            try:
                mac_part, rssi_part = item.rsplit(':', 1)
                clean_mac = mac_part.replace(':', '')
                rssi_val = float(rssi_part)
                
                # STORE DBM DIRECTLY (No conversion to mW)
                data_store.setdefault(clean_mac, []).append(rssi_val)
            except ValueError:
                continue

    def _finalize_point(self, label, x, y, data_store):
        final_fingerprints_dbm = {}
        
        for mac, dbm_values in data_store.items():
            # AVERAGE DBM DIRECTLY
            avg_dbm = sum(dbm_values) / len(dbm_values)
            final_fingerprints_dbm[mac] = round(avg_dbm, 2)
        
        new_point = BLEPoint(label, x, y, final_fingerprints_dbm)
        self.points.append(new_point)

    # --- Implementation of get_position ---
    def get_position(self, data_string: str):
        # 1. Parse Hex
        live_scan_list = self._parse_packet_hex(data_string)
        if not live_scan_list:
            return None

        # 2. Convert to dict
        live_fp_dbm = {mac: rssi for mac, rssi in live_scan_list}
        
        #   
        scored_points = []
        for point in self.points:
            rmse = self._calculate_rmse(live_fp_dbm, point.fingerprints)
            scored_points.append((point, rmse))

        # 4. Sort and take Top 3
        scored_points.sort(key=lambda x: x[1])
        top_3 = scored_points[:3]

        # 5. Weighted Average
        total_weight = 0.0
        weighted_x = 0.0
        weighted_y = 0.0
        
        # Determine closest label
        closest_label = top_3[0][0].label if top_3 else "Unknown"

        for pt, error in top_3:
            # Weight is inverse square of the dBm error
            weight = 1.0 / (error**2) if error > 0.001 else 1000.0
            weighted_x += pt.x * weight
            weighted_y += pt.y * weight
            total_weight += weight

        if total_weight == 0: return None

        return (weighted_x / total_weight, weighted_y / total_weight, closest_label)

    # --- Private Helpers ---
    def _parse_packet_hex(self, hex_string):
        """Parses packet string into list of (MAC, RSSI_dBm)"""
        hex_string = hex_string.replace(" ", "").upper()
        parsed_scan = []
        block_size = 14
        
        for i in range(0, len(hex_string), block_size):
            block = hex_string[i:i+block_size]
            if len(block) < 14: break
            
            mac_hex = block[:12]
            # Parse RSSI (hex to signed int)
            rssi_val = int(block[12:], 16)
            if rssi_val > 127: rssi_val -= 256 
            
            parsed_scan.append((mac_hex, rssi_val))
            
        return parsed_scan

    def _calculate_rmse(self, live_fp, map_fp):   
        # Check how many beacons were actually found in this live scan
        num_live = len(live_fp)

        # 1. Determine which MACs to compare
        if 0 < num_live <= 2:
            # SPARSE MODE: Only check the MACs we actually saw.
            # We ignore any extra MACs in the map point so they don't add error.
            comparison_macs = set(live_fp.keys())
        else:
            # STANDARD MODE: Check everything (Union of sets).
            # This penalizes the score if the map has beacons the live scan missed.
            comparison_macs = set(live_fp.keys()) | set(map_fp.keys())

        if not comparison_macs:
            return float('inf')

        sum_squared_error = 0.0
        
        for mac in comparison_macs:
            val_live = live_fp.get(mac, NOISE_FLOOR_DBM)
            val_map = map_fp.get(mac, NOISE_FLOOR_DBM)
            
            # Difference in dBm
            diff = val_live - val_map
            sum_squared_error += (diff ** 2)
            
        mse = sum_squared_error / len(comparison_macs)
        return math.sqrt(mse)