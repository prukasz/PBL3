import paho.mqtt.client as mqtt
import time
import random

MQTT_BROKER_IP = "10.60.150.176"
MQTT_PORT = 1883

TAG_IDS = [
    "AABBCCDDEE01",
    "AABBCCDDEE02",
    "AABBCCDDEE03",
    "AABBCCDDEE04",
    "AABBCCDDEE05",
]

# Beacons z zakresami RSSI
BEACONS = {
    "41DB26021D7A": (-67, -59),  # MAC bez : i zakres RSSI
    "CE5CA68A0D92": (-84, -79),
    "FE50487B2C1D": (-89, -82)
}

def mqtt_load_test(floor="floor", num_packets=1, duration_ms=1700):
    """
    Test obciążeniowy MQTT - wysyła num_packets pakietów w czasie duration_ms ms
    
    Args:
        floor: piętro (np. s3)
        num_packets: liczba pakietów do wysłania
        duration_ms: czas trwania testu w milisekundach
    """
    # Połączenie z brokerem MQTT
    client = mqtt.Client()
    client.connect(MQTT_BROKER_IP, MQTT_PORT, 60)
    
    # Oblicz interwał między pakietami
    interval = duration_ms / num_packets / 1000.0  # konwersja na sekundy
    
    print(f"Starting load test: {num_packets} packets over {duration_ms}ms")
    print(f"Interval between packets: {interval*1000:.2f}ms")
    
    start_time = time.time()
    
    for i in range(num_packets):
        # Losuj 3 beacony
        selected_beacons = random.sample(list(BEACONS.keys()), 3)
        
        # Generuj payload: 3x MAC (bez :) + RSSI (hex)
        payload = ""
        rssi_values = []
        
        for mac in selected_beacons:
            rssi_min, rssi_max = BEACONS[mac]
            rssi = random.randint(rssi_min, rssi_max)  # losowa wartość RSSI jako int
            rssi_values.append(rssi)
            

            rssi_hex = format(rssi & 0xFF, '02x')
            payload += mac + rssi_hex
        
        # Wybierz losowy MAC jako główny (do topicu)
        main_mac = random.choice(TAG_IDS)
    

        # Topic: floor/MAC i payload jako message body
        topic = f"{floor}/{main_mac}"
        
        # Publikuj z payloadem jako message body
        client.publish(topic, payload)
        

    end_time = time.time()
    actual_duration = (end_time - start_time) * 1000
    
    print(f"\nLoad test completed!")
    print(f"Packets sent: {num_packets}")
    print(f"Target duration: {duration_ms}ms")
    print(f"Actual duration: {actual_duration:.2f}ms")
    print(f"Average rate: {num_packets/(actual_duration/1000):.2f} packets/sec")
    
    client.disconnect()

if __name__ == "__main__":
    # Uruchom test obciążeniowy
    mqtt_load_test(floor="floor", num_packets=100, duration_ms=1000)


