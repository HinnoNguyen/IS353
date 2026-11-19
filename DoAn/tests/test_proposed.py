"""T35 – Unit test cho phần ghép hệ thống đề xuất eval/baselines/proposed.py và các module mỏng.

Chạy:
    cd DoAn
    python -m unittest discover -s tests -v

Không cần Neo4j hay LLM.
"""
import importlib
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from baselines import proposed  # noqa: E402
from pilot_text2cypher import PROMPT  # noqa: E402

SCHEMA = "Node labels and properties:\n  (:Person) {firstName: String}"
EXAMPLES = "Examples:\n\nQuestion: q1?\nCypher: MATCH (n) RETURN n.name"
HINTS = "Relevant entities in the graph:\n- Person: firstName='A', lastName='B'\n\n"


class TestPrompt(unittest.TestCase):
    def test_without_b_c_prompt_is_exactly_b1(self):
        """Tắt B, C: prompt sinh Cypher giống hệt B1, chỉ khác nội dung schema (đối chứng B1 + A công bằng)."""
        head = proposed.prompt_head(SCHEMA, "Who?", proposed.prompt_extra())
        self.assertEqual(head + "Cypher:", PROMPT.format(schema=SCHEMA, question="Who?"))

    def test_examples_then_hints_right_before_question(self):
        extra = proposed.prompt_extra(EXAMPLES, HINTS)
        head = proposed.prompt_head(SCHEMA, "Who?", extra)
        i_schema, i_ex, i_hint, i_q = (head.index(s) for s in (SCHEMA, "Examples:", "Relevant entities",
                                                                 "Question: Who?"))
        self.assertLess(i_schema, i_ex)
        self.assertLess(i_ex, i_hint)
        self.assertLess(i_hint, i_q)
        self.assertNotIn("\n\n\n", head, "các khối chỉ cách nhau một dòng trống")

    def test_only_hints_matches_previous_b_integration(self):
        """Cấu hình có B mà không có C: phần thêm giống cách ghép của Ân (schema + '\\n\\n' + hints.strip())."""
        self.assertEqual(proposed.prompt_extra("", HINTS), "\n\n" + HINTS.strip())

    def test_empty_parts_add_nothing(self):
        self.assertEqual(proposed.prompt_extra("", ""), "")
        self.assertEqual(proposed.prompt_extra("  ", "\n"), "")


class TestThinModules(unittest.TestCase):
    def test_every_thin_module_turns_off_the_listed_components(self):
        for name, (off, _) in proposed.CONFIGS.items():
            if name == "proposed":
                continue
            module = importlib.import_module(f"baselines.{name}")
            with mock.patch.object(module, "build_proposed", lambda model, off: frozenset(off)):
                self.assertEqual(module.build("m"), frozenset(off), name)

    def test_full_pipeline_has_nothing_off(self):
        self.assertEqual(proposed.CONFIGS["proposed"][0], set())
        self.assertEqual(proposed.build.__defaults__, (frozenset(),))

    def test_registry_lists_every_proposed_module(self):
        files = {p.stem for p in (ROOT / "eval" / "baselines").glob("proposed*.py")} - {"proposed_v0"}
        self.assertEqual(files, set(proposed.CONFIGS))

    def test_section_3_2_configurations(self):
        """Đúng 5 cấu hình proposed của mục 3.2 chạy trên test2 với gpt-oss-20b."""
        official = {n for n, (_, tag) in proposed.CONFIGS.items() if tag == "3.2"}
        self.assertEqual(official, {"proposed_a", "proposed_ab", "proposed_abc", "proposed", "proposed_no_a"})


if __name__ == "__main__":
    unittest.main()
