"""Chỉ in số liệu tổng hợp của test. – T56 bước 3: mẹo bề mặt chiếm bao nhiêu phần cải thiện.

Chạy:  python eval/audit/rescore_fix.py [--out results/audit/rescore_fix.json]

KHÔNG gọi LLM. Lấy Cypher dự đoán đã có trong các file results/runs/<split>/*.json, sửa máy móc, chạy lại
trên Neo4j ở chế độ chỉ đọc (timeout 30 s) và chấm bằng judge của pilot_text2cypher.py:
  - none : không sửa (chạy lại để kiểm tra tái lập nhãn gốc)
  - fix1 : trong chuỗi literal, thay dấu cách bằng '_' (bỏ qua literal chỉ gồm khoảng trắng, vd. ' ' khi ghép họ tên)
  - fix2 : đổi -[:KNOWS…]-> và <-[:KNOWS…]- thành không chiều -[:KNOWS…]-
  - fix3 : fix1 + fix2
Lượt chạy: dev B1 run1 (và proposed v0 để đối chiếu); test B1 run1–2, B3 run1–3.
Với test: chỉ in/ghi số câu theo loại câu và theo template_id (không id câu, không câu hỏi, không Cypher).
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from neo4j import READ_ACCESS, GraphDatabase, Query
from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))
from pilot_text2cypher import AUTH, URI, answer_rows, judge  # noqa: E402

RUNS = ROOT / "results" / "runs"
QDIR = ROOT / "eval" / "questions"
TIMEOUT_S = 30
MAX_ROWS = 1000
TYPES = ["lookup", "aggregation", "multi_hop", "path", "temporal"]
FIXES = ["none", "fix1", "fix2", "fix3"]
RUN_FILES = {
    "dev": ["b1_zeroshot__openai-gpt-oss-20b__run1", "proposed_v0__openai-gpt-oss-20b__run1"],
    "test": ["b1_zeroshot__openai-gpt-oss-20b__run1", "b1_zeroshot__openai-gpt-oss-20b__run2",
             "b1_zeroshot__openai-gpt-oss-120b__run1", "b1_zeroshot__openai-gpt-oss-120b__run2",
             "b1_zeroshot__openai-gpt-oss-120b__run3"],
}

LIT_RE = re.compile(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"")
KNOWS_OUT = re.compile(r"-\[([^\]]*:\s*KNOWS\b[^\]]*)\]->", re.I)
KNOWS_IN = re.compile(r"<-\[([^\]]*:\s*KNOWS\b[^\]]*)\]-(?!>)", re.I)


def fix_underscore(cypher):
    def repl(m):
        quote = "'" if m.group(1) is not None else '"'
        s = m.group(1) if m.group(1) is not None else m.group(2)
        if not s.strip():
            return m.group(0)
        return quote + re.sub(r"(?<=\S) (?=\S)", "_", s) + quote
    return LIT_RE.sub(repl, cypher)


def fix_knows(cypher):
    return KNOWS_IN.sub(r"-[\1]-", KNOWS_OUT.sub(r"-[\1]-", cypher))


APPLY = {"none": lambda c: c, "fix1": fix_underscore, "fix2": fix_knows,
         "fix3": lambda c: fix_knows(fix_underscore(c))}


def run_query(session, cypher):
    result = session.run(Query(cypher, timeout=TIMEOUT_S))
    records = result.fetch(MAX_ROWS + 1)
    result.consume()
    return records


def verdict_of(session, gold_rows, cypher):
    if not cypher:
        return "no_cypher"
    try:
        return judge(gold_rows, run_query(session, cypher))
    except (ServiceUnavailable, SessionExpired):
        raise
    except Neo4jError as e:
        return "timeout" if "TransactionTimedOut" in (e.code or "") else "execution_error"
    except Exception:
        return "execution_error"


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "-"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "results" / "audit" / "rescore_fix.json"))
    args = ap.parse_args()

    report = {"timeout_s": TIMEOUT_S, "fixes": FIXES, "runs": {}}
    driver = GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF")
    with driver, driver.session(default_access_mode=READ_ACCESS) as session:
        for split, names in RUN_FILES.items():
            questions = {q["id"]: q for q in json.loads((QDIR / f"{split}.json").read_text(encoding="utf-8"))}
            gold_cache = {}
            for name in names:
                path = RUNS / split / f"{name}.json"
                if not path.exists():
                    print(f"(thiếu {path.relative_to(ROOT)}, bỏ qua)")
                    continue
                results = json.loads(path.read_text(encoding="utf-8"))["results"]
                n = len(results)
                orig_correct = sum(r["verdict"] == "correct" for r in results)
                correct = {f: 0 for f in FIXES}
                changed = {f: 0 for f in FIXES}            # số câu mà bản sửa làm đổi chuỗi Cypher
                flips = {f: {"w2c": 0, "c2w": 0} for f in FIXES}
                by_type = {t: {"n": 0} | {f: 0 for f in FIXES} for t in TYPES}
                by_tpl = defaultdict(lambda: {"n": 0, "w2c": {f: 0 for f in FIXES}, "c2w": {f: 0 for f in FIXES}})
                dev_flip_ids = {f: [] for f in FIXES}
                reproduced = 0
                for r in results:
                    qid = r["id"]
                    if qid not in gold_cache:
                        gold_cache[qid] = answer_rows(run_query(session, questions[qid]["gold"]))
                    gold_rows = gold_cache[qid]
                    cy = r.get("cypher") or ""
                    t, tpl = r["type"], r["template_id"]
                    by_type[t]["n"] += 1
                    by_tpl[tpl]["n"] += 1
                    base = None
                    for f in FIXES:
                        new_cy = APPLY[f](cy)
                        if f != "none" and new_cy == cy:
                            v = base  # không đổi gì: dùng lại nhãn chạy lại của bản gốc
                        else:
                            v = verdict_of(session, gold_rows, new_cy)
                        if f == "none":
                            base = v
                            reproduced += (v == "correct") == (r["verdict"] == "correct")
                        else:
                            changed[f] += new_cy != cy
                        ok = v == "correct"
                        correct[f] += ok
                        by_type[t][f] += ok
                        if f != "none":
                            was = base == "correct"
                            if ok and not was:
                                flips[f]["w2c"] += 1
                                by_tpl[tpl]["w2c"][f] += 1
                                dev_flip_ids[f].append(qid)
                            elif was and not ok:
                                flips[f]["c2w"] += 1
                                by_tpl[tpl]["c2w"][f] += 1

                print(f"\n=== {split} / {name}  ({n} câu; EX trong file: {orig_correct}/{n} = {pct(orig_correct, n)}; "
                      f"chạy lại tái lập nhãn đúng/sai: {reproduced}/{n})")
                print(f"  {'bản':<5} {'EX':>14} {'sai→đúng':>9} {'đúng→sai':>9} {'Cypher bị đổi':>14}")
                for f in FIXES:
                    print(f"  {f:<5} {correct[f]:>4}/{n} {pct(correct[f], n):>7} {flips[f]['w2c']:>9} "
                          f"{flips[f]['c2w']:>9} {changed[f]:>14}")
                print("  Theo loại câu (EX: none / fix1 / fix2 / fix3):")
                for tt in TYPES:
                    d = by_type[tt]
                    if d["n"]:
                        print(f"    {tt:<12} n={d['n']:<3} " + " / ".join(f"{d[f]}" for f in FIXES))
                print("  Theo template_id (sai→đúng fix1/fix2/fix3 ; đúng→sai fix3):")
                for tpl in sorted(by_tpl):
                    d = by_tpl[tpl]
                    w = "/".join(str(d["w2c"][f]) for f in FIXES[1:])
                    print(f"    {tpl:<7} n={d['n']:<3} +{w:<9} -{d['c2w']['fix3']}")
                if split == "dev":
                    print(f"  id sai→đúng (fix3): {dev_flip_ids['fix3']}")

                entry = {"n": n, "ex_in_file": orig_correct, "reproduced": reproduced,
                         "correct": correct, "cypher_changed": changed, "flips": flips,
                         "by_type": by_type, "by_template": {k: dict(v) for k, v in sorted(by_tpl.items())}}
                if split == "dev":
                    entry["dev_flip_ids"] = dev_flip_ids
                report["runs"][f"{split}/{name}"] = entry

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nĐã lưu {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
