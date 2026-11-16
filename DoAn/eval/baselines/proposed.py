"""Hệ thống đề xuất: (A) schema chi tiết, (B) liên kết thực thể, (C) few-shot động, (D) tự sửa lỗi.

build(model, off=frozenset()): off ⊆ {"A", "B", "C", "D"} là các thành phần bị tắt (GIAO_VIEC_CUOI_KY.md mục 5.1).
- (A) tắt: schema cơ bản của B1 (build_schema). Bật: proposed/schema_a.detailed_schema (Khôi, T31).
- (B) liên kết thực thể bằng full-text index: proposed/entity_link (Ân, T32).
- (C): CHƯA tích hợp, chờ proposed/fewshot_c.py (Vũ, T33) – việc của T35. Bật C thì build báo NotImplementedError.
- (D) tắt: không sửa. Bật: proposed/repair_d (Bằng, T34).

Prompt sinh Cypher chỉ nằm ở file này: đúng khung PROMPT của B1, chỉ thay khối schema và bổ sung gợi ý thực thể.
Vì vậy khi tắt B, C, D, cấu hình chỉ khác B1 ở (A). Prompt sửa lỗi và prompt trả lời nằm trong proposed/repair_d.py.
Mỗi cấu hình là một module mỏng có tên riêng (cache riêng), vd. baselines/proposed_ad.py = A + D.
generate.last_info: llm_calls, first_cypher (Cypher trước khi sửa) và, khi bật (D), thông tin vòng sửa.
"""
import hashlib
import subprocess
from pathlib import Path

from neo4j import READ_ACCESS, GraphDatabase

from llm import groq_chat
from pilot_text2cypher import AUTH, URI, build_schema, extract_cypher
from pilot_text2cypher import PROMPT as B1_PROMPT
from proposed import entity_link, repair_d
from proposed.schema_a import detailed_schema

ROOT = Path(__file__).resolve().parents[2]
COMPONENTS = frozenset("ABCD")
NOT_INTEGRATED = {"C": "proposed/fewshot_c.py (Vũ, T33)"}
HEAD = B1_PROMPT.removesuffix("Cypher:")   # "...Schema:\n{schema}\n\nQuestion: {question}\n"
assert HEAD != B1_PROMPT, "PROMPT của B1 phải kết thúc bằng 'Cypher:'"


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


def build(model, off=frozenset()):
    off = frozenset(off)
    if not off <= COMPONENTS:
        raise ValueError(f"off chỉ gồm các thành phần {sorted(COMPONENTS)}, nhận {sorted(off)}")
    missing = [f"({c}) {NOT_INTEGRATED[c]}" for c in sorted(set(NOT_INTEGRATED) - off)]
    if missing:
        raise NotImplementedError("Chưa tích hợp: " + ", ".join(missing) + ". Hãy tắt chúng trong off.")

    driver = GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF")
    schema = build_schema(driver) if "A" in off else detailed_schema(driver)
    session = None
    if "D" not in off:
        session = driver.session(default_access_mode=READ_ACCESS)   # chạy thử khi sửa; đóng khi tiến trình kết thúc
    elif "B" in off:
        driver.close()

    def generate(question):
        hints_b = ""
        if "B" not in off:
            hints_b = entity_link.format_hints(session if session is not None else driver, question)
        schema_block = schema + ("\n\n" + hints_b.strip() if hints_b else "")
        head = HEAD.format(schema=schema_block, question=question)
        cypher = extract_cypher(groq_chat(model, head + "Cypher:"))
        info = {"llm_calls": 1, "first_cypher": cypher}
        if session is not None:
            cypher, d = repair_d.repair(model, session, head, cypher)
            info = {"llm_calls": 1 + d.pop("fix_calls")} | d
        generate.last_info = info
        return cypher

    generate.last_info = None
    generate.meta = {"prompt": HEAD + "Cypher:", "schema": schema,
                     "schema_sha256": hashlib.sha256(schema.encode("utf-8")).hexdigest(),
                     "off": sorted(off), "components": sorted(COMPONENTS - off), "commit": git_commit()}
    if session is not None:
        generate.meta |= {"fix_prompt_tail": repair_d.FIX_TAIL, "fix_instructions": repair_d.INSTRUCTIONS,
                          "max_fixes": repair_d.MAX_FIXES, "fix_llm_options": repair_d.llm_options(model)}
    return generate
