"""Kiểm tra chéo bộ câu hỏi (eval/QA_GUIDELINE.md mục 6).

Chạy:  python eval/cross_check.py export  --reviewer Ân   # chọn 20% câu mỗi loại, xuất file KHÔNG có gold
       python eval/cross_check.py compare --reviewer Ân   # chạy Cypher của người kiểm tra + gold, chấm, in tỉ lệ đồng thuận

File người kiểm tra điền: eval/cross_check/<reviewer>.json (trường my_cypher)
Kết quả:                  eval/cross_check/<reviewer>_result.json (trường cause, action điền khi thảo luận)
Câu được chọn lấy từ dev.json + test.json (seed cố định); chấm bằng hàm judge của pilot_text2cypher.
"""
import argparse
import json
import math
import os
import random
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase, Query

from pilot_text2cypher import answer_rows, judge

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "graphqa123"))
QDIR = ROOT / "eval" / "questions"
OUT_DIR = ROOT / "eval" / "cross_check"
TYPES = ["lookup", "aggregation", "multi_hop", "path", "temporal"]
SEED = 353
RATIO = 0.2
TIMEOUT_S = 30


def all_questions():
    return json.loads((QDIR / "dev.json").read_text(encoding="utf-8")) + \
        json.loads((QDIR / "test.json").read_text(encoding="utf-8"))


def export(reviewer):
    path = OUT_DIR / f"{reviewer}.json"
    if path.exists() and any(q["my_cypher"] for q in json.loads(path.read_text(encoding="utf-8"))):
        raise SystemExit(f"{path} đã có Cypher được điền – không ghi đè.")
    rng = random.Random(SEED)
    questions, picked = all_questions(), []
    for t in TYPES:
        ids = sorted(q["id"] for q in questions if q["type"] == t)
        picked += sorted(rng.sample(ids, math.ceil(RATIO * len(ids))))
    by_id = {q["id"]: q for q in questions}
    items = [{"id": i, "type": by_id[i]["type"], "question": by_id[i]["question"], "my_cypher": ""} for i in picked]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Đã xuất {len(items)} câu -> {path.relative_to(ROOT)}")


def preview(rows):
    return [[str(v) for v in row] for row in rows[:5]]


def compare(reviewer):
    items = json.loads((OUT_DIR / f"{reviewer}.json").read_text(encoding="utf-8"))
    result_path = OUT_DIR / f"{reviewer}_result.json"
    old = {r["id"]: r for r in json.loads(result_path.read_text(encoding="utf-8"))} if result_path.exists() else {}
    current = {q["id"]: q for q in all_questions()}
    results = []
    with GraphDatabase.driver(URI, auth=AUTH) as driver, driver.session() as session:
        def run(cypher):
            return list(session.run(Query(cypher, timeout=TIMEOUT_S)))
        for it in items:
            r = {"id": it["id"], "type": it["type"], "question": it["question"], "my_cypher": it["my_cypher"]}
            # sinh lại câu sau khi sửa template có thể làm id trỏ sang câu khác hoặc câu bị loại
            if it["id"] not in current or current[it["id"]]["question"] != it["question"]:
                r["verdict"] = "câu đã đổi"
                results.append(r)
                continue
            r["gold"] = current[it["id"]]["gold"]
            gold_rows = answer_rows(run(r["gold"]))
            r["gold_preview"] = preview(gold_rows)
            if not it["my_cypher"].strip():
                r["verdict"] = "chưa làm"
            else:
                try:
                    mine = run(it["my_cypher"])
                    r["my_preview"] = preview([list(rec.values()) for rec in mine])
                    r["verdict"] = "khớp" if judge(gold_rows, mine) == "correct" else "không khớp"
                except Exception as e:
                    r["verdict"] = "lỗi"
                    r["error"] = str(e).splitlines()[0][:200]
            r["cause"] = old.get(it["id"], {}).get("cause", "")
            r["action"] = old.get(it["id"], {}).get("action", "")
            results.append(r)
    result_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"{'Loại':<12} {'Đã làm':>6} {'Khớp':>5} {'Đồng thuận':>11}")
    done_all = agree_all = 0
    for t in TYPES + ["Tổng"]:
        rs = [r for r in results if (t == "Tổng" or r["type"] == t) and r["verdict"] in ("khớp", "không khớp", "lỗi")]
        agree = sum(r["verdict"] == "khớp" for r in rs)
        rate = f"{agree / len(rs):.0%}" if rs else "-"
        flag = "  <- dưới 90%, rà lại cả loại" if rs and t != "Tổng" and agree / len(rs) < 0.9 else ""
        print(f"{t:<12} {len(rs):>6} {agree:>5} {rate:>11}{flag}")
    todo = [r["id"] for r in results if r["verdict"] == "chưa làm"]
    bad = [r for r in results if r["verdict"] in ("không khớp", "lỗi")]
    changed = [r["id"] for r in results if r["verdict"] == "câu đã đổi"]
    if todo:
        print(f"\nChưa làm ({len(todo)}): {', '.join(todo)}")
    if changed:
        print(f"\nCâu đã đổi sau khi sinh lại, không chấm ({len(changed)}): {', '.join(changed)}")
    if bad:
        print(f"\nCần thảo luận ({len(bad)}):")
        for r in bad:
            print(f"  {r['id']} [{r['verdict']}] {r['question']}")
    print(f"\nĐã lưu {result_path.relative_to(ROOT)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["export", "compare"])
    ap.add_argument("--reviewer", required=True, help="tên người kiểm tra, vd. Ân")
    args = ap.parse_args()
    export(args.reviewer) if args.command == "export" else compare(args.reviewer)


if __name__ == "__main__":
    main()
