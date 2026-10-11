"""Nạp LDBC SNB (CsvComposite + LongDateFormatter) vào Neo4j.

Chạy:  python scripts/load_ldbc.py
Mặc định: bolt://localhost:7687, user neo4j / graphqa123, dữ liệu SF0.1 trong data/.
Script xóa sạch database trước khi nạp nên chạy lại bao nhiêu lần cũng được.
"""
import csv
import os
import sys
import time
from pathlib import Path

from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("LDBC_DIR", ROOT / "data" / "social_network-sf0.1-CsvComposite-LongDateFormatter"))
URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "graphqa123"))
BATCH = 5000

csv.field_size_limit(sys.maxsize if sys.maxsize < 2**31 else 2**31 - 1)


def read_rows(rel_path):
    """Đọc file CSV phân cách '|'. Trả về list các dòng (list chuỗi), bỏ header."""
    with open(DATA_DIR / rel_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter="|", quoting=csv.QUOTE_NONE)
        next(reader)
        return list(reader)


def run_batches(session, query, rows):
    for i in range(0, len(rows), BATCH):
        session.run(query, rows=rows[i:i + BATCH]).consume()


def ms(value):
    return int(value) if value else None


def split_list(value):
    return value.split(";") if value else []


# ---------- Nodes ----------
# (file, câu Cypher, hàm chuyển 1 dòng CSV -> dict); "{label}" được thay bằng nhãn phụ
NODES = [
    ("static/place_0_0.csv",
     "UNWIND $rows AS r CREATE (:Place:{label} {{id: r.id, name: r.name, url: r.url}})",
     lambda r: {"id": int(r[0]), "name": r[1], "url": r[2], "label": r[3].capitalize()}),
    ("static/organisation_0_0.csv",
     "UNWIND $rows AS r CREATE (:Organisation:{label} {{id: r.id, name: r.name, url: r.url}})",
     lambda r: {"id": int(r[0]), "label": r[1].capitalize(), "name": r[2], "url": r[3]}),
    ("static/tagclass_0_0.csv",
     "UNWIND $rows AS r CREATE (:TagClass {id: r.id, name: r.name, url: r.url})",
     lambda r: {"id": int(r[0]), "name": r[1], "url": r[2]}),
    ("static/tag_0_0.csv",
     "UNWIND $rows AS r CREATE (:Tag {id: r.id, name: r.name, url: r.url})",
     lambda r: {"id": int(r[0]), "name": r[1], "url": r[2]}),
    ("dynamic/person_0_0.csv",
     """UNWIND $rows AS r CREATE (:Person {
            id: r.id, firstName: r.firstName, lastName: r.lastName, gender: r.gender,
            birthday: date(datetime({epochMillis: r.birthday})),
            creationDate: datetime({epochMillis: r.creationDate}),
            locationIP: r.locationIP, browserUsed: r.browserUsed,
            speaks: r.speaks, email: r.email})""",
     lambda r: {"id": int(r[0]), "firstName": r[1], "lastName": r[2], "gender": r[3],
                "birthday": ms(r[4]), "creationDate": ms(r[5]), "locationIP": r[6],
                "browserUsed": r[7], "speaks": split_list(r[8]), "email": split_list(r[9])}),
    ("dynamic/forum_0_0.csv",
     "UNWIND $rows AS r CREATE (:Forum {id: r.id, title: r.title, creationDate: datetime({epochMillis: r.creationDate})})",
     lambda r: {"id": int(r[0]), "title": r[1], "creationDate": ms(r[2])}),
    ("dynamic/post_0_0.csv",
     """UNWIND $rows AS r CREATE (p:Post:Message {
            id: r.id, creationDate: datetime({epochMillis: r.creationDate}),
            locationIP: r.locationIP, browserUsed: r.browserUsed, length: r.length})
        SET p.imageFile = r.imageFile, p.language = r.language, p.content = r.content""",
     lambda r: {"id": int(r[0]), "imageFile": r[1] or None, "creationDate": ms(r[2]),
                "locationIP": r[3], "browserUsed": r[4], "language": r[5] or None,
                "content": r[6] or None, "length": int(r[7])}),
    ("dynamic/comment_0_0.csv",
     """UNWIND $rows AS r CREATE (:Comment:Message {
            id: r.id, creationDate: datetime({epochMillis: r.creationDate}),
            locationIP: r.locationIP, browserUsed: r.browserUsed, content: r.content, length: r.length})""",
     lambda r: {"id": int(r[0]), "creationDate": ms(r[1]), "locationIP": r[2],
                "browserUsed": r[3], "content": r[4], "length": int(r[5])}),
]

# ---------- Relationships ----------
# (file, nhãn nguồn, kiểu quan hệ, nhãn đích, tên thuộc tính ở cột thứ 3 hoặc None, có phải ngày không)
RELS = [
    ("static/place_isPartOf_place_0_0.csv", "Place", "IS_PART_OF", "Place", None, False),
    ("static/organisation_isLocatedIn_place_0_0.csv", "Organisation", "IS_LOCATED_IN", "Place", None, False),
    ("static/tag_hasType_tagclass_0_0.csv", "Tag", "HAS_TYPE", "TagClass", None, False),
    ("static/tagclass_isSubclassOf_tagclass_0_0.csv", "TagClass", "IS_SUBCLASS_OF", "TagClass", None, False),
    ("dynamic/person_isLocatedIn_place_0_0.csv", "Person", "IS_LOCATED_IN", "Place", None, False),
    ("dynamic/person_knows_person_0_0.csv", "Person", "KNOWS", "Person", "creationDate", True),
    ("dynamic/person_hasInterest_tag_0_0.csv", "Person", "HAS_INTEREST", "Tag", None, False),
    ("dynamic/person_studyAt_organisation_0_0.csv", "Person", "STUDY_AT", "Organisation", "classYear", False),
    ("dynamic/person_workAt_organisation_0_0.csv", "Person", "WORK_AT", "Organisation", "workFrom", False),
    ("dynamic/person_likes_post_0_0.csv", "Person", "LIKES", "Post", "creationDate", True),
    ("dynamic/person_likes_comment_0_0.csv", "Person", "LIKES", "Comment", "creationDate", True),
    ("dynamic/forum_hasModerator_person_0_0.csv", "Forum", "HAS_MODERATOR", "Person", None, False),
    ("dynamic/forum_hasMember_person_0_0.csv", "Forum", "HAS_MEMBER", "Person", "joinDate", True),
    ("dynamic/forum_hasTag_tag_0_0.csv", "Forum", "HAS_TAG", "Tag", None, False),
    ("dynamic/forum_containerOf_post_0_0.csv", "Forum", "CONTAINER_OF", "Post", None, False),
    ("dynamic/post_hasCreator_person_0_0.csv", "Post", "HAS_CREATOR", "Person", None, False),
    ("dynamic/post_hasTag_tag_0_0.csv", "Post", "HAS_TAG", "Tag", None, False),
    ("dynamic/post_isLocatedIn_place_0_0.csv", "Post", "IS_LOCATED_IN", "Place", None, False),
    ("dynamic/comment_hasCreator_person_0_0.csv", "Comment", "HAS_CREATOR", "Person", None, False),
    ("dynamic/comment_hasTag_tag_0_0.csv", "Comment", "HAS_TAG", "Tag", None, False),
    ("dynamic/comment_isLocatedIn_place_0_0.csv", "Comment", "IS_LOCATED_IN", "Place", None, False),
    ("dynamic/comment_replyOf_post_0_0.csv", "Comment", "REPLY_OF", "Post", None, False),
    ("dynamic/comment_replyOf_comment_0_0.csv", "Comment", "REPLY_OF", "Comment", None, False),
]

LABELS_WITH_ID = ["Place", "Organisation", "TagClass", "Tag", "Person", "Forum", "Post", "Comment"]


def rel_query(src, rel, dst, prop, is_date):
    set_clause = ""
    if prop:
        value = "datetime({epochMillis: r.p})" if is_date else "r.p"
        set_clause = f" SET x.{prop} = {value}"
    return (f"UNWIND $rows AS r MATCH (a:{src} {{id: r.a}}) MATCH (b:{dst} {{id: r.b}}) "
            f"CREATE (a)-[x:{rel}]->(b){set_clause}")


def main():
    driver = GraphDatabase.driver(URI, auth=AUTH)
    driver.verify_connectivity()
    start = time.time()
    with driver.session() as s:
        print("Xóa dữ liệu cũ...")
        s.run("MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS").consume()
        for label in LABELS_WITH_ID:
            s.run(f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE").consume()
        s.run("CREATE INDEX person_name IF NOT EXISTS FOR (p:Person) ON (p.firstName, p.lastName)").consume()
        s.run("CREATE INDEX place_name IF NOT EXISTS FOR (p:Place) ON (p.name)").consume()
        s.run("CREATE INDEX tag_name IF NOT EXISTS FOR (t:Tag) ON (t.name)").consume()
        s.run("CALL db.awaitIndexes()").consume()

        for path, query, convert in NODES:
            rows = [convert(r) for r in read_rows(path)]
            if "{label}" in query:
                # Place (City/Country/Continent) và Organisation (Company/University) có nhãn phụ theo cột type
                for label in sorted({r["label"] for r in rows}):
                    run_batches(s, query.format(label=label), [r for r in rows if r["label"] == label])
            else:
                run_batches(s, query, rows)
            print(f"  node  {path:<50} {len(rows):>8,}")

        for path, src, rel, dst, prop, is_date in RELS:
            rows = []
            for r in read_rows(path):
                row = {"a": int(r[0]), "b": int(r[1])}
                if prop:
                    row["p"] = int(r[2]) if r[2] else None
                rows.append(row)
            run_batches(s, rel_query(src, rel, dst, prop, is_date), rows)
            print(f"  rel   {path:<50} {len(rows):>8,}")

    driver.close()
    print(f"Xong sau {time.time() - start:.0f}s")


if __name__ == "__main__":
    main()
