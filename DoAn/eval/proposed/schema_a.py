"""T31 – Module (A): Schema chi tiết và quy ước đồ thị bản sạch (Khôi).

Chạy độc lập để kiểm tra nội dung và độ dài token:
    python eval/proposed/schema_a.py

Nguyên tắc chống rò rỉ (GIAO_VIEC_CUOI_KY.md mục 2 & 6.1.1):
1. Mọi quy ước trong file này CHỈ được rút ra từ tài liệu có trước lần chạy test đầu tiên
   (20/10/2026 16:25:45) và từ phân tích lỗi của B1 trên tập dev (92 câu, commit 9aa3d0a).
2. Đã loại bỏ hoàn toàn mệnh đề "Cypher has no year() function" (vốn bị đánh dấu nghi rò rỉ
   trong báo cáo T56 vì tập dev có 0 câu mắc lỗi year()).
3. Không dùng số năm cụ thể (như 2011) làm ví dụ trong quy ước để tránh trùng literal với câu hỏi.
4. Hàm banned_values() chỉ đọc dev.json và test.json cũ, TUYỆT ĐỐI không đọc test2.json
   để đảm bảo prompt hoàn toàn cố định trước và sau khi công bố test2.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "eval") not in sys.path:
    sys.path.insert(0, str(ROOT / "eval"))

from pilot_text2cypher import AUTH, URI, build_schema  # noqa: E402

QDIR = ROOT / "eval" / "questions"
SAMPLE_LABELS = ["Country", "City", "Tag", "TagClass", "Company", "University"]

# Bảng truy vết nguồn gốc từng quy ước (mục 6.1.1: mỗi quy ước kèm nguồn file + commit hoặc id câu dev)
CONVENTION_SOURCES = [
    {
        "id": "C1_KNOWS_UNDIRECTED",
        "rule": (
            "KNOWS (friendship) is stored once per pair in an arbitrary direction: always match it "
            "without a direction, e.g. (a)-[:KNOWS]-(b), (a)-[:KNOWS*2]-(b), "
            "shortestPath((a)-[:KNOWS*]-(b))."
        ),
        "sources": [
            "eval/QA_GUIDELINE.md dòng 23–24, 34 (commit 908f683, 11/10/2026)",
            "README.md dòng 147 (commit 908f683, 11/10/2026)",
            "Dev B1 (commit 9aa3d0a, 20/10 16:25): 10 câu sai chiều KNOWS (MH-03-01, MH-03-05, MH-03-06, MH-03-08, PA-03-03, PA-03-09...)",
        ],
    },
    {
        "id": "C2_DIRECTED_RELATIONS_AND_SUBTYPES",
        "rule": (
            "Use every other relationship in the exact direction shown in the schema, e.g. "
            "(:Forum)-[:HAS_MEMBER]->(:Person), (:Message)-[:HAS_CREATOR]->(:Person), "
            "(:Person)-[:IS_LOCATED_IN]->(:City)-[:IS_PART_OF]->(:Country). "
            "(:Post) and (:Comment) are subtypes of (:Message); use (:Post) for posts, "
            "(:Comment) for comments, and (:Message) when referring to messages in general."
        ),
        "sources": [
            "eval/QA_GUIDELINE.md dòng 25–29 (commit 908f683, 11/10/2026)",
            "results/graph_stats.md bảng 'Node theo nhãn' & 'Cạnh theo kiểu' (commit 908f683, 11/10/2026)",
        ],
    },
    {
        "id": "C3_UNDERSCORE_ENTITY_NAMES",
        "rule": (
            "Names of countries, cities, continents, companies, universities, tags and tag classes "
            "in the database use underscores (_) instead of spaces, e.g. {samples}."
        ),
        "sources": [
            "eval/QA_GUIDELINE.md dòng 36 (commit 908f683, 11/10/2026)",
            "Dev B1 (commit 9aa3d0a, 20/10 16:25): 10 câu sai dấu '_' (AG-01-05, AG-03-01..08, AG-03-10)",
        ],
    },
    {
        "id": "C4_PERSON_FULL_NAME",
        "rule": (
            "A person's firstName may contain spaces (multiple words). Match a person either by "
            "{firstName, lastName} or by comparing p.firstName + ' ' + p.lastName with the full name."
        ),
        "sources": [
            "scripts/stats.py dòng 36 & results/graph_stats.md dòng 72–76 (commit 908f683, 11/10/2026)",
            "Dev B1 (commit 9aa3d0a, 20/10 16:25): lỗi tách tên có từ đệm ở MH-03-01 ('Alfred Sorongo Leakey'), MH-03-06 ('Ernest B Karat')",
        ],
    },
    {
        "id": "C5_TEMPORAL_COMPONENTS",
        "rule": (
            "Date and datetime properties (creationDate, joinDate, birthday) expose UTC components "
            ".year, .month and .quarter directly as integers (e.g. m.creationDate.year, "
            "m.creationDate.month, m.creationDate.quarter)."
        ),
        "sources": [
            "eval/QA_GUIDELINE.md dòng 30 (commit 908f683, 11/10/2026)",
            "eval/templates/temporal.json TM-01..05 (commit 067c7a3, 19/10/2026)",
        ],
    },
    {
        "id": "C6_CREATION_VS_JOIN_DATE",
        "rule": (
            "Person.creationDate is when a person joined the social network (created an account); "
            "rel.joinDate on (:Forum)-[rel:HAS_MEMBER]->(:Person) is when a person joined a forum; "
            "rel.creationDate on (:Person)-[rel:KNOWS]-(:Person) is when two people became friends."
        ),
        "sources": [
            "scripts/load_ldbc.py dòng 64, 97, 104 (commit 908f683, 11/10/2026)",
            "Dev B1 (commit 9aa3d0a, 20/10 16:25): 4 câu nhầm 'joined the network' thành HAS_MEMBER.joinDate (TM-02-01, TM-02-04, TM-02-07, TM-02-10)",
        ],
    },
    {
        "id": "C7_RETURN_PROPERTIES_AND_DISTINCT",
        "rule": (
            "Always RETURN specific property values (e.g. u.name, p.firstName, p.lastName, f.title), "
            "never whole nodes or paths. When counting distinct entities across relationships, use "
            "count(DISTINCT x); for 'the most / the largest / the first', use ORDER BY ... LIMIT 1."
        ),
        "sources": [
            "eval/QA_GUIDELINE.md dòng 31–32, 64 (commit 908f683, 11/10/2026)",
            "Dev B1 (commit 9aa3d0a, 20/10 16:25): 6 câu trả về nguyên node RETURN u / RETURN f (LK-03-02, LK-03-06, LK-03-09, MH-03-09...)",
        ],
    },
]


def banned_values():
    """Tập giá trị tham số của dev.json và test.json cũ (KHÔNG đọc test2.json theo quy tắc mục 2.5)."""
    try:
        from proposed.common import banned_values as common_banned  # dùng bản chung của Bằng nếu đã có
        return common_banned()
    except ImportError:
        pass
    banned = set()
    for split in ("dev", "test"):
        path = QDIR / f"{split}.json"
        if not path.exists():
            continue
        for q in json.loads(path.read_text(encoding="utf-8")):
            for v in q.get("params", {}).values():
                s = str(v).strip()
                banned |= {s, s.replace(" ", "_"), s.replace("_", " ")}
    return banned


def sample_names(driver):
    """Lấy 1 giá trị mẫu có dấu '_' cho mỗi nhãn trong SAMPLE_LABELS, loại trừ mọi giá trị trong banned_values()."""
    banned = {v.lower() for v in banned_values()}
    out = []
    for label in SAMPLE_LABELS:
        records, _, _ = driver.execute_query(
            f"MATCH (n:{label}) WHERE n.name CONTAINS '_' RETURN n.name AS name ORDER BY n.id LIMIT 40"
        )
        for r in records:
            name = r["name"]
            if name.lower() not in banned and name.replace("_", " ").lower() not in banned:
                out.append(f"'{name}' (:{label})")
                break
    return ", ".join(out)


def build_conventions(driver):
    """Ghép 7 quy ước sạch kèm giá trị mẫu lấy từ Neo4j."""
    samples = sample_names(driver)
    lines = ["Conventions of this graph:"]
    for item in CONVENTION_SOURCES:
        rule = item["rule"].format(samples=samples) if "{samples}" in item["rule"] else item["rule"]
        lines.append(f"- {rule}")
    return "\n".join(lines)


def detailed_schema(driver) -> str:
    """Trả về chuỗi schema chi tiết + quy ước sạch (< 1.500 token) để đưa vào prompt."""
    base_schema = build_schema(driver)
    conventions = build_conventions(driver)
    return f"{base_schema}\n\n{conventions}"


def estimate_tokens(text: str) -> int:
    """Ước lượng số token theo quy tắc chuẩn ~4 ký tự/token và đếm mảnh từ/ký tự."""
    word_pieces = len(re.findall(r"\w+|[^\w\s]", text))
    return max(len(text) // 4, int(word_pieces * 0.85))


if __name__ == "__main__":
    from neo4j import GraphDatabase

    sys.stdout.reconfigure(encoding="utf-8")
    with GraphDatabase.driver(URI, auth=AUTH, notifications_min_severity="OFF") as drv:
        text = detailed_schema(drv)
    n_chars = len(text)
    n_lines = len(text.splitlines())
    est_tok = estimate_tokens(text)
    print(text)
    print("\n" + "=" * 72)
    print(f"Độ dài detailed_schema: {n_lines} dòng | {n_chars} ký tự | ~{est_tok} tokens (giới hạn < 1.500 tokens)")
    print("Nguồn gốc 7 quy ước:")
    for item in CONVENTION_SOURCES:
        print(f"  - {item['id']}: {'; '.join(item['sources'])}")

