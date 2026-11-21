"""Hệ thống đề xuất: (A) schema chi tiết, (B) liên kết thực thể, (C) few-shot động, (D) tự sửa lỗi (T35).

build(model, off=frozenset()): off ⊆ {"A", "B", "C", "D"} là các thành phần bị tắt (GIAO_VIEC_CUOI_KY.md mục 5.1).
- (A) tắt: schema cơ bản của B1 (build_schema). Bật: proposed/schema_a.detailed_schema (Khôi, T31).
- (B) tắt: không có gợi ý. Bật: proposed/entity_link.format_hints, tra thực thể bằng full-text index (Ân, T32);
  cần chạy scripts/create_fulltext_index.py một lần trên Neo4j.
- (C) tắt: không có ví dụ. Bật: proposed/fewshot_c, k = 3 ví dụ BM25 chỉ lấy từ dev.json, tự loại ví dụ cùng
  template với câu dev/dev_zero/dev_para (Vũ, T33).
- (D) tắt: không sửa. Bật: proposed/repair_d (Bằng, T34).

Prompt sinh Cypher chỉ nằm ở file này (prompt_head): đúng khung PROMPT của B1, khối schema = schema (+ ví dụ của C)
(+ gợi ý thực thể của B), rồi đến câu hỏi. Gợi ý của B đặt sát câu hỏi để không lẫn với các câu hỏi ví dụ. Vì vậy
khi tắt B, C, D, cấu hình chỉ khác B1 ở (A). Prompt sửa lỗi và prompt trả lời nằm trong proposed/repair_d.py.
Mỗi cấu hình là một module mỏng có tên riêng (cache riêng), xem CONFIGS.
generate.last_info: llm_calls, first_cypher (Cypher trước khi sửa), prompt_extra (phần B, C thêm vào sau schema,
để eval/audit/replay_d.py dựng lại đúng prompt), examples_c (id các ví dụ của C) và, khi bật (D), thông tin vòng sửa.
"""
import hashlib
import subprocess
from pathlib import Path

from neo4j import READ_ACCESS, GraphDatabase

from llm import groq_chat
from pilot_text2cypher import AUTH, URI, build_schema, extract_cypher
from pilot_text2cypher import PROMPT as B1_PROMPT
from proposed import entity_link, fewshot_c, repair_d
from proposed.schema_a import detailed_schema

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = frozenset("ABCD")
HEAD = B1_PROMPT.removesuffix("Cypher:")   # "...Schema:\n{schema}\n\nQuestion: {question}\n"
assert HEAD != B1_PROMPT, "PROMPT của B1 phải kết thúc bằng 'Cypher:'"

# Module mỏng trong eval/baselines/ -> các thành phần bị tắt. Cấu hình của GIAO_VIEC_CUOI_KY.md mục 3.2 đánh dấu "3.2";
# các cấu hình còn lại chỉ dùng trên dev/dev_zero.
CONFIGS = {
    "proposed_a": ({"B", "C", "D"}, "3.2"),     # B1 + (A)
    "proposed_ab": ({"C", "D"}, "3.2"),
    "proposed_abc": ({"D"}, "3.2"),
    "proposed": (set(), "3.2"),                 # đầy đủ A + B + C + D
    "proposed_no_a": ({"A"}, "3.2"),            # B + C + D
    "proposed_ad": ({"B", "C"}, "dev"),
    "proposed_abd": ({"C"}, "dev"),
}


def git_commit():
    """Commit đang chạy, thêm '+dirty' nếu thư mục eval/ có thay đổi chưa commit."""
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                             check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "eval"], cwd=ROOT, capture_output=True,
                               text=True).stdout.strip()
        return sha + ("+dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return None


def prompt_extra(examples="", hints=""):
    """Phần thêm vào sau schema: ví dụ của (C) rồi gợi ý thực thể của (B); "" nếu không có."""
    return "".join("\n\n" + part.strip() for part in (examples, hints) if part and part.strip())


def prompt_head(schema, question, extra=""):
    """Prompt sinh Cypher bỏ chữ "Cypher:" cuối. (D) nối phần sửa lỗi vào sau đây để dùng chung tiền tố."""
    return HEAD.format(schema=schema + extra, question=question)


def build(model, off=frozenset()):
    off = frozenset(off)
    if not off <= COMPONENTS:
        raise ValueError(f"off chỉ gồm các thành phần {sorted(COMPONENTS)}, nhận {sorted(off)}")

    driver = GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF")
    schema = build_schema(driver) if "A" in off else detailed_schema(driver)
    session = None
    if "D" not in off:
        session = driver.session(default_access_mode=READ_ACCESS)   # chạy thử khi sửa; đóng khi tiến trình kết thúc
    elif "B" in off:
        driver.close()

    def generate(question):
        examples, example_ids, hints = "", [], ""
        if "C" not in off:
            picked = fewshot_c.select_examples(question)
            examples, example_ids = fewshot_c.format_examples(picked), [ex["id"] for ex in picked]
        if "B" not in off:
            hints = entity_link.format_hints(session if session is not None else driver, question)
        extra = prompt_extra(examples, hints)
        head = prompt_head(schema, question, extra)
        cypher = extract_cypher(groq_chat(model, head + "Cypher:"))
        info = {"llm_calls": 1, "first_cypher": cypher, "prompt_extra": extra, "examples_c": example_ids}
        if session is not None:
            cypher, d = repair_d.repair(model, session, head, cypher)
            fix_calls = d.pop("fix_calls")
            info = info | d | {"llm_calls": 1 + fix_calls}
        generate.last_info = info
        return cypher

    generate.last_info = None
    generate.meta = {"prompt": HEAD + "Cypher:", "schema": schema,
                     "schema_sha256": hashlib.sha256(schema.encode("utf-8")).hexdigest(),
                     "off": sorted(off), "components": sorted(COMPONENTS - off), "commit": git_commit()}
    if "C" not in off:
        generate.meta |= {"fewshot_k": fewshot_c.DEFAULT_K, "fewshot_strategy": "bm25, diverse",
                          "fewshot_bank": "eval/questions/dev.json"}
    if session is not None:
        generate.meta |= {"fix_prompt_tail": repair_d.FIX_TAIL, "fix_instructions": repair_d.INSTRUCTIONS,
                          "max_fixes": repair_d.MAX_FIXES, "fix_llm_options": repair_d.llm_options(model)}
    return generate
