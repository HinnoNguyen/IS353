"""T32 – Unit test cho Module (B) Liên kết thực thể (eval/proposed/entity_link.py) (Ân).

Chạy:
    cd DoAn
    python -m unittest discover -s tests -v

Không phụ thuộc vào server Neo4j đang chạy (sử dụng FakeSession mô phỏng).
Đặc biệt kiểm tra:
1. Tách đúng họ tên nhiều chữ trên dev: PA-01-05 (Nedeljko Bajić Mikulic), PA-01-08 (Ajuma Nasenyana Brar).
2. dev_zero: Không gán sai người không có trong DB (LK-04-Z01/Z02, MH-01-Z01/Z02).
3. Chuẩn hóa dấu gạch dưới cho Tag và Place ("Tilda Swinton" -> Tilda_Swinton, "Hong Kong" -> Hong_Kong).
4. Khung định dạng gợi ý cho prompt.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "eval"))

from proposed import entity_link  # noqa: E402


class FakeNode(dict):
    """Mô phỏng Neo4j Node."""
    def __init__(self, labels, props):
        super().__init__(props)
        self.labels = set(labels)

    def get(self, k, default=None):
        return super().get(k, default)


class FakeRecord(dict):
    """Mô phỏng neo4j.Record."""
    def __init__(self, data):
        super().__init__(data)


class FakeResult:
    def __init__(self, records):
        self.records = records

    def __iter__(self):
        return iter(self.records)

    def data(self):
        return self.records


class FakeSession:
    """Session giả lập Neo4j để kiểm thử logic liên kết thực thể mà không cần DB thật."""
    def __init__(self, db_people=None, db_places=None, db_tags=None, db_orgs=None):
        self.people = db_people or []  # list of (firstName, lastName)
        self.places = db_places or []  # list of (labels, name)
        self.tags = db_tags or []      # list of name
        self.orgs = db_orgs or []      # list of (labels, name)

    def run(self, query, **params):
        records = []
        q_clean = query.strip()

        # Fulltext hoặc Match Person
        if "person_name_fulltext" in q_clean or "p:Person" in q_clean:
            # Mô phỏng tìm kiếm
            for fn, ln in self.people:
                node = FakeNode(["Person"], {"firstName": fn, "lastName": ln})
                records.append(FakeRecord({"node": node, "score": 1.0, "fn": fn, "ln": ln}))

        # Fulltext hoặc Match Place
        elif "place_name_fulltext" in q_clean or "p:Place" in q_clean:
            for labels, name in self.places:
                node = FakeNode(labels, {"name": name})
                records.append(FakeRecord({"node": node, "score": 1.0, "labels": labels, "name": name}))

        # Fulltext hoặc Match Tag
        elif "tag_name_fulltext" in q_clean or "t:Tag" in q_clean:
            for name in self.tags:
                node = FakeNode(["Tag"], {"name": name})
                records.append(FakeRecord({"node": node, "score": 1.0, "name": name}))

        # Fulltext hoặc Match Organisation
        elif "organisation_name_fulltext" in q_clean or "o:Organisation" in q_clean:
            for labels, name in self.orgs:
                node = FakeNode(labels, {"name": name})
                records.append(FakeRecord({"node": node, "score": 1.0, "labels": labels, "name": name}))

        return FakeResult(records)


class TestEntityExtraction(unittest.TestCase):
    def test_extract_quoted_tags(self):
        q = 'How many posts are tagged with "Aung San Suu Kyi"?'
        cands = entity_link.extract_candidate_mentions(q)
        self.assertIn("Aung San Suu Kyi", cands)

    def test_extract_multiword_names(self):
        q = "How many friendship steps separate Anura Abeywardena from Nedeljko Bajić Mikulic?"
        cands = entity_link.extract_candidate_mentions(q)
        self.assertIn("Anura Abeywardena", cands)
        self.assertIn("Nedeljko Bajić Mikulic", cands)

    def test_extract_with_initials(self):
        q = "Which country does S. N. Hall live in?"
        cands = entity_link.extract_candidate_mentions(q)
        self.assertIn("S. N. Hall", cands)

    def test_extract_vietnamese_unicode(self):
        q = "What is the length of the shortest friendship path between Ayesha Butt and Hồ Chí Loan?"
        cands = entity_link.extract_candidate_mentions(q)
        self.assertIn("Hồ Chí Loan", cands)
        self.assertIn("Ayesha Butt", cands)

    def test_extract_possessive_person(self):
        q = "Who among Claude Radafison's friends lives in the same city as them?"
        cands = entity_link.extract_candidate_mentions(q)
        self.assertIn("Claude Radafison", cands)

    def test_stopwords_not_extracted_as_entities(self):
        q = "What is the number of people living in France?"
        cands = entity_link.extract_candidate_mentions(q)
        self.assertIn("France", cands)
        self.assertNotIn("What", cands)
        self.assertNotIn("What is", cands)


class TestEntityLinking(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession(
            db_people=[
                ("Anura", "Abeywardena"),
                ("Nedeljko Bajić", "Mikulic"),  # PA-01-05
                ("Ajuma Nasenyana", "Brar"),    # PA-01-08
                ("Andrey", "Aab"),
                ("S. N.", "Hall"),
                ("Claude", "Radafison"),
                ("Boris", "Johnson"),            # cùng tên Boris với Boris Sheik nhưng khác người
                ("Abdullah", "Sheik"),           # cùng họ Sheik nhưng khác người
            ],
            db_places=[
                (["Place", "Country"], "Hong_Kong"),
                (["Place", "Country"], "France"),
                (["Place", "Country"], "Uruguay"),
                (["Place", "City"], "London"),
            ],
            db_tags=[
                "Aung_San_Suu_Kyi",
                "Tilda_Swinton",
                "There_Is_No_Beginning_to_the_Story",
            ],
            db_orgs=[
                (["Organisation", "University"], "University_of_Oxford"),
            ]
        )

    def test_pa01_05_multiword_firstname_resolved_correctly(self):
        """PA-01-05: 'Nedeljko Bajić Mikulic' phải nhận diện đúng firstName 'Nedeljko Bajić' và lastName 'Mikulic'."""
        q = "How many friendship steps separate Anura Abeywardena from Nedeljko Bajić Mikulic?"
        results = entity_link.link_entities_in_session(self.session, q)
        names = {r["properties"]["firstName"]: r["properties"]["lastName"] for r in results if r["type"] == "Person"}
        self.assertIn("Nedeljko Bajić", names)
        self.assertEqual(names["Nedeljko Bajić"], "Mikulic")
        self.assertIn("Anura", names)
        self.assertEqual(names["Anura"], "Abeywardena")

    def test_pa01_08_multiword_firstname_resolved_correctly(self):
        """PA-01-08: 'Ajuma Nasenyana Brar' phải nhận diện đúng firstName 'Ajuma Nasenyana' và lastName 'Brar'."""
        q = "How many friendship steps separate Ajuma Nasenyana Brar from Andrey Aab?"
        results = entity_link.link_entities_in_session(self.session, q)
        names = {r["properties"]["firstName"]: r["properties"]["lastName"] for r in results if r["type"] == "Person"}
        self.assertIn("Ajuma Nasenyana", names)
        self.assertEqual(names["Ajuma Nasenyana"], "Brar")
        self.assertIn("Andrey", names)
        self.assertEqual(names["Andrey"], "Aab")

    def test_dev_zero_person_not_in_db_must_never_link(self):
        """dev_zero: 'Boris Sheik' KHÔNG có trong DB (dù có Boris Johnson và Abdullah Sheik).

        Module (B) tuyệt đối không được liên kết nhầm sang Boris Johnson hay Abdullah Sheik.
        """
        q = "When was Boris Sheik born?"
        results = entity_link.link_entities_in_session(self.session, q)
        people = [r for r in results if r["type"] == "Person"]
        self.assertEqual(people, [], "Boris Sheik không có trong DB nên không được sinh gợi ý Person")

    def test_dev_zero_budi_balawan_must_never_link(self):
        """dev_zero: 'Budi Balawan' không có trong DB -> không được liên kết."""
        q = "What is the date of birth of Budi Balawan?"
        results = entity_link.link_entities_in_session(self.session, q)
        people = [r for r in results if r["type"] == "Person"]
        self.assertEqual(people, [])

    def test_tag_underscores_linked_properly(self):
        """'Tilda Swinton' -> Tag: name='Tilda_Swinton'."""
        q = 'How many posts are tagged with "Tilda Swinton"?'
        results = entity_link.link_entities_in_session(self.session, q)
        tags = [r for r in results if r["type"] == "Tag"]
        self.assertEqual(len(tags), 1)
        self.assertEqual(tags[0]["properties"]["name"], "Tilda_Swinton")

    def test_country_underscores_linked_properly(self):
        """'Hong Kong' -> Country: name='Hong_Kong'."""
        q = "How many people live in Hong Kong?"
        results = entity_link.link_entities_in_session(self.session, q)
        places = [r for r in results if r["type"] in ("Country", "Place")]
        self.assertTrue(len(places) >= 1)
        self.assertEqual(places[0]["properties"]["name"], "Hong_Kong")

    def test_format_hints_produces_prompt_ready_string(self):
        q = "How many friendship steps separate Anura Abeywardena from Nedeljko Bajić Mikulic?"
        hints = entity_link.format_hints(self.session, q)
        self.assertTrue(hints.startswith("Relevant entities in the graph:\n"))
        self.assertIn("firstName='Nedeljko Bajić'", hints)
        self.assertIn("lastName='Mikulic'", hints)
        self.assertTrue(hints.endswith("\n\n"))

    def test_format_hints_empty_when_no_entities_found(self):
        """dev_zero: khi không tìm thấy thực thể, trả về rỗng '' để không làm nhiễu prompt."""
        q = "When was Boris Sheik born?"
        hints = entity_link.format_hints(self.session, q)
        self.assertEqual(hints, "")


class TestAntiLeakage(unittest.TestCase):
    def test_no_test2_in_entity_link(self):
        code = Path(entity_link.__file__).read_text(encoding="utf-8")
        self.assertNotIn("test2.json", code)
        self.assertNotIn('"test2"', code)


if __name__ == "__main__":
    unittest.main()
