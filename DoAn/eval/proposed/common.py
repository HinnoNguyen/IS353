"""Phần dùng chung của hệ thống đề xuất (Bằng – T34).

banned_values(): giá trị tham số của các bộ câu hỏi có từ trước khi khóa pipeline. Prompt không được chứa các giá
trị này (vd. tên mẫu trong quy ước của (A)), để không lộ thực thể của câu hỏi vào prompt.
- Đọc dev.json, dev_para.json, dev_zero.json và test.json cũ. Ba file dev* cũng có trước khi khóa pipeline, nên
  thêm chúng không làm prompt đổi sau đó; nhờ vậy tên mẫu của (A) không bao giờ trùng thực thể của dev_zero.
- KHÔNG đọc test2.json (GIAO_VIEC_CUOI_KY.md mục 2.5): prompt phải giống hệt trước và sau khi công bố test2.
"""
import json
from pathlib import Path

QDIR = Path(__file__).resolve().parents[1] / "questions"
BANNED_SPLITS = ("dev", "dev_para", "dev_zero", "test")   # không bao giờ thêm test2


def banned_values():
    """Tập giá trị tham số (giữ nguyên chữ hoa/thường, kèm biến thể dấu cách <-> dấu _)."""
    banned = set()
    for split in BANNED_SPLITS:
        path = QDIR / f"{split}.json"
        if not path.exists():
            continue
        for q in json.loads(path.read_text(encoding="utf-8")):
            for v in q.get("params", {}).values():
                s = str(v).strip()
                banned |= {s, s.replace(" ", "_"), s.replace("_", " ")}
    return banned
