import argparse, time, requests, random, sys

parser = argparse.ArgumentParser()
parser.add_argument("--samples", type=int, default=500)
parser.add_argument("--url", type=str, default="http://127.0.0.1:8000/cav")
parser.add_argument("--winlen", type=int, default=240)
parser.add_argument("--sr", type=int, default=4)
parser.add_argument("--timeout", type=float, default=3.0)
args = parser.parse_args()

def _rand_list(n, lo, hi, roundto=3):
    return [round(random.uniform(lo, hi), roundto) for _ in range(n)]

def make_payload(winlen):
    temp_series = _rand_list(winlen, 33.0, 37.5, 2)
    temp_scalar = temp_series[-1]

    return {
        "EDA": _rand_list(winlen, 0.1, 3.5, 3),       # list len=winlen
        "TEMP": temp_series,                          # list len=winlen
        "temp_c": temp_scalar,                        # scalar
        "BVP": _rand_list(winlen, 0.0, 1.0, 3),       # list len=winlen
        "ACC_x": _rand_list(winlen, -1.5, 1.5, 3),    # list len=winlen
        "ACC_y": _rand_list(winlen, -1.5, 1.5, 3),    # list len=winlen
        "ACC_z": _rand_list(winlen, -1.5, 1.5, 3),    # list len=winlen

        # top-level environment scalars the API expects
        "humidity": round(random.uniform(30, 70), 1), # %
        "aqi": random.randint(0, 150),      # index

        # optional: keeps your old ENV block (ignored by validator)
        "ENV": {
            "TEMP": round(random.uniform(18, 30), 1),
            "HUMIDITY": round(random.uniform(30, 70), 1),
            "AQI": round(random.uniform(0, 150), 1)
        },

        "WINDOW": winlen,
        "SAMPLE_RATE_HZ": args.sr
    }


def post(payload):
    r = requests.post(args.url, json=payload, timeout=args.timeout)
    if r.status_code != 200:
        print(f"[HTTP {r.status_code}] {r.text[:800]}")
        return None, r.status_code
    return r.json(), 200

def run():
    latencies_ms = []
    failures = 0
    print(f"[EDON Benchmark] sending {args.samples} windowed samples (len={args.winlen}) to {args.url}")
    t_all0 = time.perf_counter()
    for i in range(args.samples):
        p = make_payload(args.winlen)
        t0 = time.perf_counter()
        data, code = post(p)
        if code != 200:
            failures += 1
            continue
        latencies_ms.append((time.perf_counter() - t0) * 1000)
        if i and i % 100 == 0:
            print(f"  → {i} samples processed")
    t_all1 = time.perf_counter()

    if not latencies_ms:
        print("No successful inferences. Check the schema or server.")
        sys.exit(1)

    avg = sum(latencies_ms) / len(latencies_ms)
    p95 = sorted(latencies_ms)[max(0, int(0.95 * len(latencies_ms)) - 1)]
    thr = args.samples / (t_all1 - t_all0)

    print("\n--- EDON Inference Benchmark ---")
    print(f"Total samples: {args.samples}")
    print(f"Successful:    {len(latencies_ms)}")
    print(f"Failures:      {failures}")
    print(f"Avg latency:   {avg:.2f} ms")
    print(f"p95 latency:   {p95:.2f} ms")
    print(f"Throughput:    {thr:.2f} req/sec")
    print("--------------------------------")

if __name__ == "__main__":
    run()
