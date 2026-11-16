"""T34 – Tác động của (D) trong một lượt chạy: chạy lại first_cypher (Cypher trước khi sửa) và chấm như run_eval.

Chạy:  python eval/audit/misrepair.py results/runs/dev_zero/proposed_ad__openai-gpt-oss-20b__run1.json [...]
       thêm --json <file> để ghi số liệu từng câu và bảng tổng hợp.

Với mỗi file in: EX trước sửa (first_cypher) và sau sửa; số câu được cứu (sai -> đúng); số câu bị sửa nhầm
(đúng -> sai); tỉ lệ sửa nhầm = sửa nhầm / số câu có first_cypher đúng (GIAO_VIEC_CUOI_KY.md mục 5.4).
Tách theo subset (zero = đáp án đúng là rỗng/0, normal = còn lại). Chỉ đọc kết quả có info.first_cypher.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))

from neo4j import READ_ACCESS, GraphDatabase  # noqa: E402

from pilot_text2cypher import AUTH, URI  # noqa: E402
from proposed.repair_d import same_query  # noqa: E402
from run_eval import evaluate  # noqa: E402


def analyse(session, path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = []
    for r in data["results"]:
        info = r.get("info") or {}
        if "first_cypher" not in info:
            continue
        changed = not same_query(info["first_cypher"], r["cypher"])
        first = evaluate(session, r, {"cypher": info["first_cypher"], "seconds": 0})[0]["verdict"] if changed \
            else r["verdict"]
        rows.append({"id": r["id"], "type": r["type"], "subset": r.get("subset", "normal"), "first": first,
                     "final": r["verdict"], "changed": changed, "decisions": info.get("decisions", []),
                     "problems": info.get("problems", []), "llm_calls": info.get("llm_calls", 1)})
    return data["meta"], rows


def summary(rows):
    first_ok = [r for r in rows if r["first"] == "correct"]
    broken = [r["id"] for r in first_ok if r["final"] != "correct"]
    rescued = [r["id"] for r in rows if r["first"] != "correct" and r["final"] == "correct"]
    decisions = Counter(d for r in rows for d in r["decisions"])
    return {"n": len(rows), "first_correct": len(first_ok), "final_correct": sum(r["final"] == "correct" for r in rows),
            "rescued": rescued, "broken": broken,
            "misrepair_rate": round(len(broken) / len(first_ok), 4) if first_ok else None,
            "sent_to_d": sum(bool(r["problems"]) for r in rows), "changed": sum(r["changed"] for r in rows),
            "decisions": dict(decisions), "avg_llm_calls": round(sum(r["llm_calls"] for r in rows) / len(rows), 2)}


def main():
    ap = argparse.ArgumentParser(description="Tỉ lệ (D) sửa nhầm và số câu (D) cứu được trong một lượt chạy.")
    ap.add_argument("runs", nargs="+", help="file results/runs/<split>/<tên>.json có info.first_cypher")
    ap.add_argument("--json", help="ghi số liệu ra file này")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    out = {}
    with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as driver, \
            driver.session(default_access_mode=READ_ACCESS) as session:
        for path in args.runs:
            meta, rows = analyse(session, path)
            if not rows:
                print(f"{path}: không có câu nào có info.first_cypher (baseline không có (D)?)")
                continue
            groups = {"tất cả": rows} | {s: [r for r in rows if r["subset"] == s]
                                         for s in sorted({r["subset"] for r in rows})}
            table = {name: summary(rs) for name, rs in groups.items()}
            out[path] = {"meta": {k: meta.get(k) for k in ("baseline", "model", "split", "run", "commit")},
                         "summary": table, "rows": rows}
            print(f"\n{path}  ({meta.get('baseline')}, {meta.get('model')}, {meta.get('split')})")
            print("| Nhóm | Số câu | EX trước sửa | EX sau sửa | Được cứu | Sửa nhầm | Tỉ lệ sửa nhầm | Gửi (D) | Đổi truy vấn |"
                  " LLM/câu |")
            print("|---|---|---|---|---|---|---|---|---|---|")
            for name, s in table.items():
                rate = "–" if s["misrepair_rate"] is None else f"{100 * s['misrepair_rate']:.1f}%"
                print(f"| {name} | {s['n']} | {s['first_correct']} | {s['final_correct']} | {len(s['rescued'])} | "
                      f"{len(s['broken'])} | {rate} | {s['sent_to_d']} | {s['changed']} | {s['avg_llm_calls']} |")
            s = table["tất cả"]
            print(f"Quyết định của (D): {s['decisions'] or '-'}")
            print(f"Được cứu: {', '.join(s['rescued']) or '-'}  |  Sửa nhầm: {', '.join(s['broken']) or '-'}")
    if args.json:
        Path(args.json).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\nĐã ghi {args.json}")


if __name__ == "__main__":
    main()
