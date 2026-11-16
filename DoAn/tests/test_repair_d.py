"""T34 – Unit test cho (D) eval/proposed/repair_d.py, eval/proposed/common.py và phần kiểm tra của
eval/baselines/proposed.py.

Chạy:
    cd DoAn
    python -m unittest discover -s tests -v

Không gọi LLM (dùng hàm chat giả). Nhóm TestCheckNeo4j cần Neo4j đang chạy, tự bỏ qua nếu không kết nối được.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from pilot_text2cypher import AUTH, PROMPT, URI  # noqa: E402
from proposed import common, repair_d  # noqa: E402
from proposed.repair_d import NOT_FOUND, Problem, check, repair, same_query  # noqa: E402


class FakeRecord(dict):
    """Mô phỏng neo4j.Record (có .keys(), .values(), .items())."""


class FakeResult:
    def __init__(self, records):
        self.records = records

    def fetch(self, n):
        return self.records[:n]

    def consume(self):
        pass


class FakeSession:
    """session.run(Query) trả về các dòng đặt sẵn theo nội dung truy vấn."""

    def __init__(self, table):
        self.table = table

    def run(self, query):
        return FakeResult([FakeRecord(d) for d in self.table[query.text]])


class TestCheckFake(unittest.TestCase):
    session = FakeSession({
        "EMPTY": [], "ZERO": [{"n": 0}], "ZERO_FLOAT": [{"avg": 0.0}], "NULL": [{"x": None}],
        "FALSE": [{"b": False}], "TWO_ZERO_ROWS": [{"n": 0}, {"n": 0}], "OK": [{"name": "Oxford"}],
        "NAME_AND_ZERO": [{"name": "Oxford", "n": 0}],
    })

    def kind(self, cypher):
        p = check(self.session, cypher)
        return p.kind if p else None

    def test_no_query(self):
        self.assertEqual(self.kind(""), "no_query")
        self.assertEqual(self.kind("   "), "no_query")

    def test_empty_and_zero_are_suspicious_not_errors(self):
        self.assertEqual(self.kind("EMPTY"), "empty")
        self.assertEqual(self.kind("ZERO"), "zero")
        self.assertEqual(self.kind("ZERO_FLOAT"), "zero")
        self.assertEqual(self.kind("NULL"), "zero")
        for k in ("empty", "zero"):
            self.assertIn(k, repair_d.SUSPICIOUS)
            self.assertNotIn(k, repair_d.MUST_FIX)

    def test_values_that_are_not_zero(self):
        """False không phải 0; nhiều dòng 0 hoặc dòng có tên kèm số 0 là kết quả bình thường."""
        self.assertIsNone(self.kind("FALSE"))
        self.assertIsNone(self.kind("TWO_ZERO_ROWS"))
        self.assertIsNone(self.kind("NAME_AND_ZERO"))
        self.assertIsNone(self.kind("OK"))


def neo4j_session():
    try:
        from neo4j import READ_ACCESS, GraphDatabase
        driver = GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF")
        driver.verify_connectivity()
        return driver, driver.session(default_access_mode=READ_ACCESS)
    except Exception:
        return None, None


class TestCheckNeo4j(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver, cls.session = neo4j_session()
        if cls.session is None:
            raise unittest.SkipTest("Neo4j không chạy")

    @classmethod
    def tearDownClass(cls):
        cls.session.close()
        cls.driver.close()

    def kind(self, cypher):
        p = check(self.session, cypher)
        return p.kind if p else None

    def test_syntax_error_must_fix(self):
        p = check(self.session, "MATCH (p:Person RETURN p")
        self.assertEqual(p.kind, "error")
        self.assertTrue(p.message.startswith("it failed with this error: "))

    def test_write_is_rejected_in_read_session(self):
        self.assertEqual(self.kind("CREATE (:Person {firstName: 'Test'})"), "error")

    def test_whole_nodes_must_fix(self):
        self.assertEqual(self.kind("MATCH (p:Person) RETURN p LIMIT 1"), "graph_object")
        self.assertEqual(self.kind("MATCH (p:Person) WITH p LIMIT 2 RETURN collect(p)"), "graph_object")
        self.assertEqual(self.kind("MATCH (a:Person)-[k:KNOWS]-() RETURN k LIMIT 1"), "graph_object")

    def test_values_ok_empty_zero(self):
        self.assertIsNone(self.kind("MATCH (p:Person) RETURN count(p)"))
        self.assertEqual(self.kind("MATCH (p:Person {firstName: 'No_Such_Name'}) RETURN p.lastName"), "empty")
        self.assertEqual(self.kind("MATCH (p:Person {firstName: 'No_Such_Name'}) RETURN count(p)"), "zero")


class ScriptedChat:
    """LLM giả: trả lần lượt các câu trả lời đặt trước, ghi lại prompt đã nhận."""

    def __init__(self, *replies):
        self.replies, self.prompts, self.options = list(replies), [], []

    def __call__(self, model, prompt, **options):
        self.prompts.append(prompt)
        self.options.append(options)
        return self.replies.pop(0)


HEAD = "INSTRUCTIONS + SCHEMA\n\nQuestion: q?\n"
P_EMPTY, P_ZERO = Problem("empty", "it returned no rows."), Problem("zero", "it returned only 0 or null.")
P_ERROR = Problem("error", "it failed with this error: Invalid input")


def run_repair(problems, *replies, model="model"):
    """Chạy repair với check giả (theo bảng problems: cypher -> Problem | None) và LLM giả."""
    chat = ScriptedChat(*replies)
    with mock.patch.object(repair_d, "check", lambda session, cypher: problems.get(cypher)):
        cypher, info = repair(model, None, HEAD, "Q1", chat=chat)
    return cypher, info, chat


class TestRepairLoop(unittest.TestCase):
    def test_ok_query_is_not_sent_to_llm(self):
        cypher, info, chat = run_repair({"Q1": None})
        self.assertEqual((cypher, info["fix_calls"], chat.prompts), ("Q1", 0, []))
        self.assertEqual(info["first_cypher"], "Q1")
        self.assertIsNone(info["final_problem"])

    def test_empty_result_can_be_kept(self):
        """Rỗng: LLM xem lại và trả đúng truy vấn cũ -> giữ nguyên, dừng sau 1 lần gọi."""
        cypher, info, chat = run_repair({"Q1": P_EMPTY}, "Q1;")
        self.assertEqual(cypher, "Q1")
        self.assertEqual(info["decisions"], ["kept"])
        self.assertEqual(info["fix_calls"], 1)
        self.assertEqual(info["final_problem"], "empty")
        self.assertIn("return the same query unchanged", chat.prompts[0])

    def test_zero_result_can_be_changed(self):
        cypher, info, _ = run_repair({"Q1": P_ZERO, "Q2": None}, "Q2")
        self.assertEqual((cypher, info["decisions"], info["chosen"]), ("Q2", ["changed"], 1))

    def test_rewrite_with_same_empty_result_keeps_old_query(self):
        """Rỗng -> LLM viết lại nhưng vẫn rỗng -> dừng (same_result), giữ truy vấn cũ, không hỏi lần 2."""
        cypher, info, chat = run_repair({"Q1": P_EMPTY, "Q2": P_EMPTY}, "Q2", "Q3")
        self.assertEqual((cypher, info["decisions"], info["fix_calls"]), ("Q1", ["same_result"], 1))
        self.assertEqual(len(chat.prompts), 1)

    def test_empty_to_zero_is_reviewed_again(self):
        """Rỗng -> 0 là kết quả khác: xem lại thêm một lần."""
        cypher, info, _ = run_repair({"Q1": P_EMPTY, "Q2": P_ZERO}, "Q2", "Q2")
        self.assertEqual((cypher, info["decisions"]), ("Q2", ["changed", "kept"]))

    def test_low_reasoning_effort_only_for_gpt_oss(self):
        _, _, chat = run_repair({"Q1": P_EMPTY}, "Q1", model="openai/gpt-oss-20b")
        self.assertEqual(chat.options, [{"reasoning_effort": "low"}])
        _, _, chat = run_repair({"Q1": P_EMPTY}, "Q1", model="llama-3.3-70b-versatile")
        self.assertEqual(chat.options, [{}])

    def test_error_gets_fix_instruction_and_shared_prefix(self):
        cypher, info, chat = run_repair({"Q1": P_ERROR, "Q2": None}, "```cypher\nQ2\n```")
        self.assertEqual(cypher, "Q2")
        prompt = chat.prompts[0]
        self.assertTrue(prompt.startswith(HEAD), "prompt sửa phải dùng chung tiền tố với prompt sinh Cypher")
        self.assertIn("Write a corrected query.", prompt)
        self.assertIn("Invalid input", prompt)
        self.assertNotIn("return the same query unchanged", prompt)
        self.assertTrue(prompt.endswith("Cypher:"))

    def test_never_returns_worse_query(self):
        """Rỗng -> LLM sửa thành truy vấn lỗi hai lần -> trả lại truy vấn đầu (rỗng tốt hơn lỗi)."""
        cypher, info, _ = run_repair({"Q1": P_EMPTY, "Q2": P_ERROR, "Q3": P_ERROR}, "Q2", "Q3")
        self.assertEqual((cypher, info["chosen"], info["fix_calls"]), ("Q1", 0, 2))
        self.assertEqual(info["problems"], ["empty", "error"])
        self.assertEqual(info["final_problem"], "empty")

    def test_at_most_two_fixes_latest_of_equal_severity(self):
        cypher, info, _ = run_repair({"Q1": P_ERROR, "Q2": P_ERROR, "Q3": P_ERROR}, "Q2", "Q3", "Q4")
        self.assertEqual((cypher, info["fix_calls"]), ("Q3", 2))

    def test_unchanged_fix_stops(self):
        cypher, info, _ = run_repair({"Q1": P_ERROR}, "Q1", "Q9")
        self.assertEqual((cypher, info["decisions"], info["fix_calls"]), ("Q1", ["unchanged"], 1))

    def test_empty_llm_output_keeps_previous_query(self):
        cypher, info, _ = run_repair({"Q1": P_EMPTY}, "")
        self.assertEqual((cypher, info["decisions"]), ("Q1", ["no_output"]))

    def test_no_query_is_regenerated(self):
        chat = ScriptedChat("Q2")
        problems = {"": Problem("no_query", "no query was produced."), "Q2": None}
        with mock.patch.object(repair_d, "check", lambda session, cypher: problems.get(cypher)):
            cypher, info = repair("model", None, HEAD, "", chat=chat)
        self.assertEqual(cypher, "Q2")
        self.assertIn("(none)", chat.prompts[0])

    def test_same_query_normalization(self):
        self.assertTrue(same_query("MATCH (n)\n  RETURN n.name;", "MATCH (n) RETURN n.name"))
        self.assertFalse(same_query("MATCH (n) RETURN n.name", "MATCH (n) RETURN n.title"))


class TestAnswer(unittest.TestCase):
    def test_empty_rows_do_not_call_llm(self):
        chat = ScriptedChat()
        self.assertEqual(repair_d.answer("model", "q?", [], chat=chat), NOT_FOUND)
        self.assertEqual(chat.prompts, [])

    def test_at_most_20_rows_and_row_count_is_stated(self):
        chat = ScriptedChat("They are ...")
        rows = [FakeRecord({"name": f"P{i}"}) for i in range(25)]
        self.assertEqual(repair_d.answer("model", "Who?", rows, chat=chat), "They are ...")
        prompt = chat.prompts[0]
        self.assertIn("first 20 of 25 rows", prompt)
        self.assertIn('"P19"', prompt)
        self.assertNotIn('"P20"', prompt)

    def test_single_row_and_empty_reply_fallback(self):
        chat = ScriptedChat("  ")
        reply = repair_d.answer("model", "How many?", [FakeRecord({"n": 0})], chat=chat)
        self.assertIn("(1 row)", chat.prompts[0])
        self.assertIn("Its results are the answer to the question.", chat.prompts[0])
        self.assertEqual(reply, 'Query results: {"n": 0}')

    def test_answer_prefix_is_stripped(self):
        chat = ScriptedChat("Answer: There are no people who live in Uruguay.")
        reply = repair_d.answer("model", "How many people live in Uruguay?", [FakeRecord({"total": 0})], chat=chat)
        self.assertEqual(reply, "There are no people who live in Uruguay.")


class TestCommonAndBuild(unittest.TestCase):
    def test_banned_values_never_reads_test2(self):
        self.assertNotIn("test2", common.BANNED_SPLITS)

    def test_banned_values_cover_dev_zero_and_old_test(self):
        import json
        banned = common.banned_values()
        with_underscore = []
        for split in ("dev_zero", "test", "dev"):
            questions = json.loads((common.QDIR / f"{split}.json").read_text(encoding="utf-8"))
            for v in questions[0]["params"].values():
                self.assertIn(str(v), banned, f"{split}: {v}")
            with_underscore += [v for q in questions for v in q["params"].values() if isinstance(v, str) and "_" in v]
        self.assertTrue(with_underscore, "cần ít nhất một tham số có dấu _ để kiểm tra biến thể")
        self.assertIn(with_underscore[0].replace("_", " "), banned)

    def test_proposed_prompt_is_b1_frame(self):
        from baselines import proposed
        self.assertEqual(proposed.HEAD + "Cypher:", PROMPT)

    def test_build_rejects_missing_components(self):
        from baselines import proposed
        with self.assertRaises(NotImplementedError):
            proposed.build("model")                            # (B), (C) chưa tích hợp
        with self.assertRaises(ValueError):
            proposed.build("model", off={"E"})


if __name__ == "__main__":
    unittest.main()
