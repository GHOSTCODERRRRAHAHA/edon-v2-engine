import argparse, json, math, time, random, os
def generate_scenario(kind, seconds, hz):
    frames = []
    steps = int(seconds * hz)
    base_ts = time.time()
    for i in range(steps):
        t = i / hz
        co2 = 600
        dba = 40
        if kind == "overload_pulse":
            co2 += 600 * abs(math.sin(t * math.pi * 2 / seconds))
            dba += 25 * abs(math.sin(t * math.pi * 2 / seconds))
        elif kind == "overload_ramp":
            co2 += 10 * i
            dba += 0.5 * i
        elif kind == "restorative":
            co2 -= 3 * i
            dba -= 0.2 * i
        frame = {
            "ts": base_ts + t,
            "env": {"co2": round(co2, 1), "dba": round(dba, 1), "lux": random.randint(200, 500), "temp_c": 22.5}
        }
        frames.append(frame)
    return frames
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--hz", type=float, default=5)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    frames = generate_scenario(args.scenario, args.seconds, args.hz)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for fr in frames:
            f.write(json.dumps(fr) + "\n")
    print(f"✅ Wrote {len(frames)} frames to {args.out}")
