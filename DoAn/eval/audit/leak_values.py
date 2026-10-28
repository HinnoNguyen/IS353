"""Chỉ in số liệu tổng hợp của test. – T56 bước 1: rò rỉ giá trị qua phần văn bản cố định của prompt.

Chạy:  python eval/audit/leak_values.py [--no-neo4j] [--out results/audit/leak_values.json]

Văn bản cố định = mọi đoạn đưa vào prompt mà không phụ thuộc câu hỏi:
  - meta.prompt / fix_prompt / conventions / schema của mọi file results/runs/dev/*.json
  - build_schema(driver) của B1 lấy trực tiếp từ Neo4j (bỏ qua nếu --no-neo4j)
  - detailed_schema của module (A) nếu đã có (eval/baselines/module_a.py hoặc proposed.py có hàm detailed_schema)
Giá trị đem so (của dev và test):
  - params        : giá trị tham số của câu hỏi
  - gold_literal  : chuỗi/số literal trong Cypher gold (bắt cả giá trị viết cứng, không nằm trong params)
  - answer        : giá trị chữ trong answer_preview (đáp án)
Mỗi giá trị so ở dạng có '_' và dạng có dấu cách, không phân biệt hoa thường, khớp theo ranh giới từ.
Số (vd. năm 2011) so như một token riêng.

Quy tắc chống rò rỉ (GIAO_VIEC_KIEM_TRA_BENCHMARK.md mục 2): với test, script KHÔNG in câu hỏi, gold hay id câu;
chỉ in giá trị đã có sẵn trong văn bản prompt (tức là người đọc prompt đã thấy rồi) kèm số câu / template_id bị ảnh hưởng.
"""
import argparse
import importlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))

QDIR = ROOT / "eval" / "questions"
RUNS_DEV = ROOT / "results" / "runs" / "dev"
TEXT_FIELDS = ["prompt", "fix_prompt", "conventions", "schema"]
MIN_LEN = 3  # bỏ chuỗi quá ngắn (vd. 'M', 'en') để tránh trùng vô nghĩa với từ tiếng Anh trong prompt
LIT_RE = re.compile(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"")
NUM_RE = re.compile(r"(?<![\w.])(\d{2,})(?![\w.])")


def forms(value):
    """Các dạng đem so của một giá trị: chữ thường, có '_' và có dấu cách."""
    v = str(value).strip().lower()
    return {v, v.replace("_", " "), v.replace(" ", "_")}


def contains(text_lc, needle):
    """Khớp theo ranh giới từ (không coi '_' là một phần của từ để 'United_States' khớp cả hai dạng)."""
    pat = r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])"
    return re.search(pat, text_lc) is not None


def fixed_texts(use_neo4j):
    """{tên đoạn: văn bản} của mọi đoạn văn bản cố định đưa vào prompt."""
    texts = {}
    for f in sorted(RUNS_DEV.glob("*.json")):
        meta = json.loads(f.read_text(encoding="utf-8"))["meta"]
        for k in TEXT_FIELDS:
            if meta.get(k):
                texts[f"{f.stem}:{k}"] = meta[k]
    if use_neo4j:
        from neo4j import GraphDatabase
        from pilot_text2cypher import AUTH, URI, build_schema
        with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as driver:
            texts["b1:build_schema(live)"] = build_schema(driver)
            for mod_name in ("baselines.module_a", "baselines.proposed", "module_a"):
                try:
                    mod = importlib.import_module(mod_name)
                except ImportError:
                    continue
                if hasattr(mod, "detailed_schema"):
                    texts[f"{mod_name}:detailed_schema"] = mod.detailed_schema(driver)
                    break
            else:
                print("(A) detailed_schema chưa có: bỏ qua, chạy lại khi module (A) xong.\n")
    # Gộp các đoạn giống hệt nhau (vd. cùng một PROMPT trong nhiều file run) để bảng gọn hơn
    by_text = defaultdict(list)
    for name, t in texts.items():
        by_text[t].append(name)
    return {" | ".join(names): t for t, names in by_text.items()}


def question_values(q):
    """[(nguồn, giá trị)] của một câu hỏi."""
    out = [("params", v) for v in q.get("params", {}).values()]
    p = q.get("params", {})
    if "firstName" in p and "lastName" in p:
        out.append(("params", f"{p['firstName']} {p['lastName']}"))
    for m in LIT_RE.finditer(q["gold"]):
        out.append(("gold_literal", m.group(1) if m.group(1) is not None else m.group(2)))
    for m in NUM_RE.finditer(q["gold"]):
        out.append(("gold_literal", m.group(1)))
    for row in q.get("answer_preview") or []:
        for v in row if isinstance(row, list) else [row]:
            if isinstance(v, str):
                out.append(("answer", v))
    return out


def keep(value):
    s = str(value).strip()
    return len(s) >= MIN_LEN or s.isdigit() and len(s) >= 2


def scan(split, questions, texts):
    """Trả về list các lần trùng: (nguồn, giá trị, đoạn, template_id, id câu)."""
    lowered = {name: t.lower() for name, t in texts.items()}
    hits = []
    for q in questions:
        seen = set()
        for src, value in question_values(q):
            if not keep(value):
                continue
            for name, text in lowered.items():
                if any(contains(text, f) for f in forms(value)):
                    key = (src, str(value).lower(), name)
                    if key not in seen:
                        seen.add(key)
                        hits.append({"split": split, "source": src, "value": str(value), "segment": name,
                                     "template_id": q["template_id"], "type": q["type"], "id": q["id"]})
    return hits


def year_check(questions, texts):
    """Năm xuất hiện trong văn bản prompt -> số câu (theo template) có tham số/literal là năm đó."""
    years = sorted({y for t in texts.values() for y in re.findall(r"(?<!\d)(20[01]\d)(?!\d)", t)})
    out = {}
    for y in years:
        tids = defaultdict(int)
        for q in questions:
            vals = {str(v) for _, v in question_values(q)}
            if y in vals or re.search(rf"(?<!\d){y}(?!\d)", q["gold"]):
                tids[q["template_id"]] += 1
        out[y] = dict(tids)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-neo4j", action="store_true", help="không lấy build_schema/detailed_schema trực tiếp")
    ap.add_argument("--out", default=str(ROOT / "results" / "audit" / "leak_values.json"))
    args = ap.parse_args()

    texts = fixed_texts(not args.no_neo4j)
    print(f"Số đoạn văn bản cố định: {len(texts)}")
    for name, t in texts.items():
        print(f"  - {name}  ({len(t)} ký tự)")

    report = {"segments": list(texts), "splits": {}}
    for split in ("dev", "test"):
        questions = json.loads((QDIR / f"{split}.json").read_text(encoding="utf-8"))
        hits = scan(split, questions, texts)
        n_q = len({h["id"] for h in hits})
        print(f"\n=== {split}: {len(questions)} câu, {len(hits)} lần trùng, {n_q} câu bị ảnh hưởng")
        groups = defaultdict(lambda: {"questions": set(), "templates": defaultdict(int)})
        for h in hits:
            g = groups[(h["source"], h["value"].lower(), h["segment"])]
            g["questions"].add(h["id"])
            g["templates"][h["template_id"]] += 1
        rows = []
        for (src, value, seg), g in sorted(groups.items()):
            row = {"source": src, "value": value, "segment": seg, "n_questions": len(g["questions"]),
                   "by_template": dict(g["templates"])}
            if split == "dev":
                row["ids"] = sorted(g["questions"])
            rows.append(row)
            ids = f"  ids={row['ids']}" if split == "dev" else ""
            print(f"  [{src:<12}] '{value}' trong <{seg}>: {len(g['questions'])} câu {dict(g['templates'])}{ids}")
        years = year_check(questions, texts)
        print(f"  Năm xuất hiện trong prompt -> số câu {split} dùng đúng năm đó (theo template): {years}")
        report["splits"][split] = {"n_questions": len(questions), "n_hits": len(hits),
                                   "n_questions_affected": n_q, "matches": rows, "years_in_prompt": years}

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nĐã lưu {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
