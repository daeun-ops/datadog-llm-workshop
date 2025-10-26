import os,json,time,random,requests
from statistics import mean

EVAL_FILE=os.getenv("EVAL_FILE","data/eval.jsonl")
RAG_URL=os.getenv("RAG_URL","http://localhost:7000/query")

def load():
    with open(EVAL_FILE,"r",encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line:
                continue
            yield json.loads(line)
          
def run():
    lat=[]
    varcnt={"A":0,"B":0}
    for row in load():
        r=requests.post(RAG_URL,json={"q":row["question"]},timeout=30).json()
        lat.append(r["latency_s"])
        varcnt[r["variant"]]+=1
    print(json.dumps({"count":len(lat),"avg_latency":mean(lat) if lat else 0,"variant_split":varcnt},ensure_ascii=False))
if __name__=="__main__":
    run()
