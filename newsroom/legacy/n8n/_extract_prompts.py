import json, pathlib, io, sys

root = pathlib.Path(r"D:\Work\n8n")
out = io.StringIO()

KEYS = ("text", "systemMessage", "content", "message", "prompt", "code", "jsCode", "jsonBody")
SKIP_TYPES = ("stickyNote",)

def walk(obj, path=""):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in KEYS and isinstance(v, str) and len(v) > 120 and any(ch in v for ch in ("你", "请", "评分", "文章")):
                hits.append((k, v))
            else:
                hits.extend(walk(v, path + "/" + str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(walk(v, path + f"[{i}]"))
    return hits

for f in sorted(root.glob("*.json")):
    try:
        data = json.loads(f.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        out.write(f"\n### {f.name}  [解析失败 {e}]\n")
        continue
    nodes = data.get("nodes") or []
    out.write(f"\n{'='*70}\n### {f.name}   （{len(nodes)} 节点）\n")
    for n in nodes:
        t = str(n.get("type", ""))
        if any(s in t for s in SKIP_TYPES):
            continue
        if "lmChat" not in t and "agent" not in t.lower() and "openAi" not in t and "chainLlm" not in t:
            continue
        name = n.get("name")
        model = (n.get("parameters") or {}).get("model") or (n.get("parameters") or {}).get("modelId")
        out.write(f"\n--- [{name}]  type={t.split('.')[-1]}  model={model}\n")
        for k, v in walk(n.get("parameters") or {}):
            out.write(f"    <{k}>\n{v.strip()[:1800]}\n")

txt = out.getvalue()
pathlib.Path(r"D:\Work\n8n\_prompts_dump.txt").write_text(txt, encoding="utf-8")
print("chars:", len(txt))
print("files scanned:", len(list(root.glob('*.json'))))
