"""In thống kê đồ thị trong Neo4j (dùng cho mục 3. Data) và lưu ra results/graph_stats.md."""
import os
from pathlib import Path

from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parent.parent
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "graphqa123"))

QUERIES = {
    "Node theo nhãn": "MATCH (n) UNWIND labels(n) AS label RETURN label, count(*) AS count ORDER BY count DESC",
    "Cạnh theo kiểu (nguồn → đích)": """MATCH (a)-[r]->(b)
        RETURN labels(a)[0] + ' -[' + type(r) + ']-> ' + labels(b)[0] AS pattern, count(*) AS count
        ORDER BY count DESC""",
    "Tổng quan": """CALL () { MATCH (n) RETURN count(n) AS nodes }
        CALL () { MATCH ()-[r]->() RETURN count(r) AS edges }
        RETURN nodes, edges""",
    "Mạng bạn bè KNOWS (vô hướng)": """MATCH (p:Person) OPTIONAL MATCH (p)-[:KNOWS]-(f)
        WITH p, count(f) AS deg
        RETURN count(p) AS persons, min(deg) AS min_degree, max(deg) AS max_degree,
               round(avg(deg), 2) AS avg_degree, percentileDisc(deg, 0.5) AS median_degree,
               sum(CASE WHEN deg = 0 THEN 1 ELSE 0 END) AS isolated""",
    "Khoảng thời gian dữ liệu": """MATCH (m:Message)
        RETURN toString(date(min(m.creationDate))) AS first_message, toString(date(max(m.creationDate))) AS last_message""",
    "Top 5 người nhiều bạn nhất": """MATCH (p:Person)-[:KNOWS]-(f)
        RETURN p.firstName + ' ' + p.lastName + ' (id ' + toString(p.id) + ')' AS person, count(f) AS friends
        ORDER BY friends DESC LIMIT 5""",
}


def to_md(records):
    if not records:
        return "(trống)\n"
    keys = list(records[0].keys())
    lines = ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
    for rec in records:
        lines.append("| " + " | ".join(f"{v:,}" if isinstance(v, int) else str(v) for v in rec.values()) + " |")
    return "\n".join(lines) + "\n"


def main():
    out = ["# Thống kê đồ thị LDBC SNB SF0.1 trong Neo4j\n"]
    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        for title, q in QUERIES.items():
            records, _, _ = driver.execute_query(q)
            out.append(f"## {title}\n\n{to_md(records)}")
    text = "\n".join(out)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "graph_stats.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
