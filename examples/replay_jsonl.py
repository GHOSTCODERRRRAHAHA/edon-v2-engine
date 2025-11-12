import sys, json, requests
URL = "http://localhost:8000/v1/ingest"
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python examples/replay_jsonl.py data\\sample.jsonl"); sys.exit(1)
    path = sys.argv[1]
    batch = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try: batch.append(json.loads(line))
            except: pass
    r = requests.post(URL, json={"frames": batch})
    print("status:", r.status_code, "resp:", r.text[:300])
