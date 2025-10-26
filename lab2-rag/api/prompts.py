import os, yaml

PROMPT_PATH = os.path.join(os.path.dirname(__file__), "prompts.yaml")

def load_prompts():
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

_PROMPTS = load_prompts()

def get_prompt(version: str, q: str, ctx: str) -> str:
    tmpl = _PROMPTS.get(version) or _PROMPTS["v1"]
    return tmpl.format(q=q, ctx=ctx)
