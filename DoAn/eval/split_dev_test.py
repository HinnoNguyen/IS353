"""Chia bộ câu hỏi thành dev/test theo eval/QA_GUIDELINE.md mục 7.

- Chia theo template: mọi câu của một template nằm cùng một phía; mỗi loại có template ở cả hai phía.
- Thực thể không trùng: thực thể (người, quốc gia, thành phố, tag) đã có trong test thì câu dev chứa nó bị bỏ
  (giữ nguyên test, hy sinh dev).
- Mã băm SHA-256 của test tính trên nội dung JSON chuẩn hóa (không phụ thuộc CRLF/LF giữa các máy).

Chạy:  python eval/split_dev_test.py
Kết quả: eval/questions/dev.json, eval/questions/test.json, eval/questions/split_info.json
"""
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QDIR = ROOT / "eval" / "questions"
TYPES = ["lookup", "aggregation", "multi_hop", "path", "temporal"]
SEED = 353
DEV_TEMPLATES_PER_TYPE = 2   # 5 template/loại -> 2 dev, 3 test


def entities(q):
    """Thực thể làm tham số của câu hỏi: người (họ tên đầy đủ) và các tham số tên khác."""
    p, out = q["params"], set()
    for s in ("", "1", "2"):
        if "firstName" + s in p:
            out.add(("person", p["firstName" + s], p["lastName" + s]))
    for k in ("country", "city", "tag"):
        if k in p:
            out.add((k, p[k]))
    return out


def canonical_hash(questions):
    data = json.dumps(questions, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def main():
    rng = random.Random(SEED)
    dev, test, dev_tpl, test_tpl = [], [], {}, {}
    for t in TYPES:
        qs = json.loads((QDIR / f"{t}.json").read_text(encoding="utf-8"))
        tids = sorted({q["template_id"] for q in qs})
        rng.shuffle(tids)
        dev_tpl[t], test_tpl[t] = sorted(tids[:DEV_TEMPLATES_PER_TYPE]), sorted(tids[DEV_TEMPLATES_PER_TYPE:])
        dev += [q for q in qs if q["template_id"] in dev_tpl[t]]
        test += [q for q in qs if q["template_id"] in test_tpl[t]]

    # checked_by lấy từ kết quả kiểm tra chéo (eval/cross_check/<người>_result.json), nếu đã có
    checked = {}
    for f in sorted((QDIR.parent / "cross_check").glob("*_result.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            if r["verdict"] in ("khớp", "không khớp", "lỗi"):
                checked[r["id"]] = f.stem.removesuffix("_result")
    for q in dev + test:
        q["checked_by"] = checked.get(q["id"], q["checked_by"])

    test_entities = set().union(*(entities(q) for q in test))
    dropped = [q["id"] for q in dev if entities(q) & test_entities]
    dev = [q for q in dev if q["id"] not in dropped]

    for name, qs in (("dev", dev), ("test", test)):
        (QDIR / f"{name}.json").write_text(json.dumps(qs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    count = lambda qs: {t: sum(q["type"] == t for q in qs) for t in TYPES} | {"total": len(qs)}
    info = {
        "seed": SEED,
        "dev_templates": dev_tpl,
        "test_templates": test_tpl,
        "dev_count": count(dev),
        "test_count": count(test),
        "dev_dropped_shared_entity": dropped,
        "test_sha256": canonical_hash(test),
        "hash_note": "sha256 của json.dumps(test, ensure_ascii=False, sort_keys=True, separators=(',', ':'))",
    }
    (QDIR / "split_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"dev : {info['dev_count']}")
    print(f"test: {info['test_count']}")
    print(f"bỏ {len(dropped)} câu dev trùng thực thể với test: {dropped}")
    print(f"test sha256: {info['test_sha256']}")


if __name__ == "__main__":
    main()
