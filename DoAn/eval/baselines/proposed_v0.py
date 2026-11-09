"""Proposed v0 – bản thử cho kết quả sơ bộ giữa kỳ: model của B1 + (A) schema kèm quy ước + (D) tự sửa lỗi.

(A) Thêm vào prompt các quy ước của đồ thị (KNOWS không xét chiều, chiều các cạnh, tên dùng dấu _, so khớp họ tên
    đầy đủ, thành phần ngày giờ) và vài giá trị mẫu lấy từ Neo4j, bỏ mọi giá trị là tham số của câu hỏi dev/test.
(D) Chạy thử câu Cypher (chỉ đọc, timeout 30 s); nếu lỗi, không sinh được, rỗng, chỉ ra 0/null hoặc trả về nguyên
    node thì gửi đúng vấn đề đó cho LLM sửa, tối đa 2 lần. Không bao giờ dùng đáp án gold.
Chưa có (B) liên kết thực thể và (C) few-shot. Chỉ chạy trên dev; module chính thức của từng thành phần làm sau.
"""
import hashlib
import json
from pathlib import Path

from neo4j import READ_ACCESS, GraphDatabase, Query
from neo4j.exceptions import Neo4jError
from neo4j.graph import Node

from llm import groq_chat
from pilot_text2cypher import AUTH, URI, build_schema, extract_cypher

QDIR = Path(__file__).resolve().parent.parent / "questions"
MAX_FIXES = 2
TIMEOUT_S = 30
SAMPLE_LABELS = ["Country", "City", "Tag", "Company", "University"]

CONVENTIONS = """Conventions of this graph:
- KNOWS (friendship) is stored once per pair, in an arbitrary direction: always match it without a direction, e.g. (a)-[:KNOWS]-(b), (a)-[:KNOWS*1..2]-(b), shortestPath((a)-[:KNOWS*]-(b)).
- Use every other relationship in the direction shown in the schema, e.g. (:Forum)-[:HAS_MEMBER]->(:Person), (:Message)-[:HAS_CREATOR]->(:Person), (:Person)-[:IS_LOCATED_IN]->(:City)-[:IS_PART_OF]->(:Country).
- Names of countries, cities, companies, universities, tags and tag classes use underscores instead of spaces, e.g. {samples}.
- A person's firstName may contain several words. To match a full name from the question, compare p.firstName + ' ' + p.lastName with the full name.
- creationDate, joinDate and other date-time values have components .year, .month, .quarter (e.g. m.creationDate.year = 2011); Cypher has no year() function.
- Person.creationDate is when the person joined the network; HAS_MEMBER.joinDate is when a person joined a forum.
- Return property values (e.g. u.name, p.firstName, p.lastName), never whole nodes."""

PROMPT = """You are an expert Neo4j developer. Write one Cypher query that answers the question
using only the graph schema below. Return only the Cypher query, with no explanation.

Schema:
{schema}

{conventions}

Question: {question}
Cypher:"""

FIX_PROMPT = """You are an expert Neo4j developer. A Cypher query written for the question below has a problem.
Write a corrected Cypher query using only the graph schema below. Return only the Cypher query, with no explanation.

Schema:
{schema}

{conventions}

Question: {question}
Previous query:
{cypher}
Problem: {problem}
Cypher:"""


def sample_names(driver):
    """Một tên có dấu _ cho mỗi nhãn, không trùng tham số nào của câu hỏi dev/test (tránh rò rỉ đáp án)."""
    banned = {str(v) for split in ("dev", "test")
              for q in json.loads((QDIR / f"{split}.json").read_text(encoding="utf-8")) for v in q["params"].values()}
    out = []
    for label in SAMPLE_LABELS:
        records, _, _ = driver.execute_query(
            f"MATCH (n:{label}) WHERE n.name CONTAINS '_' RETURN n.name AS name ORDER BY n.id LIMIT 30")
        out += [f"'{r['name']}' ({label})" for r in records if r["name"] not in banned][:1]
    return ", ".join(out)


def check(session, cypher):
    """None nếu câu chạy được và ra giá trị; ngược lại là mô tả vấn đề (chỉ dựa vào kết quả chạy, không dùng gold)."""
    if not cypher:
        return "No query was produced."
    try:
        result = session.run(Query(cypher, timeout=TIMEOUT_S))
        records = result.fetch(1)
        result.consume()
    except Neo4jError as e:
        lines = (e.message or "").strip().splitlines()
        return f"The query failed with error: {lines[0][:300] if lines else e.code}"
    if not records:
        return "The query returned no rows, which usually means a name, label or relationship direction did not match."
    values = list(records[0].values())
    if any(isinstance(v, Node) for v in values):
        return "The query returns whole nodes; return property values instead."
    if all(v in (0, None) for v in values):
        return "The query returned only 0 or null, which usually means a name, label or relationship direction did not match."
    return None


def build(model):
    driver = GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF")
    schema = build_schema(driver)
    conventions = CONVENTIONS.format(samples=sample_names(driver))
    session = driver.session(default_access_mode=READ_ACCESS)  # chạy thử khi tự sửa lỗi; đóng khi tiến trình kết thúc

    def generate(question):
        cypher = extract_cypher(groq_chat(model, PROMPT.format(schema=schema, conventions=conventions,
                                                               question=question)))
        problems = []
        for _ in range(MAX_FIXES):
            problem = check(session, cypher)
            if problem is None:
                break
            problems.append(problem)
            cypher = extract_cypher(groq_chat(model, FIX_PROMPT.format(
                schema=schema, conventions=conventions, question=question, cypher=cypher or "(none)",
                problem=problem)))
        generate.last_info = {"llm_calls": 1 + len(problems), "problems": problems}
        return cypher

    generate.meta = {"prompt": PROMPT, "fix_prompt": FIX_PROMPT, "conventions": conventions, "schema": schema,
                     "schema_sha256": hashlib.sha256(schema.encode("utf-8")).hexdigest(), "max_fixes": MAX_FIXES}
    return generate
