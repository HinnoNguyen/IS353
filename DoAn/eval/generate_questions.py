"""Sinh bộ câu hỏi QA từ template (theo eval/QA_GUIDELINE.md).

Mỗi file eval/templates/<loại>.json là danh sách template gồm:
  template_id, type, author, note
  questions   : 2–3 cách diễn đạt, chỗ trống {tên_tham_số}
  gold        : Cypher có tham số $tên_tham_số
  candidates  : Cypher trả về các bộ tham số hợp lệ (cột = tên tham số), có ORDER BY để ổn định

Với mỗi template, script lấy ngẫu nhiên tham số (seed cố định), chạy gold và loại câu theo guideline:
đáp án rỗng hoặc bằng 0, quá 20 dòng, chạy quá 10 s, người trùng họ tên, câu trùng lặp,
và thực thể đã dùng trong eval/pilot_questions.json (tránh rò rỉ).

Chạy:  python eval/generate_questions.py                 # mọi loại
       python eval/generate_questions.py --type lookup   # một loại
Kết quả: eval/questions/<loại>.json (chưa chia dev/test).
"""
import argparse
import json
import os
import random
import re
import zlib
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase, Query

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "graphqa123"))
TEMPLATE_DIR = ROOT / "eval" / "templates"
OUT_DIR = ROOT / "eval" / "questions"
PILOT = ROOT / "eval" / "pilot_questions.json"

SEED = 353
PER_TEMPLATE = 10       # số câu giữ lại mỗi template
MAX_ROWS = 20           # đáp án dài hơn thì loại (guideline mục 3.5)
TIMEOUT_S = 10          # gold chạy lâu hơn thì loại (guideline mục 3.6)


def pilot_entities():
    """Các chuỗi trong dấu nháy của Cypher gold pilot (tên người, tag, quốc gia…) – không dùng lại."""
    if not PILOT.exists():
        return set()
    gold = " ".join(q["gold"] for q in json.loads(PILOT.read_text(encoding="utf-8")))
    return set(re.findall(r"'([^']+)'", gold))


def display(value):
    """Giá trị hiển thị trong câu hỏi: tên tự nhiên (United_States -> United States)."""
    return value.replace("_", " ") if isinstance(value, str) else str(value)


def literal(value):
    """Giá trị Cypher để nhúng tham số vào gold (giúp gold chạy được độc lập)."""
    if isinstance(value, str):
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
    return json.dumps(value)


def inline(cypher, params):
    for name in sorted(params, key=len, reverse=True):
        cypher = cypher.replace("$" + name, literal(params[name]))
    return cypher


def run(session, cypher, params=None):
    result = session.run(Query(cypher, timeout=TIMEOUT_S), params or {})
    return [list(r.values()) for r in result]


def unique_person(session, params):
    if "firstName" not in params or "lastName" not in params:
        return True
    rows = run(session, "MATCH (p:Person {firstName: $firstName, lastName: $lastName}) RETURN count(p)", params)
    return rows[0][0] == 1


def reject_reason(rows):
    if not rows:
        return "empty"
    if len(rows) == 1 and len(rows[0]) == 1 and rows[0][0] in (0, None):
        return "zero"
    if len(rows) > MAX_ROWS:
        return "too_many_rows"
    return None


def generate(session, tpl, banned):
    rng = random.Random(SEED + zlib.crc32(tpl["template_id"].encode()))
    candidates = [dict(zip(r.keys(), r.values())) for r in session.run(tpl["candidates"])]
    rng.shuffle(candidates)
    kept, stats, seen = [], {}, set()
    for params in candidates:
        if len(kept) >= PER_TEMPLATE:
            break
        reason = None
        if any(isinstance(v, str) and v in banned for v in params.values()):
            reason = "pilot_entity"
        elif not unique_person(session, params):
            reason = "duplicate_name"
        if reason is None:
            try:
                rows = run(session, tpl["gold"], params)
                reason = reject_reason(rows)
            except Exception as e:  # timeout hoặc lỗi Cypher
                reason = "error_or_timeout"
                print(f"  {tpl['template_id']} lỗi: {str(e).splitlines()[0][:120]}")
        phrasing = tpl["questions"][len(kept) % len(tpl["questions"])]
        question = phrasing.format(**{k: display(v) for k, v in params.items()})
        if reason is None and question in seen:
            reason = "duplicate_question"
        if reason:
            stats[reason] = stats.get(reason, 0) + 1
            continue
        seen.add(question)
        kept.append({
            "id": f"{tpl['template_id']}-{len(kept) + 1:02d}",
            "template_id": tpl["template_id"],
            "type": tpl["type"],
            "question": question,
            "gold": inline(tpl["gold"], params),
            "params": params,
            "answer_preview": [[str(v) for v in row] for row in rows[:5]],
            "author": tpl.get("author", ""),
            "checked_by": "",
            "note": "",
        })
    return kept, stats, len(candidates)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", help="chỉ sinh một loại (tên file trong eval/templates, không có .json)")
    args = ap.parse_args()
    files = sorted(TEMPLATE_DIR.glob("*.json"))
    if args.type:
        files = [f for f in files if f.stem == args.type]
    banned = pilot_entities()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with GraphDatabase.driver(URI, auth=AUTH) as driver, driver.session() as session:
        for f in files:
            templates = json.loads(f.read_text(encoding="utf-8"))
            questions = []
            print(f"== {f.stem}")
            for tpl in templates:
                kept, stats, n_cand = generate(session, tpl, banned)
                questions.extend(kept)
                print(f"  {tpl['template_id']}: giữ {len(kept)}/{PER_TEMPLATE} (ứng viên {n_cand}), loại {stats or '-'}")
            out = OUT_DIR / f"{f.stem}.json"
            out.write_text(json.dumps(questions, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
            print(f"  -> {out.relative_to(ROOT)} ({len(questions)} câu)")


if __name__ == "__main__":
    main()
