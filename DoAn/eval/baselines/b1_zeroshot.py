"""B1 (llama-3.1-8b-instant) và B3 (model lớn hơn, chỉ đổi --model): LLM zero-shot sinh Cypher qua Groq.

Dùng nguyên PROMPT, build_schema, extract_cypher của pilot_text2cypher.py.
"""
import hashlib

from neo4j import GraphDatabase

from llm import groq_chat
from pilot_text2cypher import AUTH, PROMPT, URI, build_schema, extract_cypher


def build(model):
    with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as driver:
        schema = build_schema(driver)

    def generate(question):
        return extract_cypher(groq_chat(model, PROMPT.format(schema=schema, question=question)))

    generate.meta = {"prompt": PROMPT, "schema": schema,
                     "schema_sha256": hashlib.sha256(schema.encode("utf-8")).hexdigest()}
    return generate
