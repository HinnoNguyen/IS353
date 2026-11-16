"""T33 – Module (C): Chọn k ví dụ few-shot động từ dev.json (Vũ).

Interface cho proposed.py (GIAO_VIEC_CUOI_KY.md mục 6.3 & PR #11):
    select(question, k=3) -> str
        Trả về khối văn bản chứa tối đa k ví dụ (Question / Cypher) để nối ngay sau schema,
        trước câu hỏi của người dùng. Trả về "" nếu k <= 0 hoặc không có ví dụ phù hợp.

    select_examples(question, k=3, exclude_template=None, strategy="bm25", diverse=True) -> list[dict]
        Hàm chi tiết trả về danh sách dict ví dụ kèm điểm BM25 (phục vụ kiểm thử & ablation).

Quy tắc chống rò rỉ dữ liệu:
1. Kho ví dụ CHỈ lấy từ eval/questions/dev.json (tuyệt đối không đọc tập kiểm thử hay eval/templates/).
2. Leave-template-out: khi câu hỏi thuộc dev.json, dev_zero.json hoặc dev_para.json (cùng dùng
   10 template dev), tự động loại bỏ toàn bộ ví dụ có cùng template_id để tránh model chép lại mẫu.
"""
import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

QDIR = Path(__file__).resolve().parents[1] / "questions"
DEV_FILE = QDIR / "dev.json"
DEV_SUBSET_FILES = ("dev.json", "dev_zero.json", "dev_para.json")   # không bao giờ đọc test/test2
DEFAULT_K = 3
BM25_K1 = 1.5
BM25_B = 0.75


def _norm_question(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", (text or "").lower())


def _compact_cypher(cypher: str) -> str:
    return re.sub(r"\s+", " ", (cypher or "").strip())


def estimate_tokens(text: str) -> int:
    word_pieces = len(re.findall(r"\w+|[^\w\s]", text or ""))
    return max(len(text or "") // 4, int(word_pieces * 0.85))


@lru_cache(maxsize=1)
def _load_bank():
    """Nạp kho ví dụ duy nhất từ dev.json và dựng chỉ mục BM25 + bảng leave-template-out."""
    examples = json.loads(DEV_FILE.read_text(encoding="utf-8"))
    docs = [_tokenize(q["question"]) for q in examples]
    n_docs = len(docs)
    avgdl = sum(len(d) for d in docs) / n_docs if n_docs else 1.0

    df: Counter[str] = Counter()
    for d in docs:
        for tok in set(d):
            df[tok] += 1
    idf = {
        tok: math.log((n_docs - freq + 0.5) / (freq + 0.5) + 1.0)
        for tok, freq in df.items()
    }
    doc_tfs = [Counter(d) for d in docs]

    # Map câu hỏi chuẩn hóa -> template_id chỉ từ các tập dev* có trước khi khóa pipeline
    q_to_tpl: dict[str, str] = {}
    for fname in DEV_SUBSET_FILES:
        path = QDIR / fname
        if not path.exists():
            continue
        for item in json.loads(path.read_text(encoding="utf-8")):
            tid = item.get("template_id")
            if tid:
                q_to_tpl[_norm_question(item.get("question", ""))] = tid

    # Chọn cố định 1 ví dụ đại diện cho mỗi loại câu hỏi (phục vụ baseline tĩnh trong ablation)
    fixed_examples: list[dict] = []
    seen_types: set[str] = set()
    for item in examples:
        qtype = item.get("type", "")
        if qtype not in seen_types:
            fixed_examples.append(item)
            seen_types.add(qtype)

    return examples, doc_tfs, docs, avgdl, idf, q_to_tpl, fixed_examples


def infer_dev_template(question: str) -> str | None:
    """Trả về template_id nếu câu hỏi trùng với một câu trong dev / dev_zero / dev_para."""
    _, _, _, _, _, q_to_tpl, _ = _load_bank()
    return q_to_tpl.get(_norm_question(question))


def _bm25_score(query_tokens: list[str], tf: Counter[str], dl: int, avgdl: float, idf: dict[str, float]) -> float:
    score = 0.0
    for tok in query_tokens:
        freq = tf.get(tok, 0)
        if freq:
            denom = freq + BM25_K1 * (1.0 - BM25_B + BM25_B * dl / avgdl)
            score += idf.get(tok, 0.0) * (freq * (BM25_K1 + 1.0)) / denom
    return score


def select_examples(
    question: str,
    k: int = DEFAULT_K,
    exclude_template: str | None = None,
    strategy: str = "bm25",
    diverse: bool = True,
) -> list[dict]:
    """Chọn tối đa k ví dụ từ dev.json, tự động leave-template-out nếu thuộc dev/dev_zero/dev_para."""
    if k <= 0:
        return []
    if strategy not in ("bm25", "fixed"):
        raise ValueError(f"strategy phải là 'bm25' hoặc 'fixed', nhận: {strategy!r}")

    examples, doc_tfs, docs, avgdl, idf, _, fixed_examples = _load_bank()
    q_norm = _norm_question(question)
    excl_tpl = exclude_template if exclude_template is not None else infer_dev_template(question)

    def allowed(ex: dict) -> bool:
        if _norm_question(ex["question"]) == q_norm:
            return False
        if excl_tpl and ex.get("template_id") == excl_tpl:
            return False
        return True

    if strategy == "fixed":
        candidates = [dict(ex, score=0.0) for ex in fixed_examples if allowed(ex)]
        if len(candidates) < k:
            seen_ids = {ex["id"] for ex in candidates}
            for ex in examples:
                if ex["id"] not in seen_ids and allowed(ex):
                    candidates.append(dict(ex, score=0.0))
                    seen_ids.add(ex["id"])
                    if len(candidates) >= k:
                        break
        return candidates[:k]

    q_tokens = _tokenize(question)
    scored: list[tuple[float, dict]] = []
    for idx, ex in enumerate(examples):
        if not allowed(ex):
            continue
        score = _bm25_score(q_tokens, doc_tfs[idx], len(docs[idx]), avgdl, idf)
        scored.append((score, ex))

    # Sắp xếp ổn định: điểm BM25 giảm dần, hòa điểm ưu tiên theo id tăng dần
    scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))

    chosen: list[dict] = []
    seen_tpls: set[str] = set()
    used_ids: set[str] = set()
    if diverse:
        for score, ex in scored:
            tid = ex.get("template_id")
            if tid in seen_tpls:
                continue
            chosen.append(dict(ex, score=round(score, 4)))
            seen_tpls.add(tid)
            used_ids.add(ex["id"])
            if len(chosen) >= k:
                return chosen

    for score, ex in scored:
        if ex["id"] in used_ids:
            continue
        chosen.append(dict(ex, score=round(score, 4)))
        used_ids.add(ex["id"])
        if len(chosen) >= k:
            break
    return chosen


def format_examples(examples: list[dict]) -> str:
    """Định dạng các ví dụ thành khối text ghép thẳng vào prompt của proposed.py."""
    if not examples:
        return ""
    blocks = ["Examples:"]
    for ex in examples:
        blocks.append(f"Question: {ex['question']}\nCypher: {_compact_cypher(ex['gold'])}")
    return "\n\n".join(blocks)


def select(
    question: str,
    k: int = DEFAULT_K,
    exclude_template: str | None = None,
    strategy: str = "bm25",
    diverse: bool = True,
) -> str:
    """Hàm chính cho Module (C): trả về đoạn text chứa k ví dụ đưa thẳng vào prompt."""
    examples = select_examples(
        question=question,
        k=k,
        exclude_template=exclude_template,
        strategy=strategy,
        diverse=diverse,
    )
    return format_examples(examples)


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    examples = json.loads(DEV_FILE.read_text(encoding="utf-8"))
    for strat, div in [("fixed", True), ("bm25", False), ("bm25", True)]:
        h1 = h3 = 0
        toks = []
        for q in examples:
            picks = select_examples(q["question"], k=3, strategy=strat, diverse=div)
            assert all(p["template_id"] != q["template_id"] for p in picks), "Vi phạm leave-template-out!"
            h1 += int(bool(picks and picks[0]["type"] == q["type"]))
            h3 += int(any(p["type"] == q["type"] for p in picks))
            toks.append(estimate_tokens(format_examples(picks)))
        n = len(examples)
        avg_t = sum(toks) / n
        print(f"strategy={strat:<5} diverse={str(div):<5} | Hit@1(type)={h1}/{n} ({h1*100/n:.1f}%) | "
              f"Hit@3(type)={h3}/{n} ({h3*100/n:.1f}%) | AvgTokens={avg_t:.1f}")
