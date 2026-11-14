"""T25 + T60 – Unit test cho hàm chấm điểm judge, answer_rows, row_values, norm trong eval/pilot_text2cypher.py.

Chạy:
    cd DoAn
    python -m unittest discover -s tests -v
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from pilot_text2cypher import answer_rows, judge, norm, row_values  # noqa: E402


class FakeRecord(dict):
    """Mô phỏng neo4j.Record (có .keys(), .values(), __getitem__)."""


def make_records(*dicts):
    return [FakeRecord(d) for d in dicts]


class TestJudge(unittest.TestCase):
    # --- 1. Ca gold rỗng và đếm bằng 0 (T60) ---

    def test_empty_gold_and_empty_pred_is_correct(self):
        """Khi đáp án đúng là rỗng (0 dòng) và dự đoán cũng rỗng -> correct."""
        self.assertEqual(judge([], []), "correct")

    def test_empty_gold_and_nonempty_pred_is_wrong(self):
        """Khi đáp án đúng là rỗng nhưng dự đoán trả về dòng -> wrong_result."""
        self.assertEqual(judge([], make_records({"name": "Oxford"})), "wrong_result")

    def test_nonempty_gold_and_empty_pred_is_empty_result(self):
        """Khi đáp án đúng có dữ liệu nhưng dự đoán rỗng -> empty_result."""
        self.assertEqual(judge([["Oxford"]], []), "empty_result")

    def test_zero_count_gold_and_zero_pred_is_correct(self):
        """Câu đếm có đáp án [[0]] và dự đoán trả về 0 -> correct."""
        self.assertEqual(judge([[0]], make_records({"total": 0})), "correct")

    def test_zero_count_gold_and_empty_pred_is_empty_result(self):
        """Câu đếm có đáp án [[0]] nhưng dự đoán không trả dòng nào -> empty_result."""
        self.assertEqual(judge([[0]], []), "empty_result")

    def test_zero_count_gold_and_nonzero_pred_is_wrong(self):
        """Câu đếm có đáp án [[0]] nhưng dự đoán trả về 2 -> wrong_result."""
        self.assertEqual(judge([[0]], make_records({"total": 2})), "wrong_result")

    # --- 2. Khớp cơ bản, hoa thường, khoảng trắng, cột phụ ---

    def test_exact_single_value_case_and_whitespace(self):
        """So khớp không phân biệt hoa thường và khoảng trắng đầu/cuối."""
        self.assertEqual(
            judge([["Rawalpindi_Medical_College"]], make_records({"u.name": "  rawalpindi_medical_college \n"})),
            "correct",
        )

    def test_extra_columns_in_pred_still_correct(self):
        """Dự đoán trả thêm cột phụ (vd. id, count) nhưng chứa đủ đáp án trên cùng dòng -> correct."""
        self.assertEqual(
            judge([["University_of_Oxford"]], make_records({"id": 101, "name": "University_of_Oxford", "n": 5})),
            "correct",
        )

    # --- 3. Ghép họ tên (firstName + lastName) ---

    def test_split_name_in_gold_matches_concatenated_in_pred(self):
        """Gold tách 2 cột ['Anupam', 'Reddy'] khớp với dự đoán ghép 1 cột 'Anupam Reddy'."""
        self.assertEqual(
            judge([["Anupam", "Reddy"]], make_records({"person": "Anupam Reddy"})),
            "correct",
        )

    def test_concatenated_name_in_gold_matches_split_in_pred(self):
        """Gold 1 cột ['Anupam Reddy'] khớp với dự đoán tách 2 cột firstName, lastName."""
        self.assertEqual(
            judge([["Anupam Reddy"]], make_records({"firstName": "Anupam", "lastName": "Reddy"})),
            "correct",
        )

    # --- 4. Nhiều dòng & thứ tự dòng ---

    def test_multiple_rows_order_independent(self):
        """Nhiều dòng đáp án khớp không phụ thuộc thứ tự dòng."""
        gold = [["Alice", "Smith"], ["Bob", "Jones"]]
        pred = make_records(
            {"firstName": "Bob", "lastName": "Jones"},
            {"firstName": "Alice", "lastName": "Smith"},
        )
        self.assertEqual(judge(gold, pred), "correct")

    def test_row_count_mismatch_too_many_or_too_few(self):
        """Số dòng dự đoán nhiều hơn hoặc ít hơn gold -> wrong_result."""
        gold = [["Alice"], ["Bob"]]
        self.assertEqual(judge(gold, make_records({"name": "Alice"})), "wrong_result")
        self.assertEqual(
            judge(
                [["Alice"]],
                make_records({"name": "Alice"}, {"name": "Bob"}),
            ),
            "wrong_result",
        )

    # --- 5. Số thực (float), danh sách (list) và answer_rows ---

    def test_float_rounding_four_decimals(self):
        """Số thực được làm tròn 4 chữ số thập phân khi so sánh."""
        self.assertEqual(norm(3.1415926), "3.1416")
        self.assertEqual(judge([[3.14159]], make_records({"avg": 3.14161})), "correct")

    def test_list_value_in_pred_row(self):
        """Cột kiểu list trong dự đoán được mở phẳng để đối chiếu từng phần tử."""
        vals = row_values([["en", "de", "fr"]])
        self.assertTrue({"en", "de", "fr"} <= vals)
        self.assertEqual(judge([["de"]], make_records({"speaks": ["en", "de"]})), "correct")

    def test_answer_rows_strips_aux_n_column(self):
        """answer_rows bỏ cột phụ 'n' khi còn cột khác, nhưng giữ lại nếu chỉ có cột 'n'."""
        recs_with_n = make_records({"u.name": "Oxford", "n": 12})
        self.assertEqual(answer_rows(recs_with_n), [["Oxford"]])

        recs_only_n = make_records({"n": 12})
        self.assertEqual(answer_rows(recs_only_n), [[12]])

        self.assertEqual(answer_rows([]), [])


if __name__ == "__main__":
    unittest.main()

