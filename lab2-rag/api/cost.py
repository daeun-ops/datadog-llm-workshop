RATES = {
    # example rates (USD per 1K tokens); adjust per your infra
    "llama3.1": {"input": 0.2/1000, "output": 0.2/1000},
}

def estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / 4))

def estimate_cost_usd(model: str, prompt: str, completion: str|None) -> float:
    r = RATES.get(model, {"input":0.0001, "output":0.0001})
    t_in = estimate_tokens(prompt or "")
    t_out = estimate_tokens((completion or ""))
    return t_in * r["input"] + t_out * r["output"]
