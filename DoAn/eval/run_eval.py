"""Khung đánh giá Text-to-Cypher: baseline sinh Cypher -> chạy trên Neo4j (chỉ đọc, timeout 30 s) -> chấm -> gán nhãn.

Chạy:  python eval/run_eval.py --baseline oracle --split dev
       python eval/run_eval.py --baseline b1_zeroshot --model openai/gpt-oss-20b --split test --run 1 [--answers]

Baseline là module eval/baselines/<tên>.py có hàm build(model) -> (câu hỏi -> 1 câu Cypher).
Cypher sinh ra được cache theo id câu hỏi ở results/cache/<baseline>__<model>__run<k>.json, ghi ngay sau mỗi câu:
chạy bị ngắt (hết hạn mức, mất mạng) thì chạy lại đúng lệnh cũ là làm tiếp. Lỗi LLM không được cache.
Kết quả: results/runs/<split>/<baseline>__<model>__run<k>.json, chỉ ghi khi lượt chạy đi hết bộ câu hỏi.

Nhãn: correct | wrong_result | empty_result | execution_error | timeout | no_cypher | llm_error
"""
import argparse
import importlib
import json
import platform
import time
from collections import Counter
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from itertools import zip_longest
from pathlib import Path

from neo4j import READ_ACCESS, GraphDatabase, Query
from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired
from neo4j.graph import Node, Relationship
from neo4j.graph import Path as GraphPath

from llm import DailyLimitError, groq_chat
from pilot_text2cypher import AUTH, URI, answer_rows, judge
from split_dev_test import TYPES, canonical_hash

ROOT = Path(__file__).resolve().parent.parent
QDIR = ROOT / "eval" / "questions"
CACHE_DIR = ROOT / "results" / "cache"
RUNS_DIR = ROOT / "results" / "runs"
VERDICTS = ["correct", "wrong_result", "empty_result", "execution_error", "timeout", "no_cypher", "llm_error"]
TIMEOUT_S = 30
MAX_ROWS = 1000           # gold có ≤ 20 dòng: đọc tối đa 1000 dòng kết quả dự đoán không làm đổi kết quả chấm
PREVIEW_ROWS = 5
MAX_LLM_ERRORS_IN_A_ROW = 5   # lỗi liên tiếp = sai key, mất mạng...: dừng thay vì gán llm_error cho cả bộ câu
ANSWER_MODEL = "openai/gpt-oss-20b"   # cùng model với B1 (Groq đã gỡ llama-3.1-8b-instant từ 16/08/2026)
ANSWER_MAX_ROWS = 20
ANSWER_PROMPT = """Answer the question in one or two sentences using only these query results.

Question: {question}
Query results:
{rows}
Answer:"""
PACKAGES = ["neo4j", "groq", "python-dotenv", "langchain-neo4j", "langchain-groq"]


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def file_name(baseline, model, run):
    return f"{baseline}__{(model or 'none').replace('/', '-').replace(':', '-')}__run{run}.json"


def plain(v):
    """Giá trị Neo4j -> giá trị ghi được ra JSON (node/quan hệ -> nhãn + thuộc tính, ngày giờ -> chuỗi)."""
    if v is None or isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, str):
        return v if len(v) <= 300 else v[:300] + "…"
    if isinstance(v, (list, tuple)):
        return [plain(x) for x in v]
    if isinstance(v, dict):
        return {k: plain(x) for k, x in v.items()}
    if isinstance(v, Node):
        return {"_labels": sorted(v.labels)} | {k: plain(x) for k, x in v.items()}
    if isinstance(v, Relationship):
        return {"_type": v.type} | {k: plain(x) for k, x in v.items()}
    if isinstance(v, GraphPath):
        return {"_path_length": len(v), "_nodes": [plain(n) for n in v.nodes]}
    return str(v)


def first_line(text):
    lines = (text or "").strip().splitlines()
    return lines[0][:300] if lines else ""


def run_query(session, cypher):
    """Chạy trong session READ với timeout; đọc tối đa MAX_ROWS + 1 dòng rồi bỏ phần còn lại."""
    result = session.run(Query(cypher, timeout=TIMEOUT_S))
    records = result.fetch(MAX_ROWS + 1)
    result.consume()
    return records


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def evaluate(session, q, entry):
    """Chạy Cypher (đã có trong cache) của một câu, chấm và gán nhãn. Trả về (kết quả, các dòng dự đoán | None)."""
    r = {"id": q["id"], "type": q["type"], "template_id": q["template_id"], "question": q["question"],
         "cypher": entry["cypher"], "gold": q["gold"], "seconds": entry["seconds"]}
    if "info" in entry:
        r["info"] = entry["info"]
    gold_rows = answer_rows(run_query(session, q["gold"]))
    r["gold_answer"] = plain(gold_rows)
    if not entry["cypher"]:
        r["verdict"] = "no_cypher"
        return r, None
    start, pred = time.time(), None
    try:
        pred = run_query(session, entry["cypher"])
        r["verdict"] = judge(gold_rows, pred)
        r["pred_rows"] = len(pred) if len(pred) <= MAX_ROWS else f">{MAX_ROWS}"
        r["pred_preview"] = [plain(list(rec.values())) for rec in pred[:PREVIEW_ROWS]]
    except (ServiceUnavailable, SessionExpired):
        raise  # Neo4j không chạy: dừng hẳn, không gán nhãn sai cho câu hỏi
    except Neo4jError as e:
        r["verdict"] = "timeout" if "TransactionTimedOut" in (e.code or "") else "execution_error"
        r["error"] = f"{e.code}: {first_line(e.message)}"
    except Exception as e:
        r["verdict"] = "execution_error"
        r["error"] = f"{type(e).__name__}: {first_line(str(e))}"
    r["exec_seconds"] = round(time.time() - start, 2)
    return r, pred


def make_answer(question, records):
    rows = "\n".join(json.dumps({k: plain(v) for k, v in rec.items()}, ensure_ascii=False)
                     for rec in records[:ANSWER_MAX_ROWS])
    return groq_chat(ANSWER_MODEL, ANSWER_PROMPT.format(question=question, rows=rows)).strip()


def package_versions():
    out = {"python": platform.python_version()}
    for p in PACKAGES:
        try:
            out[p] = version(p)
        except PackageNotFoundError:
            pass
    return out


def main():
    ap = argparse.ArgumentParser(description="Chạy một baseline trên dev/test và chấm execution accuracy.")
    ap.add_argument("--baseline", required=True, help="tên module trong eval/baselines/, vd. oracle, b1_zeroshot")
    ap.add_argument("--model", default=None, help="ID model trên Groq, vd. openai/gpt-oss-20b (oracle: bỏ trống)")
    ap.add_argument("--split", required=True, choices=["dev", "test"])
    ap.add_argument("--run", type=int, default=1, help="lần chạy thứ k (mỗi lần có cache riêng)")
    ap.add_argument("--answers", action="store_true",
                    help=f"sinh câu trả lời văn bản cho các câu correct bằng {ANSWER_MODEL} (chỉ dùng cho B1 test run 1)")
    ap.add_argument("--limit", type=int, default=None, help="chỉ chạy N câu đầu để thử; không ghi file kết quả")
    ap.add_argument("--interleave", action="store_true",
                    help="xếp câu xen kẽ theo loại, để phần đã chạy khi bị dừng giữa chừng vẫn đủ các loại")
    ap.add_argument("--cached-only", action="store_true",
                    help="chỉ chấm các câu đã có Cypher trong cache, không gọi LLM; ghi <tên>.partial.json")
    args = ap.parse_args()

    all_questions = json.loads((QDIR / f"{args.split}.json").read_text(encoding="utf-8"))
    questions = all_questions
    if args.interleave:
        groups = [[q for q in questions if q["type"] == t] for t in TYPES]
        questions = [q for row in zip_longest(*groups) for q in row if q]
    questions = questions[:args.limit] if args.limit else questions
    name = file_name(args.baseline, args.model, args.run)
    cache_path = CACHE_DIR / name
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    started = now()
    generate = importlib.import_module(f"baselines.{args.baseline}").build(args.model)

    results, stopped, errors_in_a_row = [], None, 0
    driver = GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF")
    with driver, driver.session(default_access_mode=READ_ACCESS) as session:
        neo4j_version = session.run("CALL dbms.components() YIELD versions, edition "
                                    "RETURN versions[0] + ' ' + edition AS v").single()["v"]
        for q in questions:
            entry = cache.get(q["id"])
            if entry is None and args.cached_only:
                continue
            if entry is None:
                start = time.time()
                try:
                    cypher = (generate(q["question"]) or "").strip()
                    errors_in_a_row = 0
                except DailyLimitError as e:
                    stopped = f"hết hạn mức theo ngày của Groq ({str(e)[:200]})"
                    break
                except Exception as e:
                    errors_in_a_row += 1
                    r = {"id": q["id"], "type": q["type"], "template_id": q["template_id"],
                         "question": q["question"], "cypher": "", "gold": q["gold"], "verdict": "llm_error",
                         "seconds": round(time.time() - start, 1), "error": f"{type(e).__name__}: {str(e)[:300]}"}
                    results.append(r)
                    print(f"{q['id']:<10} {q['type']:<12} llm_error        {r['error'][:100]}")
                    if errors_in_a_row >= MAX_LLM_ERRORS_IN_A_ROW:
                        stopped = f"{errors_in_a_row} lần gọi LLM lỗi liên tiếp"
                        break
                    continue
                entry = cache[q["id"]] = {"cypher": cypher, "seconds": round(time.time() - start, 1), "at": now()}
                if getattr(generate, "last_info", None):  # thông tin phụ của baseline, vd số lần gọi LLM khi tự sửa lỗi
                    entry["info"] = generate.last_info
                save_json(cache_path, cache)

            r, pred = evaluate(session, q, entry)
            if args.answers and r["verdict"] == "correct":  # chỉ cần câu đúng làm ví dụ demo, đỡ tốn hạn mức
                if "answer" not in entry:
                    try:
                        entry["answer"] = make_answer(q["question"], pred)
                        save_json(cache_path, cache)
                    except DailyLimitError as e:
                        stopped = f"hết hạn mức theo ngày của Groq khi sinh câu trả lời ({str(e)[:200]})"
                        break
                    except Exception as e:
                        r["answer_error"] = f"{type(e).__name__}: {str(e)[:300]}"
                if "answer" in entry:
                    r["answer"] = entry["answer"]
            results.append(r)
            exec_s = f"  chạy {r['exec_seconds']}s" if "exec_seconds" in r else ""
            print(f"{q['id']:<10} {q['type']:<12} {r['verdict']:<16} sinh {r['seconds']}s{exec_s}")

    if stopped:
        missing = sum(q["id"] not in cache for q in questions)
        print(f"\nDỪNG: {stopped}.\nCòn {missing}/{len(questions)} câu chưa có Cypher "
              f"(cache: {cache_path.relative_to(ROOT)}). Chạy lại đúng lệnh này để làm tiếp. Chưa ghi file kết quả.")
        raise SystemExit(2)

    counts = Counter(r["verdict"] for r in results)
    print(f"\n{'Loại':<12} Đúng")
    for t in TYPES + ["Tổng"]:
        rs = [r for r in results if t == "Tổng" or r["type"] == t]
        if rs:
            print(f"{t:<12} {sum(r['verdict'] == 'correct' for r in rs)}/{len(rs)}")
    print("Nhãn: " + ", ".join(f"{v}={counts[v]}" for v in VERDICTS if counts[v]))
    if counts["llm_error"]:
        print(f"Có {counts['llm_error']} câu llm_error (không cache): chạy lại lệnh này để thử lại các câu đó.")
    if args.limit:
        print("Chạy thử với --limit: không ghi file kết quả.")
        return

    llm_times = [cache[q["id"]]["at"] for q in questions if "at" in cache.get(q["id"], {})]
    meta = {"baseline": args.baseline, "model": args.model or "none", "split": args.split, "run": args.run,
            "started_at": started, "finished_at": now(),
            "llm_first_call_at": min(llm_times, default=None), "llm_last_call_at": max(llm_times, default=None),
            "temperature": 0, "timeout_s": TIMEOUT_S, "max_rows_read": MAX_ROWS,
            "questions_file": f"eval/questions/{args.split}.json", "questions_sha256": canonical_hash(all_questions),
            "n_questions": len(results), "verdicts": {v: counts[v] for v in VERDICTS},
            "partial": args.cached_only, "neo4j": neo4j_version, "packages": package_versions(), "prompt": None,
            "answers": {"model": ANSWER_MODEL, "prompt": ANSWER_PROMPT, "max_rows": ANSWER_MAX_ROWS}
            if args.answers else None}
    meta |= getattr(generate, "meta", {})
    out_path = RUNS_DIR / args.split / (name.replace(".json", ".partial.json") if args.cached_only else name)
    save_json(out_path, {"meta": meta, "results": results})
    print(f"\nĐã lưu {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
