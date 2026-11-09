"""Chỉ in số liệu tổng hợp của test. – T56 bước 5: các đường rò rỉ khác (kiểm tra nhanh).

Chạy:  python eval/audit/leak_misc.py

1. Dev/test gần trùng: che tên riêng (mọi giá trị params, cả dạng '_' và dấu cách, và số) rồi tính Jaccard trên tập từ
   giữa mỗi câu test và mọi câu dev. In số câu test có Jaccard lớn nhất >= 0,8 (và phân bố), không in câu.
2. Đường đi của gold: quét mã nguồn eval/baselines/*.py (và module đề xuất nếu có) tìm truy cập trường
   gold / gold_answer / answer_preview. Chỉ oracle được phép.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QDIR = ROOT / "eval" / "questions"
THRESHOLD = 0.8
GOLD_RE = re.compile(r"""["'](gold|gold_answer|answer_preview)["']|\.gold\b|\bgold_rows\b""")
ALLOWED = {"oracle.py"}


def masked_tokens(q):
    text = q["question"].lower()
    vals = []
    for v in q.get("params", {}).values():
        s = str(v).lower()
        vals += [s, s.replace("_", " ")]
    for s in sorted(set(vals), key=len, reverse=True):
        text = text.replace(s, " zzent ")
    text = re.sub(r"\d+", " zznum ", text)
    return set(re.findall(r"[a-z]+", text))


def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 0.0


def near_duplicates():
    dev = json.loads((QDIR / "dev.json").read_text(encoding="utf-8"))
    test = json.loads((QDIR / "test.json").read_text(encoding="utf-8"))
    dev_toks = [masked_tokens(q) for q in dev]
    best = []
    tpl_pairs = Counter()
    for q in test:
        t = masked_tokens(q)
        scores = [(jaccard(t, d), dq["template_id"]) for d, dq in zip(dev_toks, dev)]
        s, dtpl = max(scores)
        best.append(s)
        if s >= THRESHOLD:
            tpl_pairs[(q["template_id"], dtpl)] += 1
    bins = Counter(min(int(s * 10), 9) / 10 for s in best)
    n_dup = sum(s >= THRESHOLD for s in best)
    print(f"1. Gần trùng dev/test (Jaccard trên từ, đã che tên riêng; ngưỡng {THRESHOLD}):")
    print(f"   {n_dup}/{len(test)} câu test có câu dev gần trùng")
    print("   Phân bố Jaccard lớn nhất của mỗi câu test: "
          + ", ".join(f"[{b:.1f},{b + 0.1:.1f}): {bins[b]}" for b in sorted(bins)))
    if tpl_pairs:
        print("   Cặp (template test, template dev) gần trùng: " + str(dict(tpl_pairs)))
    return {"threshold": THRESHOLD, "n_test": len(test), "n_near_dup": n_dup,
            "max_jaccard_hist": {f"{b:.1f}": bins[b] for b in sorted(bins)},
            "template_pairs": {f"{a}~{b}": c for (a, b), c in tpl_pairs.items()}}


def gold_access():
    print("\n2. Truy cập trường gold trong mã baseline / module đề xuất:")
    files = sorted((ROOT / "eval" / "baselines").glob("*.py"))
    files += [p for p in (ROOT / "eval").glob("module_*.py")]
    out = {}
    for f in files:
        hits = [i + 1 for i, line in enumerate(f.read_text(encoding="utf-8").splitlines()) if GOLD_RE.search(line)]
        status = "được phép" if f.name in ALLOWED else ("VI PHẠM" if hits else "sạch")
        print(f"   {f.relative_to(ROOT)}: {len(hits)} dòng {hits} -> {status}")
        out[str(f.relative_to(ROOT))] = {"lines": hits, "status": status}
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    report = {"near_duplicates": near_duplicates(), "gold_access": gold_access()}
    out = ROOT / "results" / "audit" / "leak_misc.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nĐã lưu {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
