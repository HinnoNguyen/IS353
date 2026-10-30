"""B0 – Template/rule-based: nhận diện ý định bằng từ khóa/regex + điền tham số vào mẫu Cypher.

Quy tắc chống rò rỉ dữ liệu (QA_GUIDELINE.md mục 7, GIAO_VIEC_CHUNG.md mục 2):
Luật CHỈ được viết dựa trên 10 template của tập dev (dev.json).
Không sử dụng LLM. Khi câu hỏi không khớp bất kỳ luật nào của 10 template dev, trả về chuỗi rỗng ("").
"""
import re
from pathlib import Path
from neo4j import GraphDatabase

from pilot_text2cypher import AUTH, URI

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
}

QUARTERS = {
    "first": 1, "1st": 1, "1": 1,
    "second": 2, "2nd": 2, "2": 2,
    "third": 3, "3rd": 3, "3": 3,
    "fourth": 4, "4th": 4, "4": 4
}


def build(model=None):
    # Nạp danh bạ thực thể từ đồ thị tĩnh để chuẩn hóa thực thể chính xác
    with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as driver:
        records_p, _, _ = driver.execute_query("MATCH (p:Person) RETURN p.firstName AS f, p.lastName AS l")
        persons = {f"{r['f']} {r['l']}".strip().lower(): (r['f'], r['l']) for r in records_p}

        records_c, _, _ = driver.execute_query("MATCH (c:Country) RETURN c.name AS name")
        countries = {r['name'].replace('_', ' ').lower(): r['name'] for r in records_c}
        for r in records_c:
            countries[r['name'].lower()] = r['name']

        records_t, _, _ = driver.execute_query("MATCH (t:Tag) RETURN t.name AS name")
        tags = {r['name'].replace('_', ' ').lower(): r['name'] for r in records_t}
        for r in records_t:
            tags[r['name'].lower()] = r['name']

    def resolve_person(name_str):
        name = name_str.strip().rstrip("?.,")
        if name.lower() in persons:
            return persons[name.lower()]
        parts = name.rsplit(" ", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return name, ""

    def resolve_country(c_str):
        c = c_str.strip().rstrip("?.,")
        return countries.get(c.lower(), c.replace(" ", "_"))

    def resolve_tag(t_str):
        t = t_str.strip().strip('"').strip("'").rstrip("?.,")
        return tags.get(t.lower(), t.replace(" ", "_"))

    def generate(question):
        q = question.strip().rstrip("?.,") + "?"

        # 1. LK-03: University attend/student/study at
        m = re.search(r"(?:What|Which) university does (.*?) attend\?", q, re.I) or \
            re.search(r"At which university is (.*?) a student\?", q, re.I) or \
            re.search(r"Which university did (.*?) study at\?", q, re.I)
        if m:
            f, l = resolve_person(m.group(1))
            return f"MATCH (:Person {{firstName: '{f}', lastName: '{l}'}})-[:STUDY_AT]->(u:University) RETURN u.name"

        # 2. LK-04: Birthday / born
        m = re.search(r"When was (.*?) born\?", q, re.I) or \
            re.search(r"What is the date of birth of (.*?)\?", q, re.I) or \
            re.search(r"What is (.*?)'s birthday\?", q, re.I)
        if m:
            f, l = resolve_person(m.group(1))
            return f"MATCH (p:Person {{firstName: '{f}', lastName: '{l}'}}) RETURN p.birthday"

        # 3. AG-01: How many people live in Country
        m = re.search(r"How many people live in (.*?)\?", q, re.I) or \
            re.search(r"What is the number of people living in (.*?)\?", q, re.I) or \
            re.search(r"How many residents of (.*?) are there in the network\?", q, re.I)
        if m:
            co = resolve_country(m.group(1))
            return f"MATCH (p:Person)-[:IS_LOCATED_IN]->(:City)-[:IS_PART_OF]->(:Country {{name: '{co}'}}) RETURN count(DISTINCT p) AS total"

        # 4. AG-03: Posts tagged with Tag
        m = re.search(r"How many posts are tagged with [\"\']?(.*?)[\"\']?\?", q, re.I) or \
            re.search(r"What is the number of posts that have the tag [\"\']?(.*?)[\"\']?\?", q, re.I) or \
            re.search(r"How many posts carry the tag [\"\']?(.*?)[\"\']?\?", q, re.I)
        if m:
            t = resolve_tag(m.group(1))
            return f"MATCH (p:Post)-[:HAS_TAG]->(:Tag {{name: '{t}'}}) RETURN count(DISTINCT p) AS total"

        # 5. MH-01: Which country does Person live in
        m = re.search(r"Which country does (.*?) live in\?", q, re.I) or \
            re.search(r"In what country is (.*?) based\?", q, re.I) or \
            re.search(r"(.*?) lives in which country\?", q, re.I)
        if m:
            f, l = resolve_person(m.group(1))
            return f"MATCH (:Person {{firstName: '{f}', lastName: '{l}'}})-[:IS_LOCATED_IN]->(:City)-[:IS_PART_OF]->(k:Country) RETURN k.name"

        # 6. MH-03: Friends live in same city as Person
        m = re.search(r"Which friends of (.*?) live in the same city as (?:them|(?:\1))\?", q, re.I) or \
            re.search(r"Who among (.*?)'s friends lives in the same city as them\?", q, re.I) or \
            re.search(r"List the friends of (.*?) who share their city of residence\?", q, re.I)
        if m:
            f, l = resolve_person(m.group(1))
            return f"MATCH (p:Person {{firstName: '{f}', lastName: '{l}'}})-[:IS_LOCATED_IN]->(c:City)<-[:IS_LOCATED_IN]-(f:Person)-[:KNOWS]-(p) RETURN DISTINCT f.firstName, f.lastName"

        # 7. PA-01: Shortest friendship path between Person1 and Person2
        m = re.search(r"length of the shortest friendship path between (.*?) and (.*?)\?", q, re.I) or \
            re.search(r"friendship steps separate (.*?) from (.*?)\?", q, re.I) or \
            re.search(r"minimum number of friendship links needed to connect (.*?) and (.*?)\?", q, re.I)
        if m:
            f1, l1 = resolve_person(m.group(1))
            f2, l2 = resolve_person(m.group(2))
            return f"MATCH (a:Person {{firstName: '{f1}', lastName: '{l1}'}}), (b:Person {{firstName: '{f2}', lastName: '{l2}'}}) MATCH p = shortestPath((a)-[:KNOWS*]-(b)) RETURN length(p)"

        # 8. PA-03: Mutual / Common friends
        m = re.search(r"mutual friends of (.*?) and (.*?)\?", q, re.I) or \
            re.search(r"friends with both (.*?) and (.*?)\?", q, re.I) or \
            re.search(r"common friends of (.*?) and (.*?)\?", q, re.I)
        if m:
            f1, l1 = resolve_person(m.group(1))
            f2, l2 = resolve_person(m.group(2))
            return f"MATCH (:Person {{firstName: '{f1}', lastName: '{l1}'}})-[:KNOWS]-(m:Person)-[:KNOWS]-(:Person {{firstName: '{f2}', lastName: '{l2}'}}) RETURN DISTINCT m.firstName, m.lastName"

        # 9. TM-02: Joined network in Month Year
        m = re.search(r"(?:people joined the network|accounts were created|people who signed up) in ([A-Za-z]+)\s+(\d{4})\?", q, re.I)
        if m:
            month_name = m.group(1).lower()
            year = int(m.group(2))
            month = MONTHS.get(month_name, 1)
            return f"MATCH (p:Person) WHERE p.creationDate.year = {year} AND p.creationDate.month = {month} RETURN count(p)"

        # 10. TM-04: Comments by Person in Quarter of Year
        m = re.search(r"comments did (.*?) write in the ([A-Za-z0-9]+) quarter of (\d{4})\?", q, re.I) or \
            re.search(r"In the ([A-Za-z0-9]+) quarter of (\d{4}), how many comments did (.*?) make\?", q, re.I) or \
            re.search(r"comments (.*?) wrote during Q(\d)\s+(\d{4})\?", q, re.I)
        if m:
            if len(m.groups()) == 3:
                if m.group(2).lower() in QUARTERS:
                    p_name, q_str, year = m.group(1), m.group(2), int(m.group(3))
                elif m.group(1).lower() in QUARTERS:
                    q_str, year, p_name = m.group(1), int(m.group(2)), m.group(3)
                else:
                    p_name, q_str, year = m.group(1), m.group(2), int(m.group(3))
            f, l = resolve_person(p_name)
            quarter = QUARTERS.get(q_str.lower(), 1)
            return f"MATCH (:Person {{firstName: '{f}', lastName: '{l}'}})<-[:HAS_CREATOR]-(c:Comment) WHERE c.creationDate.year = {year} AND c.creationDate.quarter = {quarter} RETURN count(DISTINCT c)"

        return ""

    generate.meta = {
        "baseline": "b0_rulebased",
        "description": "Rule-based regex template matching strictly designed on dev.json (10 templates)",
        "model": "none"
    }
    return generate
