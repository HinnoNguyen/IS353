"""T34 – Chạy lại vòng (D) hiện tại trên first_cypher của một lượt chạy có sẵn (không sinh lại Cypher), rồi chấm.

Dùng để chỉnh (D) trên dev/dev_zero mà không tốn token cho lần sinh Cypher đầu: mọi phiên bản (D) được so trên
CÙNG các truy vấn đầu (so sánh theo cặp). Prompt sinh Cypher và schema lấy từ meta của file kết quả.

Chạy:  python eval/audit/replay_d.py results/runs/dev_zero/proposed_ad__openai-gpt-oss-20b__run1.json \
           --tag v2 [--limit N]
Các lần gọi LLM được cache ở results/cache/replay_d__<tag>__<tên file>: hết hạn mức thì chạy lại đúng lệnh.
Kết quả: results/audit/repair_d/<split>_<tag>.json (số liệu từng câu + bảng tổng hợp như misrepair.py).
Chỉ dùng trên dev, dev_zero. KHÔNG dùng trên test2.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))
sys.path.insert(0, str(ROOT / "eval" / "audit"))

from neo4j import READ_ACCESS, GraphDatabase  # noqa: E402

from llm import DailyLimitError  # noqa: E402
from misrepair import summary  # noqa: E402
from pilot_text2cypher import AUTH, URI  # noqa: E402
from proposed import repair_d  # noqa: E402
from run_eval import CACHE_DIR, evaluate, save_json  # noqa: E402

OUT_DIR = ROOT / "results" / "audit" / "repair_d"


def main():
    ap = argparse.ArgumentParser(description="Chạy lại (D) hiện tại trên first_cypher của một lượt chạy có sẵn.")
    ap.add_argument("run", help="file results/runs/<split>/<tên>.json có info.first_cypher")
    ap.add_argument("--tag", required=True, help="tên phiên bản (D), vd. v2 – dùng cho tên cache và file kết quả")
    ap.add_argument("--limit", type=int, default=None, help="chỉ chạy N câu đầu để thử")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    data = json.loads(Path(args.run).read_text(encoding="utf-8"))
    meta = data["meta"]
    if meta["split"] not in ("dev", "dev_zero"):
        raise SystemExit("Chỉ chạy lại (D) trên dev hoặc dev_zero.")
    head_template = meta["prompt"].removesuffix("Cypher:")
    results = [r for r in data["results"] if "first_cypher" in (r.get("info") or {})][:args.limit]
    cache_path = CACHE_DIR / f"replay_d__{args.tag}__{Path(args.run).name}"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    rows, stopped = [], None
    with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as driver, \
            driver.session(default_access_mode=READ_ACCESS) as session:
        for r in results:
            first = r["info"]["first_cypher"]
            if r["id"] not in cache:
                head = head_template.format(schema=meta["schema"], question=r["question"])
                try:
                    cypher, info = repair_d.repair(meta["model"], session, head, first)
                except DailyLimitError as e:
                    stopped = str(e)[:200]
                    break
                cache[r["id"]] = {"cypher": cypher, "info": info}
                save_json(cache_path, cache)
            entry = cache[r["id"]]
            final = evaluate(session, r, {"cypher": entry["cypher"], "seconds": 0})[0]["verdict"]
            first_verdict = final if repair_d.same_query(first, entry["cypher"]) else \
                evaluate(session, r, {"cypher": first, "seconds": 0})[0]["verdict"]
            info = entry["info"]
            rows.append({"id": r["id"], "type": r["type"], "subset": r.get("subset", "normal"),
                         "first": first_verdict, "final": final,
                         "changed": not repair_d.same_query(first, entry["cypher"]),
                         "decisions": info["decisions"], "problems": info["problems"],
                         "llm_calls": 1 + info["fix_calls"], "cypher": entry["cypher"]})
            print(f"{r['id']:<10} {first_verdict:<14} -> {final:<14} {info['decisions']}")

    if stopped:
        raise SystemExit(f"\nDỪNG (hết hạn mức Groq): {stopped}\nChạy lại đúng lệnh này để làm tiếp.")
    groups = {"tất cả": rows} | {s: [x for x in rows if x["subset"] == s] for s in sorted({x["subset"] for x in rows})}
    table = {name: summary(rs) for name, rs in groups.items()}
    for name, s in table.items():
        rate = "–" if s["misrepair_rate"] is None else f"{100 * s['misrepair_rate']:.1f}%"
        print(f"{name}: EX trước sửa {s['first_correct']}/{s['n']}, sau sửa {s['final_correct']}/{s['n']}, "
              f"cứu {len(s['rescued'])}, sửa nhầm {len(s['broken'])} ({rate}), LLM/câu {s['avg_llm_calls']}, "
              f"quyết định {s['decisions']}")
    if not args.limit:
        out = OUT_DIR / f"{meta['split']}_{args.tag}.json"
        save_json(out, {"source_run": Path(args.run).as_posix(), "tag": args.tag, "model": meta["model"],
                        "d_options": repair_d.llm_options(meta["model"]), "summary": table, "rows": rows})
        print(f"\nĐã lưu {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
