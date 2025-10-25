import os, glob

def load_md_docs(path="/kb_data/docs"):
    files = sorted(glob.glob(os.path.join(path, "*.md")))
    docs = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fh:
            docs.append({"id": os.path.basename(f), "text": fh.read()})
    return docs
