"""T32 – Tạo full-text indexes trong Neo4j phục vụ Entity Linking (Module B - Ân).

Chạy:
    python scripts/create_fulltext_index.py

Tạo các full-text indexes phục vụ tra cứu nhanh thực thể:
1. person_name_fulltext:        (p:Person) ON EACH [p.firstName, p.lastName]
2. place_name_fulltext:         (p:Place) ON EACH [p.name]  (City, Country, Continent)
3. tag_name_fulltext:           (t:Tag) ON EACH [t.name]
4. tagclass_name_fulltext:      (tc:TagClass) ON EACH [tc.name]
5. organisation_name_fulltext:  (o:Organisation) ON EACH [o.name] (Company, University)
6. forum_title_fulltext:        (f:Forum) ON EACH [f.title]
"""
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "graphqa123"))

FULLTEXT_INDEXES = [
    {
        "name": "person_name_fulltext",
        "query": "CREATE FULLTEXT INDEX person_name_fulltext IF NOT EXISTS FOR (p:Person) ON EACH [p.firstName, p.lastName]",
        "desc": "Person (firstName, lastName)"
    },
    {
        "name": "place_name_fulltext",
        "query": "CREATE FULLTEXT INDEX place_name_fulltext IF NOT EXISTS FOR (p:Place) ON EACH [p.name]",
        "desc": "Place (City, Country, Continent: name)"
    },
    {
        "name": "tag_name_fulltext",
        "query": "CREATE FULLTEXT INDEX tag_name_fulltext IF NOT EXISTS FOR (t:Tag) ON EACH [t.name]",
        "desc": "Tag (name)"
    },
    {
        "name": "tagclass_name_fulltext",
        "query": "CREATE FULLTEXT INDEX tagclass_name_fulltext IF NOT EXISTS FOR (tc:TagClass) ON EACH [tc.name]",
        "desc": "TagClass (name)"
    },
    {
        "name": "organisation_name_fulltext",
        "query": "CREATE FULLTEXT INDEX organisation_name_fulltext IF NOT EXISTS FOR (o:Organisation) ON EACH [o.name]",
        "desc": "Organisation (Company, University: name)"
    },
    {
        "name": "forum_title_fulltext",
        "query": "CREATE FULLTEXT INDEX forum_title_fulltext IF NOT EXISTS FOR (f:Forum) ON EACH [f.title]",
        "desc": "Forum (title)"
    },
]


def create_indexes(driver):
    """Tạo toàn bộ full-text indexes và đợi Neo4j lập chỉ mục xong."""
    created = []
    with driver.session() as s:
        for idx in FULLTEXT_INDEXES:
            print(f"Đang tạo index {idx['name']} cho {idx['desc']}...")
            s.run(idx["query"]).consume()
            created.append(idx["name"])
        print("Đang chờ indexes sẵn sàng (CALL db.awaitIndexes)...")
        s.run("CALL db.awaitIndexes()").consume()
    return created


def list_fulltext_indexes(driver):
    """Liệt kê trạng thái các full-text indexes trong Neo4j."""
    results = []
    with driver.session() as s:
        try:
            records = s.run("SHOW FULLTEXT INDEXES YIELD name, state, populationPercent").data()
            for r in records:
                results.append(r)
        except Exception:
            # Neo4j phiên bản cũ hơn hoặc fallback SHOW INDEXES
            try:
                records = s.run("SHOW INDEXES YIELD name, type, state WHERE type = 'FULLTEXT'").data()
                for r in records:
                    results.append(r)
            except Exception:
                pass
    return results


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"Kết nối tới Neo4j tại {URI}...")
    try:
        driver = GraphDatabase.driver(URI, auth=AUTH)
        driver.verify_connectivity()
    except Exception as e:
        print(f"Không thể kết nối Neo4j: {e}", file=sys.stderr)
        print("Hãy đảm bảo container Neo4j đang chạy trước khi tạo index.", file=sys.stderr)
        sys.exit(1)

    start = time.time()
    create_indexes(driver)
    indexes = list_fulltext_indexes(driver)
    print("\nCác full-text indexes hiện có trong Neo4j:")
    for idx in indexes:
        print(f"  - {idx.get('name')}: state={idx.get('state')}, population={idx.get('populationPercent', 'N/A')}%")
    driver.close()
    print(f"\nHoàn tất sau {time.time() - start:.1f}s.")


if __name__ == "__main__":
    main()
