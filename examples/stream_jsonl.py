import argparse, json, time, requests
def stream_file(file, hz):
    url = "http://localhost:8000/v1/ingest"
    with open(file, "r", encoding="utf-8") as f:
        lines = [json.loads(x) for x in f if x.strip()]
    delay = 1.0 / hz
    print(f"Streaming {len(lines)} frames to {url} at {hz} Hz")
    for fr in lines:
        r = requests.post(url, json={"frames": [fr]})
        print(f"{fr['ts']:.2f} -> {r.status_code} {r.text[:80]}")
        time.sleep(delay)
if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True)
    p.add_argument("--hz", type=float, default=5)
    args = p.parse_args()
    stream_file(args.file, args.hz)
