"""B2 (openai/gpt-oss-20b) – LangChain GraphCypherQAChain sinh Cypher qua Groq.

T24:
- Trích xuất schema đầy đủ cho cả node đa nhãn (Place/City/Country, Organisation/University/Company, Message/Post/Comment).
- Giữ cấu hình mặc định của GraphCypherQAChain (validate_cypher=False, không sửa CYPHER_GENERATION_PROMPT).
- Tôn trọng retry-after và DailyLimitError để không nuốt lỗi mạng/rate-limit thành chuỗi rỗng (no_cypher).
"""
import hashlib
import re
import time

import groq
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_neo4j.chains.graph_qa.cypher import extract_cypher as lc_extract_cypher
from langchain_neo4j.chains.graph_qa.prompts import CYPHER_GENERATION_PROMPT
from neo4j import GraphDatabase
from neo4j_graphrag.schema import format_schema

from llm import DailyLimitError, retry_after
from pilot_text2cypher import AUTH, URI, extract_cypher

MAX_RETRIES = 5
RETRYABLE = (groq.RateLimitError, groq.InternalServerError, groq.APIConnectionError)


def _clean_cypher(text: str) -> str:
    """Tách câu Cypher từ output thô của chain: dùng bộ tách LangChain + chuẩn hóa rỗng/tiền tố."""
    extracted = lc_extract_cypher(text or "")
    cypher = extract_cypher(extracted)
    cypher = re.sub(r"^\s*cypher\s*:\s*", "", cypher, flags=re.I)
    return cypher.strip().rstrip(";")


def _build_structured_schema(driver) -> dict:
    """Trích xuất structured_schema từ Neo4j không phụ thuộc APOC, giữ đủ mọi nhãn trên node đa nhãn."""
    rn, _, _ = driver.execute_query(
        "CALL db.schema.nodeTypeProperties() YIELD nodeLabels, propertyName, propertyTypes "
        "UNWIND nodeLabels AS label "
        "WITH label, propertyName, propertyTypes WHERE propertyName IS NOT NULL "
        "RETURN label, collect(DISTINCT {property: propertyName, type: propertyTypes[0]}) AS props"
    )
    node_props = {r["label"]: r["props"] for r in rn if r["label"]}

    rp, _, _ = driver.execute_query(
        "CALL db.schema.relTypeProperties() YIELD relType, propertyName, propertyTypes "
        "WITH substring(relType, 2, size(relType)-3) AS rel, propertyName, propertyTypes "
        "WHERE propertyName IS NOT NULL "
        "RETURN rel, collect(DISTINCT {property: propertyName, type: propertyTypes[0]}) AS props"
    )
    rel_props = {r["rel"]: r["props"] for r in rp if r["rel"]}

    rr, _, _ = driver.execute_query(
        "MATCH (a)-[r]->(b) "
        "WITH DISTINCT labels(a) AS la, type(r) AS type, labels(b) AS lb "
        "UNWIND la AS start UNWIND lb AS end "
        "RETURN DISTINCT start, type, end"
    )
    relationships = [{"start": r["start"], "type": r["type"], "end": r["end"]} for r in rr]
    return {"node_props": node_props, "rel_props": rel_props, "relationships": relationships}


def build(model):
    load_dotenv()
    with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as driver:
        structured_schema = _build_structured_schema(driver)

    graph = Neo4jGraph(
        url=URI,
        username=AUTH[0],
        password=AUTH[1],
        refresh_schema=False,
        sanitize=True,
    )
    graph.structured_schema = structured_schema
    graph.schema = format_schema(structured_schema, False)

    # Giữ cấu hình mặc định của GraphCypherQAChain (validate_cypher=False, prompt mặc định)
    llm = ChatGroq(model=model, temperature=0, max_retries=0)
    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        allow_dangerous_requests=True,
    )

    def generate(question):
        for attempt in range(MAX_RETRIES + 1):
            try:
                raw_cypher = chain.cypher_generation_chain.invoke({
                    "question": question,
                    "schema": chain.graph_schema,
                    "examples": "",
                })
                break
            except RETRYABLE as e:
                if "per day" in str(e).lower():
                    raise DailyLimitError(str(e)) from e
                if attempt == MAX_RETRIES:
                    raise
                wait = retry_after(e) or 15 * (attempt + 1)
                print(f"    Groq {type(e).__name__}, chờ {wait}s ({attempt + 1}/{MAX_RETRIES})...", flush=True)
                time.sleep(wait)
        return _clean_cypher(raw_cypher)

    generate.meta = {
        "baseline": "b2_langchain",
        "model": model,
        "validate_cypher": False,
        "prompt": CYPHER_GENERATION_PROMPT.template,
        "schema": chain.graph_schema,
        "schema_sha256": hashlib.sha256(chain.graph_schema.encode("utf-8")).hexdigest(),
    }
    return generate
