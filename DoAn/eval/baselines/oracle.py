"""Oracle: trả về đúng Cypher gold. CHỈ dùng để kiểm tra khung chấm (phải đạt 100%), không phải baseline."""
import json
from pathlib import Path

QDIR = Path(__file__).resolve().parent.parent / "questions"


def build(model=None):
    gold = {q["question"]: q["gold"]
            for split in ("dev", "test")
            for q in json.loads((QDIR / f"{split}.json").read_text(encoding="utf-8"))}
    return lambda question: gold.get(question, "")
