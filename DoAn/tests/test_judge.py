"""T25 + T60 – Unit test cho hàm chấm điểm judge, answer_rows, row_values, norm trong eval/pilot_text2cypher.py.

Chạy bằng pytest hoặc unittest:
    cd DoAn
    python -m pytest tests/test_judge.py -v -rx
    python -m unittest discover -s tests -v

================================================================================
DANH SÁCH CÁC CA HÀM `judge` CHẤM KHÁC KỲ VỌNG (UNEXPECTED / QUIRKY BEHAVIORS)
================================================================================
Do `judge(gold_rows, pred_records)` được đóng băng để giữ tính nhất quán xuyên suốt
các đợt đánh giá, các trường hợp dưới đây được ghi nhận lại (không tự ý sửa `judge`
ngoài ca gold rỗng của T60) để giải thích trong báo cáo và đối chiếu với Module (D):

1. Trả về nguyên Node hoặc dict thuộc tính (`RETURN u` thay vì `RETURN u.name`) -> `wrong_result`
   - Kỳ vọng ngữ nghĩa: Nếu câu hỏi hỏi tên trường và dự đoán trả về nguyên Node
     `(:University {id: 10, name: 'Oxford'})`, thông tin đáp án ('Oxford') có nằm trong Node.
   - Thực tế `judge`:
     + Với `neo4j.graph.Node`: `norm(node)` ép cả đối tượng thành một chuỗi dài
       `"<node element_id=... properties={'id': 10, 'name': 'oxford'}>"`, không tách rời
       giá trị thuộc tính `'oxford'` vào tập `row_values` -> chấm `wrong_result`.
     + Với `dict`: `row_values` lọc bỏ mọi phần tử kiểu `dict`
       (`if not isinstance(v, (list, dict))`) -> tập giá trị rỗng -> chấm `wrong_result`.
   - Cách xử lý trong hệ thống: Quy ước C7 của Module (A) nhắc chỉ `RETURN` thuộc tính,
     và hàm `check()` của Module (D) (`repair_d.py`) bắt lỗi `graph_object` để buộc LLM sửa.

2. Số nguyên `3` so với số thực `3.0` (`int` vs `float`) -> `wrong_result`
   - Kỳ vọng toán học: `3` và `3.0` bằng nhau (ví dụ `count` so với phép chia / `toFloat`).
   - Thực tế `judge`: `norm(3)` trả về `"3"`, trong khi `norm(3.0)` đi vào nhánh `isinstance(v, float)`
     và trả về `str(round(3.0, 4)) == "3.0"`. Vì `"3" != "3.0"`, `judge([[3]], [{"n": 3.0}])`
     bị chấm `wrong_result`.

3. Giá trị `None` (`null` trong Cypher) đụng độ với chuỗi văn bản `"None"` / `"none"` -> `correct`
   - Kỳ vọng: Giá trị `null` (`None`) rỗng không được phép khớp với một thực thể có tên là chuỗi `"None"`.
   - Thực tế `judge`: `norm(None)` gọi `str(None).strip().lower()` tạo ra chuỗi `"none"`, trùng khớp
     với `norm("None") == "none"`. Do đó `judge([[None]], [{"x": "None"}])` và
     `judge([["None"]], [{"x": None}])` đều bị chấm là `correct`.
   - Ngoài ra, khi `gold` có dữ liệu (`[["Oxford"]]`) nhưng `pred` trả về 1 dòng chứa `None`
     (`[{"u.name": None}]`, thường gặp khi dùng `OPTIONAL MATCH` hoặc `max/min` trên tập rỗng),
     `len(pred_records) == 1` nên `judge` chấm `wrong_result` thay vì `empty_result`.

4. Dòng trùng trong `gold` che khuất dòng sai trong `pred` -> `correct`
   - Kỳ vọng: Nếu `gold = [["Alice"], ["Alice"]]` (2 dòng) và `pred = [{"n": "Alice"}, {"n": "Bob"}]`
     (1 dòng đúng, 1 dòng sai), kết quả phải là `wrong_result`.
   - Thực tế `judge`: Biểu thức `covered = all(any(... for p in pred_sets) for g in gold_rows)`
     chỉ kiểm tra từng dòng `g` của `gold` có xuất hiện ở *ít nhất một* dòng của `pred` hay không
     (không đối sánh 1–1 / multiset giữa các dòng), rồi chỉ so `len(pred_records) == len(gold_rows)`.
     Vì cả 2 dòng `["Alice"]` của `gold` cùng khớp vào dòng đầu của `pred` và tổng số dòng đều bằng 2,
     dòng sai `"Bob"` bị bỏ qua và `judge` chấm `correct`.

5. Ngày tháng khác kiểu hoặc khác định dạng chuỗi (`Date` vs `DateTime` / chuỗi khác chuẩn ISO) -> `wrong_result`
   - `neo4j.time.Date(1985, 6, 15)` khi qua `str()` cho chuỗi chuẩn ISO `"1985-06-15"`, nên khớp
     được với chuỗi `"1985-06-15"` (`correct`).
   - Tuy nhiên nếu một bên là `neo4j.time.Date(1985, 6, 15)` (`"1985-06-15"`) còn bên kia là
     `neo4j.time.DateTime(1985, 6, 15, 0, 0, 0)` (`"1985-06-15t00:00:00"`) hoặc chuỗi `"15/06/1985"`,
     `norm()` so sánh chuỗi thuần túy nên chấm `wrong_result`.

6. Ghép chuỗi nhiều cột phụ thuộc thứ tự cột trong `pred` -> `wrong_result`
   - Trong `row_values`, các cột kiểu `str` được nối theo đúng thứ tự xuất hiện trong `pred`:
     `norm(" ".join(strings))`. Nếu `gold` là `[["Anupam Reddy"]]` (1 cột) nhưng `pred` trả về
     ngược thứ tự cột `{"lastName": "Reddy", "firstName": "Anupam"}`, chuỗi ghép là `"reddy anupam"`
     nên bị chấm `wrong_result` (trong khi nếu `gold` tách 2 cột `[["Anupam", "Reddy"]]` thì lại `correct`
     nhờ kiểm tra tập con `set(map(norm, g)) <= p`).
"""
import datetime
import sys
import unittest
from pathlib import Path

import neo4j.time
import pytest
from neo4j.graph import Graph, Node

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from pilot_text2cypher import answer_rows, judge, norm, row_values  # noqa: E402

# Danh sách có cấu trúc các ca judge chấm khác kỳ vọng để tra cứu / xuất báo cáo
UNEXPECTED_JUDGE_CASES = [
    {
        "id": "U1_WHOLE_NODE_OR_DICT",
        "case": "Dự đoán trả về nguyên Node neo4j.graph.Node hoặc dict thuộc tính chứa đáp án đúng",
        "gold": [["Oxford"]],
        "pred": "[{'u': Node(:University {id: 10, name: 'Oxford'})}] hoặc [{'u': {'id': 10, 'name': 'Oxford'}}]",
        "expected": "correct (nếu xét có chứa thông tin đáp án)",
        "actual": "wrong_result",
        "reason": "row_values() loại bỏ dict và không mở phẳng thuộc tính của neo4j.graph.Node.",
    },
    {
        "id": "U2_INT_VS_FLOAT_EQUAL",
        "case": "Số nguyên 3 so với số thực 3.0",
        "gold": [[3]],
        "pred": "[{'val': 3.0}]",
        "expected": "correct",
        "actual": "wrong_result",
        "reason": "norm(3) == '3' nhưng norm(3.0) == str(round(3.0, 4)) == '3.0'.",
    },
    {
        "id": "U3_NONE_VS_STRING_NONE",
        "case": "Giá trị None (null) so với chuỗi chữ 'None' / 'none'",
        "gold": [[None]],
        "pred": "[{'x': 'None'}]",
        "expected": "wrong_result",
        "actual": "correct",
        "reason": "norm(None) gọi str(None).lower() -> 'none', trùng với norm('None').",
    },
    {
        "id": "U4_DUPLICATE_GOLD_MASKS_WRONG_PRED",
        "case": "Gold có dòng trùng làm che khuất dòng dự đoán sai khi cùng tổng số dòng",
        "gold": [["Alice"], ["Alice"]],
        "pred": "[{'name': 'Alice'}, {'name': 'Bob'}]",
        "expected": "wrong_result",
        "actual": "correct",
        "reason": "covered chỉ kiểm tra mọi dòng gold nằm trong ít nhất 1 dòng pred (không ghép cặp 1-1).",
    },
    {
        "id": "U5_DATE_VS_DATETIME_STRING",
        "case": "Cùng ngày nhưng một bên là Date('1985-06-15'), một bên là DateTime('1985-06-15T00:00:00') hoặc '15/06/1985'",
        "gold": [["Date(1985, 6, 15)"]],
        "pred": "[{'b': DateTime(1985, 6, 15, 0, 0, 0)}]",
        "expected": "correct (cùng ngày)",
        "actual": "wrong_result",
        "reason": "norm() chỉ gọi str(v) nên '1985-06-15' != '1985-06-15t00:00:00'.",
    },
    {
        "id": "U6_REVERSED_NAME_COLUMNS_VS_FULLNAME_GOLD",
        "case": "Gold 1 cột họ tên đầy đủ ['Anupam Reddy'], Pred trả 2 cột ngược thứ tự {lastName, firstName}",
        "gold": [["Anupam Reddy"]],
        "pred": "[{'lastName': 'Reddy', 'firstName': 'Anupam'}]",
        "expected": "correct",
        "actual": "wrong_result",
        "reason": "row_values() chỉ nối các cột chuỗi theo một chiều xuất hiện ('reddy anupam').",
    },
]


class FakeRecord(dict):
    """Mô phỏng neo4j.Record (có .keys(), .values(), __getitem__)."""


def make_records(*dicts):
    return [FakeRecord(d) for d in dicts]


def make_neo4j_node(element_id="4:test:1", node_id=1, labels=("University",), props=None):
    """Tạo đối tượng neo4j.graph.Node thật của driver Neo4j."""
    g = Graph()
    return Node(g, element_id, node_id, tuple(labels), props or {})


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

    def test_concatenated_name_in_gold_fails_when_pred_columns_reversed(self):
        """Ca chấm khác kỳ vọng (U6): Gold 1 cột ['Anupam Reddy'] nhưng Pred trả {lastName, firstName} ngược thứ tự."""
        self.assertEqual(
            judge([["Anupam Reddy"]], make_records({"lastName": "Reddy", "firstName": "Anupam"})),
            "wrong_result",
        )

    # --- 4. Nhiều dòng, thứ tự dòng & dòng trùng (Duplicate rows) ---

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

    def test_duplicate_rows_in_pred_rejected(self):
        """Dòng trùng trong dự đoán (vd. quên DISTINCT): thừa dòng hoặc lặp 1 dòng mà thiếu dòng khác -> wrong_result."""
        # Gold 1 dòng nhưng Pred trả 2 dòng trùng nhau
        self.assertEqual(
            judge([["Alice"]], make_records({"name": "Alice"}, {"name": "Alice"})),
            "wrong_result",
        )
        # Gold 2 dòng khác nhau nhưng Pred lặp 'Alice' 2 lần và thiếu 'Bob'
        self.assertEqual(
            judge([["Alice"], ["Bob"]], make_records({"name": "Alice"}, {"name": "Alice"})),
            "wrong_result",
        )

    def test_duplicate_rows_in_gold_masks_wrong_pred_row(self):
        """Ca chấm khác kỳ vọng (U4): Gold có 2 dòng trùng [['Alice'], ['Alice']], Pred trả 1 đúng + 1 sai vẫn 'correct'."""
        gold = [["Alice"], ["Alice"]]
        pred = make_records({"name": "Alice"}, {"name": "Bob"})
        self.assertEqual(judge(gold, pred), "correct")

    # --- 5. Số thực (float), 3 so với 3.0, danh sách (list) và answer_rows ---

    def test_float_rounding_four_decimals(self):
        """Số thực được làm tròn 4 chữ số thập phân khi so sánh."""
        self.assertEqual(norm(3.1415926), "3.1416")
        self.assertEqual(judge([[3.14159]], make_records({"avg": 3.14161})), "correct")

    def test_int_3_vs_float_3_0_is_wrong_result(self):
        """Ca chấm khác kỳ vọng (U2): norm(3) == '3' khác norm(3.0) == '3.0' nên 3 so với 3.0 bị chấm wrong_result."""
        self.assertEqual(norm(3), "3")
        self.assertEqual(norm(3.0), "3.0")
        self.assertEqual(judge([[3]], make_records({"val": 3.0})), "wrong_result")
        self.assertEqual(judge([[3.0]], make_records({"val": 3})), "wrong_result")

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

    # --- 6. Ngày Date so với chuỗi (neo4j.time.Date / datetime.date vs str) ---

    def test_date_object_matches_iso_string(self):
        """Đối tượng neo4j.time.Date và datetime.date khớp với chuỗi ngày chuẩn ISO 'YYYY-MM-DD'."""
        neo_d = neo4j.time.Date(1985, 6, 15)
        py_d = datetime.date(1985, 6, 15)
        self.assertEqual(norm(neo_d), "1985-06-15")
        self.assertEqual(norm(py_d), "1985-06-15")
        self.assertEqual(judge([[neo_d]], make_records({"birthday": "1985-06-15"})), "correct")
        self.assertEqual(judge([["1985-06-15"]], make_records({"birthday": neo_d})), "correct")
        self.assertEqual(judge([[py_d]], make_records({"birthday": "1985-06-15"})), "correct")

    def test_date_mismatch_or_datetime_format_difference(self):
        """Khác ngày hoặc so sánh Date('1985-06-15') với DateTime('1985-06-15T00:00:00') (U5) -> wrong_result."""
        neo_d = neo4j.time.Date(1985, 6, 15)
        neo_dt = neo4j.time.DateTime(1985, 6, 15, 0, 0, 0)
        self.assertEqual(judge([[neo_d]], make_records({"birthday": "1985-06-16"})), "wrong_result")
        self.assertEqual(judge([[neo_d]], make_records({"birthday": "15/06/1985"})), "wrong_result")
        self.assertEqual(judge([[neo_d]], make_records({"birthday": neo_dt})), "wrong_result")

    # --- 7. Giá trị None (null trong Cypher) ---

    def test_none_value_handling(self):
        """Kiểm tra None khi gold có dữ liệu (wrong_result), khi cả hai đều None (correct), và đụng độ chuỗi 'None' (U3)."""
        # Pred trả về 1 dòng có giá trị None khi gold là ['Oxford'] -> wrong_result (không phải empty_result)
        self.assertEqual(judge([["Oxford"]], make_records({"u.name": None})), "wrong_result")
        # Cả gold và pred đều có 1 dòng giá trị None -> correct
        self.assertEqual(judge([[None]], make_records({"u.name": None})), "correct")
        # Ca chấm khác kỳ vọng (U3): norm(None) == 'none' nên None khớp với chuỗi 'None' / 'none'
        self.assertEqual(norm(None), "none")
        self.assertEqual(judge([[None]], make_records({"u.name": "None"})), "correct")
        self.assertEqual(judge([["None"]], make_records({"u.name": None})), "correct")

    # --- 8. Trả về nguyên Node (RETURN u thay vì RETURN u.name) – đánh dấu xfail ---

    @pytest.mark.xfail(
        strict=True,
        reason="judge không mở phẳng thuộc tính của neo4j.graph.Node (U1): norm(node) biến cả Node thành chuỗi '<node ...>'",
    )
    @unittest.expectedFailure
    def test_whole_neo4j_node_in_pred_xfail(self):
        """Dự đoán trả về nguyên đối tượng neo4j.graph.Node chứa thuộc tính đúng -> judge hiện chấm wrong_result (xfail)."""
        node = make_neo4j_node(labels=("University",), props={"id": 10, "name": "Oxford"})
        self.assertEqual(judge([["Oxford"]], make_records({"u": node})), "correct")

    @pytest.mark.xfail(
        strict=True,
        reason="row_values() loại bỏ phần tử kiểu dict nên trả về node dạng dict bị rỗng tập giá trị (U1)",
    )
    @unittest.expectedFailure
    def test_whole_dict_node_in_pred_xfail(self):
        """Dự đoán trả về nguyên node dạng dict {'id': 10, 'name': 'Oxford'} -> judge hiện chấm wrong_result (xfail)."""
        self.assertEqual(
            judge([["Oxford"]], make_records({"u": {"id": 10, "name": "Oxford"}})),
            "correct",
        )


if __name__ == "__main__":
    unittest.main()
