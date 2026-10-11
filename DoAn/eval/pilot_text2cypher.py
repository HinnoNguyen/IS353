"""Thử nghiệm sơ bộ (pilot) = baseline B1: LLM zero-shot sinh Cypher trên LDBC SNB SF0.1.

Với mỗi câu hỏi:
  1. Đưa schema của đồ thị + câu hỏi cho LLM, yêu cầu trả về 1 câu Cypher.
  2. Chạy câu Cypher sinh ra và câu Cypher đúng (gold) trên Neo4j.
  3. So sánh kết quả (execution accuracy) và phân loại lỗi.

Chạy:  python eval/pilot_text2cypher.py
Mặc định dùng LLM local qua Ollama (cần Ollama đang chạy và đã `ollama pull <model>`).
Biến môi trường (.env), đều tùy chọn:
  LLM_BACKEND=ollama|gemini   OLLAMA_MODEL, OLLAMA_URL   GEMINI_MODEL, GOOGLE_GEMINI_API_KEY
  NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD
"""
import json
import os
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BACKEND = os.getenv("LLM_BACKEND", "ollama")
MODEL = (os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b") if BACKEND == "ollama"
         else os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
SEED = 42
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "graphqa123"))
QUESTIONS = ROOT / "eval" / "pilot_questions.json"
OUT_DIR = ROOT / "results"
SLEEP_BETWEEN_CALLS = 7 if BACKEND == "gemini" else 0  # Gemini free tier giới hạn số request/phút

PROMPT = """You are an expert Neo4j developer. Write one Cypher query that answers the question
using only the graph schema below. Return only the Cypher query, with no explanation.

Schema:
{schema}

Question: {question}
Cypher:"""


def build_schema(driver):
    """Schema dạng chữ: thuộc tính theo nhãn node + các mẫu quan hệ (nguồn)-[TYPE]->(đích)."""
    records, _, _ = driver.execute_query(
        "CALL db.schema.nodeTypeProperties() YIELD nodeLabels, propertyName, propertyTypes "
        "RETURN nodeLabels, collect(propertyName + ': ' + propertyTypes[0]) AS props")
    lines = ["Node labels and properties:"]
    for r in sorted(records, key=lambda r: r["nodeLabels"]):
        lines.append(f"  (:{':'.join(r['nodeLabels'])}) {{{', '.join(sorted(r['props']))}}}")
    records, _, _ = driver.execute_query(
        "MATCH (a)-[r]->(b) WITH DISTINCT labels(a) AS la, type(r) AS t, labels(b) AS lb, "
        "keys(r) AS ks RETURN la, t, lb, collect(DISTINCT ks)[0] AS ks")
    lines.append("Relationships:")
    seen = set()
    for r in records:
        line = f"  (:{':'.join(r['la'])})-[:{r['t']}{' {' + ', '.join(r['ks']) + '}' if r['ks'] else ''}]->(:{':'.join(r['lb'])})"
        if line not in seen:
            seen.add(line)
            lines.append(line)
    return "\n".join(lines)


def extract_cypher(text):
    text = (text or "").strip()
    m = re.search(r"```(?:cypher)?\s*(.*?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip().rstrip(";")


def ask_ollama(prompt):
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False,
                       "options": {"temperature": 0, "seed": SEED}}).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:  # chạy bằng CPU có thể mất vài chục giây mỗi câu
        return extract_cypher(json.loads(resp.read())["message"]["content"])


def ask_gemini(client, prompt):
    from google.genai import types
    for attempt in range(4):
        try:
            resp = client.models.generate_content(
                model=MODEL, contents=prompt,
                config=types.GenerateContentConfig(temperature=0, seed=SEED))
            return extract_cypher(resp.text)
        except Exception as e:  # 429 / 5xx / lỗi mạng: chờ rồi thử lại
            daily_quota = getattr(e, "code", None) == 429 and "PerDay" in str(e)
            if attempt == 3 or daily_quota or getattr(e, "code", None) in (400, 401, 403, 404):
                raise
            wait = 30 * (attempt + 1)
            print(f"    LLM lỗi ({str(e)[:80]}), chờ {wait}s...")
            time.sleep(wait)


def make_llm():
    """Trả về hàm prompt -> Cypher theo backend đã chọn."""
    if BACKEND == "ollama":
        return ask_ollama
    from google import genai
    client = genai.Client(api_key=os.environ["GOOGLE_GEMINI_API_KEY"])
    return lambda prompt: ask_gemini(client, prompt)


def norm(v):
    if isinstance(v, float):
        return str(round(v, 4))
    return str(v).strip().lower()


def row_values(row):
    """Tập giá trị của 1 dòng; thêm chuỗi ghép các cột chữ để 'Anupam' + 'Reddy' khớp 'Anupam Reddy'."""
    vals = [v for v in row if not isinstance(v, (list, dict))]
    out = {norm(v) for v in vals}
    strings = [str(v) for v in vals if isinstance(v, str)]
    if len(strings) > 1:
        out.add(norm(" ".join(strings)))
    for v in row:
        if isinstance(v, list):
            out |= {norm(x) for x in v}
    return out


def answer_rows(records):
    """Đáp án của câu gold: bỏ cột đếm phụ (n) nếu còn cột khác."""
    rows = []
    for rec in records:
        keys = [k for k in rec.keys() if k != "n"] or list(rec.keys())
        rows.append([rec[k] for k in keys])
    return rows


def run(driver, cypher):
    records, _, _ = driver.execute_query(cypher, routing_="r")
    return records


def judge(gold_rows, pred_records):
    """Đúng khi: số dòng bằng nhau và mọi dòng đáp án đều nằm trong một dòng kết quả dự đoán."""
    if not pred_records:
        return "empty_result"
    pred_sets = [row_values(list(r.values())) for r in pred_records]
    covered = all(any(set(map(norm, g)) <= p or norm(" ".join(map(str, g))) in p for p in pred_sets)
                  for g in gold_rows)
    if covered and len(pred_records) == len(gold_rows):
        return "correct"
    return "wrong_result"


def main():
    llm = make_llm()
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    driver = GraphDatabase.driver(URI, auth=AUTH)
    schema = build_schema(driver)
    # Cache câu Cypher đã sinh theo model, để chạy lại không phải gọi LLM lần nữa và không mất tiến độ khi lỗi
    safe_model = MODEL.replace(":", "-").replace("/", "-")
    cache_path = OUT_DIR / f"pilot_cache_{BACKEND}_{safe_model}.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    results = []
    for q in questions:
        gold_rows = answer_rows(run(driver, q["gold"]))
        key = q["id"]
        if key not in cache:
            try:
                start = time.time()
                cypher = llm(PROMPT.format(schema=schema, question=q["question"]))
                cache[key] = {"cypher": cypher, "seconds": round(time.time() - start, 1)}
                OUT_DIR.mkdir(exist_ok=True)
                cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
                time.sleep(SLEEP_BETWEEN_CALLS)
            except Exception as e:
                print(f"{q['id']} {q['type']:<12} llm_unavailable ({str(e)[:60]})")
                continue
        cypher, seconds = cache[key]["cypher"], cache[key]["seconds"]
        try:
            pred = run(driver, cypher)
            verdict = judge(gold_rows, pred)
            pred_preview = [list(r.values()) for r in pred[:3]]
        except Exception as e:
            verdict, pred_preview = "execution_error", str(e).splitlines()[0][:200]
        results.append({"id": q["id"], "type": q["type"], "question": q["question"],
                        "gold_answer": gold_rows, "cypher": cypher, "seconds": seconds,
                        "pred_preview": pred_preview, "verdict": verdict})
        print(f"{q['id']} {q['type']:<12} {verdict:<16} {seconds}s")
    driver.close()
    missing = len(questions) - len(results)
    if missing:
        print(f"\nCòn {missing} câu chưa có Cypher do LLM lỗi — chạy lại script để bổ sung.")

    OUT_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    meta = {"backend": BACKEND, "model": MODEL, "prompt": "zero-shot + auto-extracted schema",
            "temperature": 0, "seed": SEED, "timestamp": stamp, "schema": schema}
    (OUT_DIR / f"pilot_{stamp}.json").write_text(
        json.dumps({"meta": meta, "results": results}, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8")
    write_report(results, meta, OUT_DIR / f"pilot_{stamp}.md")


def write_report(results, meta, path):
    def acc(rows):
        return f"{sum(r['verdict'] == 'correct' for r in rows)}/{len(rows)}"

    lines = [f"# Pilot Text2Cypher — {meta['backend']}/{meta['model']} (zero-shot), {meta['timestamp']}\n",
             "## Execution accuracy\n", "| Nhóm | Đúng | Thời gian TB (s) |", "|---|---|---|"]
    groups = sorted({r["type"] for r in results}, key=lambda t: [r["type"] for r in results].index(t))
    for g in groups + ["TỔNG"]:
        rows = results if g == "TỔNG" else [r for r in results if r["type"] == g]
        avg = sum(r["seconds"] for r in rows) / len(rows) if rows else 0
        lines.append(f"| {g} | {acc(rows)} | {avg:.1f} |")
    lines += ["\n## Phân loại kết quả\n", "| Kết quả | Số lượng |", "|---|---|"]
    for v in ("correct", "wrong_result", "empty_result", "execution_error"):
        lines.append(f"| {v} | {sum(r['verdict'] == v for r in results)} |")
    lines.append("\n## Chi tiết\n")
    for r in results:
        lines += [f"### {r['id']} {r['type']} — **{r['verdict']}** ({r['seconds']}s)",
                  f"- Câu hỏi: {r['question']}", f"- Đáp án đúng: `{r['gold_answer']}`",
                  f"- Kết quả LLM (≤3 dòng): `{r['pred_preview']}`",
                  f"```cypher\n{r['cypher']}\n```\n"]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nĐã lưu {path}")


if __name__ == "__main__":
    main()
