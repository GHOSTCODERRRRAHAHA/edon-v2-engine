import json, time, random, paho.mqtt.client as mqtt
BROKER = "localhost"
TOPIC  = "edon/env"
def gen():
    return {
        "ts": time.time(),
        "env": {
            "lux": random.randint(100, 600),
            "co2": random.randint(500, 1200),
            "dba": random.randint(35, 65),
            "temp_c": round(random.uniform(21.0, 24.0), 1)
        }
    }
if __name__ == "__main__":
    c = mqtt.Client()
    c.connect(BROKER, 1883, 30)
    c.loop_start()
    try:
        while True:
            payload = json.dumps(gen())
            c.publish(TOPIC, payload, qos=0, retain=False)
            print("pub:", payload)
            time.sleep(0.2)  # 5 Hz
    except KeyboardInterrupt:
        pass
    finally:
        c.loop_stop(); c.disconnect()
