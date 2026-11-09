"""Chỉ in số liệu tổng hợp của test. – T55 bước 1: Phân tích độ phức tạp của Cypher gold.

Chạy:  python eval/audit/complexity.py [--no-neo4j] [--out results/audit/complexity.json]

Phân tích Cypher gold của dev (92 câu) và test (150 câu):
  - Số bước quan hệ (hops)
  - Đường đi độ dài thay đổi (*1..2, *) hoặc shortestPath
  - Hàm gộp (count, avg, sum, min, max...), ORDER BY ... LIMIT, WITH
  - Số điều kiện WHERE (đếm AND / OR)
  - Số dòng của đáp án (chạy gold trên Neo4j)

Thang độ phức tạp (định nghĩa trước):
  - Dễ (Easy): 1 hop (hoặc 0), không gộp, không shortestPath/*, không WITH, <= 1 điều kiện WHERE.
  - Trung bình (Medium): 2 hops, HOẶC 1 hop có gộp / ORDER BY LIMIT / lọc thời gian.
  - Khó (Hard): >= 3 hops, HOẶC có shortestPath / *, HOẶC có WITH, HOẶC (>= 2 hops VÀ có gộp VÀ >= 2 điều kiện WHERE).

Quy tắc chống rò rỉ: Với test, script KHÔNG in câu hỏi hay Cypher gold cụ thể; chỉ in số liệu tổng hợp theo split x loại câu và theo template.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))

QDIR = ROOT / "eval" / "questions"
TYPES = ["lookup", "aggregation", "multi_hop", "path", "temporal"]

# Regex nhận diện các thành phần Cypher
REL_PATTERN = re.compile(r"-\[.*?\]-")
VAR_HOP_PATTERN = re.compile(r"-\[.*?\*\d*(\.\.\d+)?.*\]-")
SHORTEST_PATH_PATTERN = re.compile(r"\bshortestPath\b", re.IGNORECASE)
AGG_FUNC_PATTERN = re.compile(r"\b(count|avg|sum|min|max|collect)\s*\(", re.IGNORECASE)
ORDER_LIMIT_PATTERN = re.compile(r"\bORDER\s+BY\b.*?\bLIMIT\b", re.IGNORECASE | re.DOTALL)
WITH_PATTERN = re.compile(r"\bWITH\b", re.IGNORECASE)
WHERE_PATTERN = re.compile(r"\bWHERE\b(.*?)(?=\b(?:RETURN|WITH|ORDER|MATCH|LIMIT)\b|$)", re.IGNORECASE | re.DOTALL)


def count_hops(cypher):
    """Đếm số bước quan hệ trong Cypher."""
    # Tìm các match pattern dạng -[...]-, -[...]->, <-[...]-
    matches = re.findall(r"-\[[^\]]*\]-?|<-?\[[^\]]*\]-", cypher)
    return len(matches)


def has_var_hops_or_shortest_path(cypher):
    """Kiểm tra có shortestPath hoặc quan hệ biến thiên * không."""
    has_sp = bool(SHORTEST_PATH_PATTERN.search(cypher))
    has_var = bool(re.search(r"-\[[^\]]*\*[^\]]*\]-?|<-?\[[^\]]*\*[^\]]*\]-", cypher))
    return has_sp or has_var


def count_where_conditions(cypher):
    """Đếm số điều kiện trong WHERE."""
    m = WHERE_PATTERN.search(cypher)
    if not m:
        return 0
    clause = m.group(1).strip()
    # Tách theo AND / OR
    conds = re.split(r"\b(?:AND|OR)\b", clause, flags=re.IGNORECASE)
    return len([c for c in conds if c.strip()])


def analyze_cypher(cypher):
    """Phân tích các chỉ số kỹ thuật của câu Cypher."""
    hops = count_hops(cypher)
    var_path = has_var_hops_or_shortest_path(cypher)
    has_agg = bool(AGG_FUNC_PATTERN.search(cypher))
    has_order_limit = bool(ORDER_LIMIT_PATTERN.search(cypher))
    has_with = bool(WITH_PATTERN.search(cypher))
    where_conds = count_where_conditions(cypher)

    # Đánh giá độ khó (Tier)
    # Quy tắc:
    # - Hard: có shortestPath/* HOẶC >= 3 hops HOẶC has_with HOẶC (hops >= 2 và has_agg và where_conds >= 2)
    # - Medium: hops == 2 HOẶC (hops <= 1 và (has_agg hoặc has_order_limit hoặc where_conds >= 1))
    # - Easy: còn lại (hops <= 1, không gộp, không order/limit, where_conds <= 1)
    if var_path or hops >= 3 or has_with or (hops >= 2 and has_agg and where_conds >= 2):
        tier = "Khó"
    elif hops == 2 or has_agg or has_order_limit or where_conds >= 1:
        tier = "Trung bình"
    else:
        tier = "Dễ"

    return {
        "hops": hops,
        "var_path": var_path,
        "has_agg": has_agg,
        "has_order_limit": has_order_limit,
        "has_with": has_with,
        "where_conds": where_conds,
        "tier": tier
    }


def get_answer_rows(driver, cypher):
    """Lấy số dòng đáp án từ Neo4j."""
    if not driver:
        return None
    try:
        records, _, _ = driver.execute_query(cypher, routing_="r")
        return len(records)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-neo4j", action="store_true", help="Không kết nối Neo4j để đếm số dòng đáp án")
    ap.add_argument("--out", default=str(ROOT / "results" / "audit" / "complexity.json"))
    args = ap.parse_args()

    driver = None
    if not args.no_neo4j:
        try:
            from neo4j import GraphDatabase
            from pilot_text2cypher import AUTH, URI
            driver = GraphDatabase.driver(URI, auth=AUTH)
            driver.verify_connectivity()
        except Exception as e:
            print(f"Cảnh báo: Không kết nối được Neo4j ({e}). Tiếp tục với --no-neo4j.")
            driver = None

    summary_data = {}

    print("=" * 80)
    print("BÁO CÁO PHÂN TÍCH ĐỘ PHỨC TẠP CYPHER GOLD (T55 - VŨ)")
    print("Thang đánh giá: Dễ (Easy), Trung bình (Medium), Khó (Hard)")
    print("=" * 80)

    for split in ["dev", "test"]:
        path = QDIR / f"{split}.json"
        if not path.exists():
            print(f"Không tìm thấy file: {path}")
            continue

        questions = json.loads(path.read_text(encoding="utf-8"))
        by_type = defaultdict(list)
        for q in questions:
            analysis = analyze_cypher(q["gold"])
            if driver:
                analysis["answer_rows"] = get_answer_rows(driver, q["gold"])
            analysis["template_id"] = q["template_id"]
            analysis["id"] = q["id"]
            by_type[q["type"]].append(analysis)

        split_summary = {}

        print(f"\n--- TẬP {split.upper()} ({len(questions)} câu) ---")
        print(f"{'Loại câu':<14} | {'Số câu':<6} | {'Hop TB':<7} | {'Biến thiên/SP':<13} | {'Gộp (%)':<9} | {'WHERE >= 1':<10} | {'Dễ':<5} | {'TB':<5} | {'Khó':<5}")
        print("-" * 88)

        total_hops = 0
        total_var = 0
        total_agg = 0
        total_where = 0
        tier_counts = Counter()

        for t in TYPES:
            items = by_type[t]
            n = len(items)
            if n == 0:
                continue
            avg_hops = sum(it["hops"] for it in items) / n
            var_cnt = sum(1 for it in items if it["var_path"])
            agg_cnt = sum(1 for it in items if it["has_agg"])
            where_cnt = sum(1 for it in items if it["where_conds"] >= 1)
            t_tiers = Counter(it["tier"] for it in items)

            total_hops += sum(it["hops"] for it in items)
            total_var += var_cnt
            total_agg += agg_cnt
            total_where += where_cnt
            tier_counts.update(t_tiers)

            print(f"{t:<14} | {n:<6} | {avg_hops:<7.2f} | {var_cnt:<13} | {agg_cnt*100/n:<8.1f}% | {where_cnt:<10} | {t_tiers['Dễ']:<5} | {t_tiers['Trung bình']:<5} | {t_tiers['Khó']:<5}")

            split_summary[t] = {
                "n": n,
                "avg_hops": round(avg_hops, 2),
                "var_path_count": var_cnt,
                "agg_pct": round(agg_cnt * 100 / n, 1),
                "where_ge_1": where_cnt,
                "tiers": dict(t_tiers)
            }

        n_all = len(questions)
        print("-" * 88)
        print(f"{'TỔNG':<14} | {n_all:<6} | {total_hops/n_all:<7.2f} | {total_var:<13} | {total_agg*100/n_all:<8.1f}% | {total_where:<10} | {tier_counts['Dễ']:<5} | {tier_counts['Trung bình']:<5} | {tier_counts['Khó']:<5}")
        print(f"Tỉ lệ mức độ khó: Dễ: {tier_counts['Dễ']*100/n_all:.1f}% | Trung bình: {tier_counts['Trung bình']*100/n_all:.1f}% | Khó: {tier_counts['Khó']*100/n_all:.1f}%")

        split_summary["TOTAL"] = {
            "n": n_all,
            "avg_hops": round(total_hops / n_all, 2),
            "var_path_count": total_var,
            "agg_pct": round(total_agg * 100 / n_all, 1),
            "where_ge_1": total_where,
            "tiers": dict(tier_counts),
            "tier_pct": {k: round(v * 100 / n_all, 1) for k, v in tier_counts.items()}
        }
        summary_data[split] = split_summary

    if driver:
        driver.close()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nĐã lưu kết quả phân tích tổng hợp vào: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    from collections import Counter
    main()

