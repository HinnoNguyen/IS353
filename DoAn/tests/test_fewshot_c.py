"""T33 – Unit test cho Module (C) eval/proposed/fewshot_c.py (Vũ).

Chạy:
    python -m unittest tests/test_fewshot_c.py -v

Không gọi LLM, không đọc test.json hay test2.json.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from proposed import fewshot_c  # noqa: E402

QDIR = ROOT / "eval" / "questions"


class TestFewshotC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dev = json.loads((QDIR / "dev.json").read_text(encoding="utf-8"))
        cls.dev_ids = {q["id"] for q in cls.dev}

    def test_only_uses_dev_examples(self):
        """Kho ví dụ chỉ lấy từ dev.json (92 câu, 10 template)."""
        for q in self.dev:
            picks = fewshot_c.select_examples(q["question"], k=3)
            self.assertEqual(len(picks), 3)
            for p in picks:
                self.assertIn(p["id"], self.dev_ids)

    def test_leave_template_out_on_dev(self):
        """Mọi câu dev đều phải loại toàn bộ ví dụ cùng template_id kể cả khi không truyền exclude_template."""
        for q in self.dev:
            picks = fewshot_c.select_examples(q["question"], k=3)
            self.assertTrue(all(p["template_id"] != q["template_id"] for p in picks), q["id"])

    def test_leave_template_out_on_dev_para(self):
        """Câu viết lại ở dev_para vẫn được nhận diện template để loại trừ ví dụ cùng template."""
        dev_para = json.loads((QDIR / "dev_para.json").read_text(encoding="utf-8"))
        for q in dev_para:
            picks = fewshot_c.select_examples(q["question"], k=3)
            self.assertEqual(len(picks), 3)
            self.assertTrue(all(p["template_id"] != q["template_id"] for p in picks), q["id"])

    def test_leave_template_out_on_dev_zero_or_explicit_exclude(self):
        """Nếu có dev_zero.json thì tự nhận diện; luôn tôn trọng exclude_template tường minh."""
        dev_zero_path = QDIR / "dev_zero.json"
        if dev_zero_path.exists():
            dev_zero = json.loads(dev_zero_path.read_text(encoding="utf-8"))
            for q in dev_zero:
                picks = fewshot_c.select_examples(q["question"], k=3)
                self.assertTrue(all(p["template_id"] != q["template_id"] for p in picks), q["id"])
        # Kiểm tra tường minh kể cả với câu ngoài dev nhưng truyền exclude_template
        picks = fewshot_c.select_examples("What university does Alice attend?", k=3, exclude_template="LK-03")
        self.assertTrue(all(p["template_id"] != "LK-03" for p in picks))

    def test_diverse_templates_and_k_bounds(self):
        """Mặc định diverse=True chọn 3 template khác nhau; k=0 trả về rỗng."""
        unseen_q = "Which university do the largest number of Narong Boy's friends study at?"
        picks = fewshot_c.select_examples(unseen_q, k=3)
        self.assertEqual(len(picks), 3)
        self.assertEqual(len({p["template_id"] for p in picks}), 3)
        self.assertEqual(fewshot_c.select(unseen_q, k=0), "")

    def test_output_format_and_token_budget(self):
        """Đoạn text đầu ra đúng định dạng 'Examples:\\nQuestion: ...\\nCypher: ...' và gọn token."""
        block = fewshot_c.select("Who are the mutual friends of Alice and Bob?", k=3)
        self.assertTrue(block.startswith("Examples:\n"))
        self.assertEqual(block.count("Question: "), 3)
        self.assertEqual(block.count("Cypher: "), 3)
        self.assertLess(fewshot_c.estimate_tokens(block), 400)

    def test_does_not_reference_test_or_test2(self):
        """Mã nguồn fewshot_c.py không đọc các file test.json hoặc test2.json."""
        src = (ROOT / "eval" / "proposed" / "fewshot_c.py").read_text(encoding="utf-8")
        self.assertNotIn("test.json", src)
        self.assertNotIn("test2.json", src)


if __name__ == "__main__":
    unittest.main()
