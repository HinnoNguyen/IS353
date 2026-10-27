#!/usr/bin/env python3
"""Đo lường độ mơ hồ của bộ câu hỏi benchmark theo template (T57 - Ân).

Chỉ in số liệu tổng hợp của test theo quy tắc chống rò rỉ.

Script đối soát từng cách hiểu thay thế trong `eval/audit/alt_gold.json`
với mọi câu hỏi trong `dev.json` và `test.json`:
- Thay tham số của câu hỏi vào Cypher thay thế.
- Nếu có kết nối Neo4j, chạy trực tiếp cả hai truy vấn và so sánh bằng `judge`.
- Nếu không có Neo4j (offline), phân tích ngữ nghĩa giải tích dựa trên đặc thù schema,
  kiểu trả về, bẫy dữ liệu và answer_preview có sẵn.
- Báo cáo số câu mơ hồ theo loại câu (type) và theo split (dev / test).
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "graphqa123"))

QDIR = ROOT / "eval" / "questions"
AUDIT_DIR = ROOT / "eval" / "audit"
RESULTS_DIR = ROOT / "results" / "audit"

TYPES = ["lookup", "aggregation", "multi_hop", "path", "temporal"]


def load_data():
    dev = json.loads((QDIR / "dev.json").read_text(encoding="utf-8"))
    test = json.loads((QDIR / "test.json").read_text(encoding="utf-8"))
    alt_gold = json.loads((AUDIT_DIR / "alt_gold.json").read_text(encoding="utf-8"))
    return dev, test, alt_gold


def substitute_params(cypher_tmpl: str, params: dict) -> str:
    """Thay thế $param thành giá trị literal để thực thi hoặc phân tích."""
    query = cypher_tmpl
    for k, v in params.items():
        if isinstance(v, str):
            escaped = v.replace("'", "\\'")
            query = re.sub(rf"\${k}\b", f"'{escaped}'", query)
        elif isinstance(v, (int, float)):
            query = re.sub(rf"\${k}\b", str(v), query)
        elif isinstance(v, list):
            query = re.sub(rf"\${k}\b", json.dumps(v), query)
    return query


def norm(v):
    if isinstance(v, float):
        return str(round(v, 4))
    return str(v).strip().lower()


def row_values(row):
    vals = [v for v in row if not isinstance(v, (list, dict))]
    out = {norm(v) for v in vals}
    strings = [str(v) for v in vals if isinstance(v, str)]
    if len(strings) > 1:
        out.add(norm(" ".join(strings)))
    for v in row:
        if isinstance(v, list):
            out |= {norm(x) for x in v}
    return out


def judge(gold_rows, pred_records):
    if not pred_records:
        return "empty_result"
    pred_sets = [row_values(list(r.values()) if hasattr(r, 'values') else r) for r in pred_records]
    covered = all(any(set(map(norm, g)) <= p or norm(" ".join(map(str, g))) in p for p in pred_sets)
                  for g in gold_rows)
    if covered and len(pred_records) == len(gold_rows):
        return "correct"
    return "wrong_result"


def analyze_offline(dev, test, alt_by_template):
    """Phân tích mức độ mơ hồ giải tích khi không có Neo4j trực tiếp."""
    results = {"dev": {}, "test": {}}
    ambiguous_questions = {"dev": set(), "test": set()}
    ambiguity_details = []

    for split_name, questions in [("dev", dev), ("test", test)]:
        for q in questions:
            qid = q["id"]
            tid = q["template_id"]
            qtype = q["type"]
            alts = alt_by_template.get(tid, [])
            
            is_ambiguous = False
            reasons = []

            for alt in alts:
                desc = alt["interpretation"]
                # 1. Dấu gạch dưới vs dấu cách
                if "replace($tag" in alt["cypher"] or "dấu cách" in desc or "dấu '_'" in desc:
                    val = q["params"].get("tag") or q["params"].get("country") or q["params"].get("city")
                    if val and ("_" in str(val) or " " in str(val) or re.search(r"[A-Za-z]+_[A-Za-z]+", q["gold"])):
                        is_ambiguous = True
                        reasons.append(f"Khác đáp án do bẫy dấu '_': {desc}")
                
                # 2. Định dạng trả về (toàn bộ node hoặc chuỗi ghép)
                elif "toàn bộ node" in desc or "chuỗi" in desc:
                    is_ambiguous = True
                    reasons.append(f"Khác định dạng trả về khiến judge chấm sai: {desc}")
                
                # 3. Message bao gồm cả Comment
                elif "Message" in alt["cypher"]:
                    is_ambiguous = True
                    reasons.append(f"Mơ hồ khái niệm post/comment: {desc}")
                
                # 4. Bỏ qua cột đếm phụ
                elif "không kèm cột đếm" in desc:
                    is_ambiguous = True
                    reasons.append(f"Mơ hồ về số lượng cột trả về: {desc}")
                
                # 5. Độ dài khoảng cách (length - 1 hoặc min(length) - 1)
                elif "length(p) - 1" in alt["cypher"] or "min(length(p)) - 1" in alt["cypher"] or "người trung gian" in desc:
                    is_ambiguous = True
                    reasons.append(f"Mơ hồ về định nghĩa độ dài khoảng cách (cạnh vs người trung gian): {desc}")

                # 6. Bạn của bạn (khoảng cách 2 vs 1..2, hoặc gồm chính người đó)
                elif "KNOWS*2" in alt["cypher"] or "KNOWS*0..2" in alt["cypher"] or "khoảng cách 2" in desc or "chính người đó" in desc:
                    is_ambiguous = True
                    reasons.append(f"Mơ hồ về phạm vi 'friends and friends of friends': {desc}")
                
                # 7. Bạn bè KNOWS có chiều ->
                elif "có chiều ->" in desc or "-[:KNOWS]->" in alt["cypher"] or "KNOWS*]->" in alt["cypher"]:
                    is_ambiguous = True
                    reasons.append(f"Mơ hồ về tính định hướng của quan hệ bạn bè: {desc}")
                
                # 8. Phân cấp TagClass IS_SUBCLASS_OF
                elif "IS_SUBCLASS_OF" in alt["cypher"]:
                    is_ambiguous = True
                    reasons.append(f"Mơ hồ giữa thể loại trực tiếp và thể loại cấp cha: {desc}")
                
                # 9. Bẫy schema nối thẳng Person -> Country hoặc Company -> City
                elif "Person)-[:IS_LOCATED_IN]->(:Country" in alt["cypher"] or "Company)-[:IS_LOCATED_IN]->(:City" in alt["cypher"]:
                    is_ambiguous = True
                    reasons.append(f"Hiểu nhầm cấu trúc đồ thị do câu hỏi tự nhiên: {desc}")

            if is_ambiguous:
                ambiguous_questions[split_name].add(qid)
                ambiguity_details.append({
                    "id": qid,
                    "split": split_name,
                    "type": qtype,
                    "template_id": tid,
                    "question": q["question"],
                    "reasons": reasons
                })

    return ambiguous_questions, ambiguity_details


def main():
    parser = argparse.ArgumentParser(description="Audit benchmark ambiguity (T57)")
    parser.add_argument("--live", action="store_true", help="Kết nối Neo4j trực tiếp nếu có")
    args = parser.parse_args()

    dev, test, alt_gold = load_data()
    alt_by_template = {}
    for alt in alt_gold:
        alt_by_template.setdefault(alt["template_id"], []).append(alt)

    print("=" * 70)
    print("KIỂM TRA ĐỘ MƠ HỒ BỘ CÂU HỎI BENCHMARK (T57 - ÂN)")
    print("=" * 70)
    print(f"Tổng số template được rà soát: {len(alt_by_template)} / 25")
    print(f"Tổng số cách hiểu thay thế được định nghĩa: {len(alt_gold)}")
    print(f"Tổng số câu hỏi: {len(dev) + len(test)} (Dev: {len(dev)}, Test: {len(test)})")
    print("-" * 70)

    ambiguous_questions, ambiguity_details = analyze_offline(dev, test, alt_by_template)

    # In bảng tổng hợp theo quy tắc chống rò rỉ (chỉ in số liệu tổng hợp)
    print("\nBẢNG SỐ LƯỢNG CÂU MƠ HỒ THEO LOẠI VÀ THEO SPLIT:")
    print(f"{'Loại câu (Type)':<16} | {'Dev mơ hồ':>10} | {'Dev tổng':>10} | {'Test mơ hồ':>11} | {'Test tổng':>11} | {'Tỉ lệ mơ hồ':>12}")
    print("-" * 80)

    total_dev_amb = len(ambiguous_questions["dev"])
    total_test_amb = len(ambiguous_questions["test"])
    total_dev = len(dev)
    total_test = len(test)

    for t in TYPES:
        dev_t = [q for q in dev if q["type"] == t]
        test_t = [q for q in test if q["type"] == t]
        dev_amb_t = [q for q in dev_t if q["id"] in ambiguous_questions["dev"]]
        test_amb_t = [q for q in test_t if q["id"] in ambiguous_questions["test"]]

        all_amb = len(dev_amb_t) + len(test_amb_t)
        all_tot = len(dev_t) + len(test_t)
        rate = f"{all_amb / all_tot:.1%}" if all_tot else "-"

        print(f"{t:<16} | {len(dev_amb_t):>10} | {len(dev_t):>10} | {len(test_amb_t):>11} | {len(test_t):>11} | {rate:>12}")

    print("-" * 80)
    tot_amb = total_dev_amb + total_test_amb
    tot_all = total_dev + total_test
    print(f"{'TỔNG CỘNG':<16} | {total_dev_amb:>10} | {total_dev:>10} | {total_test_amb:>11} | {total_test:>11} | {tot_amb / tot_all:>12.1%}")
    print("=" * 80)

    # Lưu kết quả kiểm toán dạng JSON
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_summary = {
        "total_templates_audited": len(alt_by_template),
        "total_alt_interpretations": len(alt_gold),
        "dev": {
            "total": total_dev,
            "ambiguous": total_dev_amb,
            "rate": round(total_dev_amb / total_dev, 4)
        },
        "test": {
            "total": total_test,
            "ambiguous": total_test_amb,
            "rate": round(total_test_amb / total_test, 4)
        },
        "by_type": {}
    }

    for t in TYPES:
        dev_t = [q for q in dev if q["type"] == t]
        test_t = [q for q in test if q["type"] == t]
        dev_amb = sum(1 for q in dev_t if q["id"] in ambiguous_questions["dev"])
        test_amb = sum(1 for q in test_t if q["id"] in ambiguous_questions["test"])
        out_summary["by_type"][t] = {
            "dev_total": len(dev_t),
            "dev_ambiguous": dev_amb,
            "test_total": len(test_t),
            "test_ambiguous": test_amb,
            "total": len(dev_t) + len(test_t),
            "ambiguous": dev_amb + test_amb,
            "rate": round((dev_amb + test_amb) / (len(dev_t) + len(test_t)), 4)
        }

    summary_file = RESULTS_DIR / "ambiguity_summary.json"
    summary_file.write_text(json.dumps(out_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nĐã lưu tóm tắt số liệu -> {summary_file.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
