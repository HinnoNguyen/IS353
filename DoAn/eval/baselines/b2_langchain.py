"""B2 (openai/gpt-oss-20b) – LangChain GraphCypherQAChain sinh Cypher qua Groq.

Sử dụng chuỗi cypher_generation_chain chuẩn của langchain_neo4j kèm CYPHER_GENERATION_PROMPT.
"""
import hashlib
import os
import time
from dotenv import load_dotenv

from neo4j import GraphDatabase
from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_neo4j.chains.graph_qa.prompts import CYPHER_GENERATION_PROMPT
from langchain_groq import ChatGroq
from neo4j_graphrag.schema import format_schema

from pilot_text2cypher import AUTH, URI, extract_cypher


def build(model):
    load_dotenv()
    # 1. Trích xuất schema từ Neo4j thuần (không phụ thuộc APOC)
    with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as driver:
        records_n, _, _ = driver.execute_query(
            "CALL db.schema.nodeTypeProperties() YIELD nodeLabels, propertyName, propertyTypes "
            "RETURN nodeLabels[0] AS label, collect({property: propertyName, type: propertyTypes[0]}) AS props"
        )
        node_props = {r["label"]: r["props"] for r in records_n if r["label"]}

        records_rp, _, _ = driver.execute_query(
            "CALL db.schema.relTypeProperties() YIELD relType, propertyName, propertyTypes "
            "RETURN substring(relType, 2, size(relType)-3) AS rel, collect({property: propertyName, type: propertyTypes[0]}) AS props"
        )
        rel_props = {r["rel"]: r["props"] for r in records_rp if r["rel"]}

        records_r, _, _ = driver.execute_query(
            "MATCH (a)-[r]->(b) "
            "WITH DISTINCT labels(a)[0] AS start, type(r) AS type, labels(b)[0] AS end "
            "RETURN start, type, end"
        )
        relationships = [{"start": r["start"], "type": r["type"], "end": r["end"]} for r in records_r]

    structured_schema = {
        "node_props": node_props,
        "rel_props": rel_props,
        "relationships": relationships,
    }

    # 2. Khởi tạo Neo4jGraph và gán schema
    graph = Neo4jGraph(
        url=URI,
        username=AUTH[0],
        password=AUTH[1],
        refresh_schema=False,
        sanitize=True
    )
    graph.structured_schema = structured_schema
    graph.schema = format_schema(structured_schema, False)

    # 3. Khởi tạo ChatGroq và GraphCypherQAChain
    llm = ChatGroq(model=model, temperature=0, max_retries=4)
    chain = GraphCypherQAChain.from_llm(
        llm=llm,
        graph=graph,
        allow_dangerous_requests=True,
        validate_cypher=True
    )

    def generate(question):
        raw_cypher = ""
        for attempt in range(8):
            try:
                raw_cypher = chain.cypher_generation_chain.invoke({
                    "question": question,
                    "schema": chain.graph_schema,
                    "examples": ""
                })
                break
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower() or "limit" in str(e).lower():
                    time.sleep(15)
                    continue
                if attempt < 7:
                    time.sleep(5)
                    continue
                raise e
        if raw_cypher and chain.cypher_query_corrector:
            raw_cypher = chain.cypher_query_corrector(raw_cypher)
        time.sleep(10.0)
        return extract_cypher(raw_cypher)

    generate.meta = {
        "baseline": "b2_langchain",
        "model": model,
        "prompt": CYPHER_GENERATION_PROMPT.template,
        "schema": chain.graph_schema,
        "schema_sha256": hashlib.sha256(chain.graph_schema.encode("utf-8")).hexdigest()
    }
    return generate
