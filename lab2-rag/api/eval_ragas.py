# Simple RAG evaluation runner using RAGAS-style dataset
# dataset format: JSONL with {"question": "...", "ground_truth": "..."}
import json, argparse, statistics, time, requests

def run_eval(api, path, limit=None):
    qs = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit and i >= limit: break
            qs.append(json.loads(line))

    latencies = []
    hits = 0
    total = 0
    for row in qs:
        q = row["question"]
        gt = row.get("ground_truth", "")
        t0 = time.time()
        r = requests.post(f"{api}/ask", json={"question": q, "top_k": 8}, timeout=60)
        dt = time.time() - t0
        latencies.append(dt)
        total += 1
        if r.ok:
            ans = r.json().get("answer","")
            # naive hit: GT substring present
            ok = (gt.lower() in ans.lower()) if gt else (len(ans)>0)
            hits += 1 if ok else 0
        else:
            print("ERR", r.status_code, r.text[:200])

    p = hits/total if total else 0.0
    lat_p50 = statistics.median(latencies) if latencies else 0
    lat_p95 = statistics.quantiles(latencies, n=20)[-1] if len(latencies)>=20 else max(latencies or [0])
    print(json.dumps({"precision_like": round(p,3), "p50": round(lat_p50,3), "p95": round(lat_p95,3)}, indent=2))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8081")
    ap.add_argument("--dataset", default="./data/eval.jsonl")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    run_eval(args.api, args.dataset, args.limit)
