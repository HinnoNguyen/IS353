# Câu sai của B1 run 1 (openai/gpt-oss-20b, test)

77/150 câu sai. Nguồn: `results/runs/test/b1_zeroshot__openai-gpt-oss-20b__run1.json`. Thứ tự: theo loại câu, rồi theo id.

## lookup (3 câu sai)

**LK-01-07** (lookup) – nhãn `empty_result`

- Câu hỏi: Which city does Kieu Cong Do live in?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName: "Kieu", lastName: "Cong Do"})-[:IS_LOCATED_IN]->(c:City:Place)
RETURN c.name AS city
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Kieu Cong', lastName: 'Do'})-[:IS_LOCATED_IN]->(c:City) RETURN c.name
```

- Kết quả gold: `[["Đà_Lạt"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**LK-02-03** (lookup) – nhãn `empty_result`

- Câu hỏi: Who are the employers of Esti Mamo Dego?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName: "Esti", lastName: "Mamo Dego"})-[:WORK_AT]->(c:Company)
RETURN c.name AS employer
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Esti Mamo', lastName: 'Dego'})-[:WORK_AT]->(c:Company) RETURN c.name
```

- Kết quả gold: `[["TransAsia_Airways"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**LK-02-09** (lookup) – nhãn `wrong_result`

- Câu hỏi: Who are the employers of Abby Hassan?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:"Abby", lastName:"Hassan"})-[:WORK_AT]->(c:Organisation:Company) RETURN c
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Abby', lastName: 'Hassan'})-[:WORK_AT]->(c:Company) RETURN c.name
```

- Kết quả gold: `[["Silverfly_(airline)"]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[{"_labels": ["Company", "Organisation"], "name": "Silverfly_(airline)", "id": 770, "url": "http://dbpedia.org/resource/Silverfly_(airline)"}]]`

## aggregation (17 câu sai)

**AG-02-02** (aggregation) – nhãn `empty_result`

- Câu hỏi: In United Kingdom, which city do the largest number of people live in?
- Cypher sinh ra:

```cypher
MATCH (c:Place:City)-[:IS_PART_OF]->(co:Place:Country {name: 'United Kingdom'}), (p:Person)-[:IS_LOCATED_IN]->(c)
RETURN c.name AS city, count(p) AS numPeople
ORDER BY numPeople DESC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:IS_LOCATED_IN]->(c:City)-[:IS_PART_OF]->(:Country {name: 'United_Kingdom'}) RETURN c.name, count(DISTINCT p) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["Bristol"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**AG-02-03** (aggregation) – nhãn `empty_result`

- Câu hỏi: What is the most populated city of Democratic Republic of the Congo in the network?
- Cypher sinh ra:

```cypher
MATCH (c:City:Place)-[:IS_PART_OF]->(co:Country:Place {name:"Democratic Republic of the Congo"})
MATCH (p:Person)-[:IS_LOCATED_IN]->(c)
WITH c, count(p) AS population
RETURN c.name AS city, population
ORDER BY population DESC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:IS_LOCATED_IN]->(c:City)-[:IS_PART_OF]->(:Country {name: 'Democratic_Republic_of_the_Congo'}) RETURN c.name, count(DISTINCT p) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["Boma"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**AG-02-04** (aggregation) – nhãn `empty_result`

- Câu hỏi: Which city in Czech Republic has the most residents?
- Cypher sinh ra:

```cypher
MATCH (c:Place:City)-[:IS_PART_OF]->(co:Place:Country {name: 'Czech Republic'})
MATCH (p:Person)-[:IS_LOCATED_IN]->(c)
RETURN c.name AS city, count(p) AS residents
ORDER BY residents DESC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:IS_LOCATED_IN]->(c:City)-[:IS_PART_OF]->(:Country {name: 'Czech_Republic'}) RETURN c.name, count(DISTINCT p) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["Hradec_Králové"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**AG-02-10** (aggregation) – nhãn `empty_result`

- Câu hỏi: Which city in Hungary has the most residents?
- Cypher sinh ra:

```cypher
MATCH (c:City)-[:IS_PART_OF]->(co:Country {name:"Hungary"})<-[:IS_LOCATED_IN]-(p:Person)
WITH c, count(p) AS residents
ORDER BY residents DESC
LIMIT 1
RETURN c.name AS city, residents
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:IS_LOCATED_IN]->(c:City)-[:IS_PART_OF]->(:Country {name: 'Hungary'}) RETURN c.name, count(DISTINCT p) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["Esztergom"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**AG-04-02** (aggregation) – nhãn `empty_result`

- Câu hỏi: Among companies based in Czech Republic, which one employs the largest number of people?
- Cypher sinh ra:

```cypher
MATCH (c:Company:Organisation)-[:IS_LOCATED_IN]->(co:Country:Place {name:"Czech Republic"})
MATCH (p:Person)-[:WORK_AT]->(c)
WITH c, count(DISTINCT p) AS empCount
RETURN c.name AS company, empCount
ORDER BY empCount DESC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:WORK_AT]->(c:Company)-[:IS_LOCATED_IN]->(:Country {name: 'Czech_Republic'}) RETURN c.name, count(DISTINCT p) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["Travel_Service_Airlines"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**AG-04-03** (aggregation) – nhãn `empty_result`

- Câu hỏi: What is the biggest employer in South Korea, by number of employees?
- Cypher sinh ra:

```cypher
MATCH (c:Company)-[:IS_LOCATED_IN]->(co:Country {name:"South Korea"})
MATCH (p:Person)-[:WORK_AT]->(c)
WITH c, count(DISTINCT p) AS empCount
ORDER BY empCount DESC
LIMIT 1
RETURN c.name AS company, empCount
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:WORK_AT]->(c:Company)-[:IS_LOCATED_IN]->(:Country {name: 'South_Korea'}) RETURN c.name, count(DISTINCT p) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["Eastar_Jet"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**AG-04-07** (aggregation) – nhãn `empty_result`

- Câu hỏi: Which company in Sri Lanka has the most employees?
- Cypher sinh ra:

```cypher
MATCH (c:Organisation:Company)-[:IS_LOCATED_IN]->(co:Place:Country {name:"Sri Lanka"})
MATCH (p:Person)-[:WORK_AT]->(c)
WITH c, count(DISTINCT p) AS empCount
ORDER BY empCount DESC
LIMIT 1
RETURN c.name AS company, empCount
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:WORK_AT]->(c:Company)-[:IS_LOCATED_IN]->(:Country {name: 'Sri_Lanka'}) RETURN c.name, count(DISTINCT p) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["Aero_Lanka"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**AG-05-01** (aggregation) – nhãn `wrong_result`

- Câu hỏi: How many people are interested in "Phil Spector"?
- Cypher sinh ra:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(t:Tag {name:"Phil Spector"})
RETURN count(p) AS numPeople
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(:Tag {name: 'Phil_Spector'}) RETURN count(DISTINCT p) AS total
```

- Kết quả gold: `[[9]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**AG-05-02** (aggregation) – nhãn `wrong_result`

- Câu hỏi: How many people list "Left Behind" among their interests?
- Cypher sinh ra:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(t:Tag {name:"Left Behind"})
RETURN count(p) AS numPeople
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(:Tag {name: 'Left_Behind'}) RETURN count(DISTINCT p) AS total
```

- Kết quả gold: `[[3]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**AG-05-03** (aggregation) – nhãn `wrong_result`

- Câu hỏi: What is the number of people with an interest in "Color Me Barbra"?
- Cypher sinh ra:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(t:Tag {name:"Color Me Barbra"})
RETURN count(DISTINCT p) AS numPeople
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(:Tag {name: 'Color_Me_Barbra'}) RETURN count(DISTINCT p) AS total
```

- Kết quả gold: `[[2]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**AG-05-04** (aggregation) – nhãn `wrong_result`

- Câu hỏi: How many people are interested in "William Randolph Hearst"?
- Cypher sinh ra:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(t:Tag {name:"William Randolph Hearst"})
RETURN count(p) AS interestCount
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(:Tag {name: 'William_Randolph_Hearst'}) RETURN count(DISTINCT p) AS total
```

- Kết quả gold: `[[13]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**AG-05-05** (aggregation) – nhãn `wrong_result`

- Câu hỏi: How many people list "Christopher Lee" among their interests?
- Cypher sinh ra:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(t:Tag {name:"Christopher Lee"})
RETURN count(p) AS numPeople
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(:Tag {name: 'Christopher_Lee'}) RETURN count(DISTINCT p) AS total
```

- Kết quả gold: `[[22]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**AG-05-06** (aggregation) – nhãn `wrong_result`

- Câu hỏi: What is the number of people with an interest in "Kaia Kanepi"?
- Cypher sinh ra:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(t:Tag {name:"Kaia Kanepi"})
RETURN count(DISTINCT p) AS numPeople
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(:Tag {name: 'Kaia_Kanepi'}) RETURN count(DISTINCT p) AS total
```

- Kết quả gold: `[[9]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**AG-05-07** (aggregation) – nhãn `wrong_result`

- Câu hỏi: How many people are interested in "Pierre Trudeau"?
- Cypher sinh ra:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(t:Tag {name:"Pierre Trudeau"})
RETURN count(p) AS interestedCount
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(:Tag {name: 'Pierre_Trudeau'}) RETURN count(DISTINCT p) AS total
```

- Kết quả gold: `[[29]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**AG-05-08** (aggregation) – nhãn `wrong_result`

- Câu hỏi: How many people list "I Walk the Line" among their interests?
- Cypher sinh ra:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(t:Tag {name:"I Walk the Line"})
RETURN count(p) AS numPeople
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(:Tag {name: 'I_Walk_the_Line'}) RETURN count(DISTINCT p) AS total
```

- Kết quả gold: `[[2]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**AG-05-09** (aggregation) – nhãn `wrong_result`

- Câu hỏi: What is the number of people with an interest in "Good Vibrations"?
- Cypher sinh ra:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(t:Tag {name: "Good Vibrations"})
RETURN count(DISTINCT p) AS numPeople
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(:Tag {name: 'Good_Vibrations'}) RETURN count(DISTINCT p) AS total
```

- Kết quả gold: `[[2]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**AG-05-10** (aggregation) – nhãn `wrong_result`

- Câu hỏi: How many people are interested in "Brian Eno"?
- Cypher sinh ra:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(t:Tag {name:"Brian Eno"})
RETURN count(DISTINCT p) AS interestedCount
```

- Cypher gold:

```cypher
MATCH (p:Person)-[:HAS_INTEREST]->(:Tag {name: 'Brian_Eno'}) RETURN count(DISTINCT p) AS total
```

- Kết quả gold: `[[8]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

## multi_hop (10 câu sai)

**MH-02-01** (multi_hop) – nhãn `wrong_result`

- Câu hỏi: At which university do the largest number of Arjun Rao's friends study?
- Cypher sinh ra:

```cypher
MATCH (arjun:Person {firstName:"Arjun", lastName:"Rao"})-[:KNOWS]->(friend:Person)-[:STUDY_AT]->(uni:Organisation:University)
WITH uni, count(DISTINCT friend) AS numFriends
RETURN uni, numFriends
ORDER BY numFriends DESC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Arjun', lastName: 'Rao'})-[:KNOWS]-(f:Person)-[:STUDY_AT]->(u:University) RETURN u.name, count(DISTINCT f) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["Sir_M._Visvesvaraya_Institute_of_Technology"]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[{"_labels": ["Organisation", "University"], "name": "Sir_M._Visvesvaraya_Institute_of_Technology", "id": 3014, "url": "http://dbpedia.org/resource/Sir_M._Visvesvaraya_Institute_of_Technology"}, 3]]`

**MH-02-02** (multi_hop) – nhãn `wrong_result`

- Câu hỏi: Which university do most of Emperor of Brazil Machado's friends attend?
- Cypher sinh ra:

```cypher
MATCH (p:Person)-[:KNOWS]->(f:Person)-[:STUDY_AT]->(u:Organisation:University)
WHERE p.firstName CONTAINS 'Emperor' AND p.lastName CONTAINS 'Machado'
RETURN u.name AS university, count(DISTINCT f) AS numFriends
ORDER BY numFriends DESC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Emperor of Brazil', lastName: 'Machado'})-[:KNOWS]-(f:Person)-[:STUDY_AT]->(u:University) RETURN u.name, count(DISTINCT f) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["Rio_de_Janeiro_State_University"]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[["Hangzhou_International_School", 1]]`

**MH-02-04** (multi_hop) – nhãn `wrong_result`

- Câu hỏi: At which university do the largest number of Paulo Alves's friends study?
- Cypher sinh ra:

```cypher
MATCH (paulo:Person {firstName:"Paulo", lastName:"Alves"})-[:KNOWS]->(friend:Person)-[:STUDY_AT]->(uni:Organisation:University)
RETURN uni, count(DISTINCT friend) AS numFriends
ORDER BY numFriends DESC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Paulo', lastName: 'Alves'})-[:KNOWS]-(f:Person)-[:STUDY_AT]->(u:University) RETURN u.name, count(DISTINCT f) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["Rio_de_Janeiro_State_University"]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[{"_labels": ["Organisation", "University"], "name": "L._N._Gumilyov_Eurasian_National_University", "id": 4939, "url": "http://dbpedia.org/resource/L._N._Gumilyov_Eurasian_National_University"}, 1]]`

**MH-02-05** (multi_hop) – nhãn `wrong_result`

- Câu hỏi: Which university do most of Zhang Li's friends attend?
- Cypher sinh ra:

```cypher
MATCH (z:Person {firstName:'Zhang', lastName:'Li'})-[:KNOWS]->(friend:Person)
MATCH (friend)-[:STUDY_AT]->(uni:Organisation:University)
WITH uni, count(DISTINCT friend) AS cnt
ORDER BY cnt DESC
LIMIT 1
RETURN uni.name AS university
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Zhang', lastName: 'Li'})-[:KNOWS]-(f:Person)-[:STUDY_AT]->(u:University) RETURN u.name, count(DISTINCT f) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["Shenyang_Pharmaceutical_University"]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[["Bilkent_University"]]`

**MH-02-06** (multi_hop) – nhãn `wrong_result`

- Câu hỏi: Among the friends of Michel David, which university has the most students?
- Cypher sinh ra:

```cypher
MATCH (m:Person {firstName:"Michel", lastName:"David"})-[:KNOWS]->(f:Person)
MATCH (f)-[:STUDY_AT]->(u:Organisation:University)
WITH u, count(DISTINCT f) AS studentCount
ORDER BY studentCount DESC
LIMIT 1
RETURN u.name AS university, studentCount
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Michel', lastName: 'David'})-[:KNOWS]-(f:Person)-[:STUDY_AT]->(u:University) RETURN u.name, count(DISTINCT f) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["University_of_the_Basque_Country"]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[["Instituto_Nacional_de_Matemática_Pura_e_Aplicada", 1]]`

**MH-02-10** (multi_hop) – nhãn `wrong_result`

- Câu hỏi: At which university do the largest number of János Mészáros's friends study?
- Cypher sinh ra:

```cypher
MATCH (j:Person {firstName:"János", lastName:"Mészáros"})-[:KNOWS]->(f:Person)-[:STUDY_AT]->(u:Organisation:University)
RETURN u, count(*) AS numFriends
ORDER BY numFriends DESC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'János', lastName: 'Mészáros'})-[:KNOWS]-(f:Person)-[:STUDY_AT]->(u:University) RETURN u.name, count(DISTINCT f) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["Fulda_University_of_Applied_Sciences"]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[{"_labels": ["Organisation", "University"], "name": "International_Centre_for_Theoretical_Physics", "id": 4676, "url": "http://dbpedia.org/resource/International_Centre_for_Theoretical_Physics"}, 1]]`

**MH-04-05** (multi_hop) – nhãn `wrong_result`

- Câu hỏi: Which countries are Bjorn Andersson's employers based in?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:"Bjorn", lastName:"Andersson"})-[:WORK_AT]->(c:Company)-[:IS_LOCATED_IN]->(country:Country)
RETURN DISTINCT country
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Bjorn', lastName: 'Andersson'})-[:WORK_AT]->(:Company)-[:IS_LOCATED_IN]->(k:Country) RETURN DISTINCT k.name
```

- Kết quả gold: `[["Sweden"]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[{"_labels": ["Country", "Place"], "name": "Sweden", "id": 101, "url": "http://dbpedia.org/resource/Sweden"}]]`

**MH-05-04** (multi_hop) – nhãn `empty_result`

- Câu hỏi: Which category do most of Fali Sam Nariman's interests belong to?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:"Fali", lastName:"Sam Nariman"})-[:HAS_INTEREST]->(t:Tag)-[:HAS_TYPE]->(c:TagClass)
RETURN c.name AS category, count(*) AS cnt
ORDER BY cnt DESC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Fali Sam', lastName: 'Nariman'})-[:HAS_INTEREST]->(t:Tag)-[:HAS_TYPE]->(tc:TagClass) RETURN tc.name, count(DISTINCT t) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["Single"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**MH-05-08** (multi_hop) – nhãn `execution_error`

- Câu hỏi: Most of the topics Carl Becker is interested in fall into which category?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:'Carl', lastName:'Becker'})-[:HAS_INTEREST]->(t:Tag)-[:HAS_TYPE]->(c:TagClass)
RETURN c.name AS category
ORDER BY count(t) DESC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Carl', lastName: 'Becker'})-[:HAS_INTEREST]->(t:Tag)-[:HAS_TYPE]->(tc:TagClass) RETURN tc.name, count(DISTINCT t) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["OfficeHolder"]]`
- Lỗi: `Neo.ClientError.Statement.SyntaxError: Cannot use aggregation in ORDER BY if there are no aggregate expressions in the preceding RETURN (line 2, column 1 (offset: 106))`

**MH-05-09** (multi_hop) – nhãn `execution_error`

- Câu hỏi: What is the most common category among A. Kumar's interests?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName: "A.", lastName: "Kumar"})-[:HAS_INTEREST]->(t:Tag)-[:HAS_TYPE]->(c:TagClass)
RETURN c.name AS mostCommonCategory
ORDER BY count(t) DESC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'A.', lastName: 'Kumar'})-[:HAS_INTEREST]->(t:Tag)-[:HAS_TYPE]->(tc:TagClass) RETURN tc.name, count(DISTINCT t) AS n ORDER BY n DESC LIMIT 1
```

- Kết quả gold: `[["Person"]]`
- Lỗi: `Neo.ClientError.Statement.SyntaxError: Cannot use aggregation in ORDER BY if there are no aggregate expressions in the preceding RETURN (line 2, column 1 (offset: 105))`

## path (27 câu sai)

**PA-02-01** (path) – nhãn `wrong_result`

- Câu hỏi: How many different shortest friendship paths connect Paul Bologan and Taufik Rafiq?
- Cypher sinh ra:

```cypher
MATCH (p1:Person {firstName:"Paul", lastName:"Bologan"}), (p2:Person {firstName:"Taufik", lastName:"Rafiq"})
MATCH p = allShortestPaths((p1)-[:KNOWS*]->(p2))
RETURN count(p) AS numShortestPaths
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Paul', lastName: 'Bologan'}), (b:Person {firstName: 'Taufik', lastName: 'Rafiq'}) MATCH p = allShortestPaths((a)-[:KNOWS*]-(b)) RETURN count(p)
```

- Kết quả gold: `[[1]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**PA-02-02** (path) – nhãn `wrong_result`

- Câu hỏi: How many distinct shortest chains of friends link Chen Liu to Aurora Cruz?
- Cypher sinh ra:

```cypher
MATCH p = allShortestPaths((p1:Person {firstName:'Chen', lastName:'Liu'})-[:KNOWS*]->(p2:Person {firstName:'Aurora', lastName:'Cruz'}))
RETURN count(p) AS numShortestChains
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Chen', lastName: 'Liu'}), (b:Person {firstName: 'Aurora', lastName: 'Cruz'}) MATCH p = allShortestPaths((a)-[:KNOWS*]-(b)) RETURN count(p)
```

- Kết quả gold: `[[17]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**PA-02-03** (path) – nhãn `wrong_result`

- Câu hỏi: Count the shortest friendship paths between Warwick Raymond Akerman and Akira Inoue.
- Cypher sinh ra:

```cypher
MATCH (p1:Person {firstName:"Warwick", lastName:"Akerman"}), (p2:Person {firstName:"Akira", lastName:"Inoue"})
MATCH p = allShortestPaths((p1)-[:KNOWS*]-(p2))
RETURN count(p) AS shortestFriendshipPathCount
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Warwick Raymond', lastName: 'Akerman'}), (b:Person {firstName: 'Akira', lastName: 'Inoue'}) MATCH p = allShortestPaths((a)-[:KNOWS*]-(b)) RETURN count(p)
```

- Kết quả gold: `[[2]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**PA-02-04** (path) – nhãn `wrong_result`

- Câu hỏi: How many different shortest friendship paths connect David Agudelo and Mamoon Eshaq 0 Amin?
- Cypher sinh ra:

```cypher
MATCH (p1:Person {firstName:"David", lastName:"Agudelo"}), (p2:Person {firstName:"Mamoon", lastName:"Eshaq 0 Amin"})
MATCH path = allShortestPaths((p1)-[:KNOWS*]-(p2))
RETURN count(path) AS numShortestPaths
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'David', lastName: 'Agudelo'}), (b:Person {firstName: 'Mamoon Eshaq 0', lastName: 'Amin'}) MATCH p = allShortestPaths((a)-[:KNOWS*]-(b)) RETURN count(p)
```

- Kết quả gold: `[[1]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**PA-02-05** (path) – nhãn `wrong_result`

- Câu hỏi: How many distinct shortest chains of friends link Jose Carvalho to Ali Koksal?
- Cypher sinh ra:

```cypher
MATCH p = allShortestPaths((p1:Person {firstName:"Jose", lastName:"Carvalho"})-[:KNOWS*]->(p2:Person {firstName:"Ali", lastName:"Koksal"}))
RETURN count(p) AS numShortestChains
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Jose', lastName: 'Carvalho'}), (b:Person {firstName: 'Ali', lastName: 'Koksal'}) MATCH p = allShortestPaths((a)-[:KNOWS*]-(b)) RETURN count(p)
```

- Kết quả gold: `[[6]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**PA-02-07** (path) – nhãn `wrong_result`

- Câu hỏi: How many different shortest friendship paths connect Dado Kesovija and Evangelos Alkaios?
- Cypher sinh ra:

```cypher
MATCH (a:Person {firstName:"Dado", lastName:"Kesovija"}), (b:Person {firstName:"Evangelos", lastName:"Alkaios"})
MATCH p = allShortestPaths((a)-[:KNOWS*]->(b))
RETURN count(p) AS numShortestPaths
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Dado', lastName: 'Kesovija'}), (b:Person {firstName: 'Evangelos', lastName: 'Alkaios'}) MATCH p = allShortestPaths((a)-[:KNOWS*]-(b)) RETURN count(p)
```

- Kết quả gold: `[[1]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**PA-02-08** (path) – nhãn `execution_error`

- Câu hỏi: How many distinct shortest chains of friends link Bechir Cardinale to Ayesha Ahmed?
- Cypher sinh ra:

```cypher
MATCH (a:Person {firstName:'Bechir', lastName:'Cardinale'}), (b:Person {firstName:'Ayesha', lastName:'Ahmed'})
MATCH p = shortestPath((a)-[:KNOWS*]->(b))
WITH a, b, length(p) AS L
MATCH q = (a)-[:KNOWS*L..L]->(b)
RETURN count(DISTINCT q) AS numShortestChains
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Bechir', lastName: 'Cardinale'}), (b:Person {firstName: 'Ayesha', lastName: 'Ahmed'}) MATCH p = allShortestPaths((a)-[:KNOWS*]-(b)) RETURN count(p)
```

- Kết quả gold: `[[13]]`
- Lỗi: `Neo.ClientError.Statement.SyntaxError: Invalid input 'L': expected a parameter, '..', 'WHERE', ']', '{' or an integer value (line 4, column 23 (offset: 202))`

**PA-02-09** (path) – nhãn `execution_error`

- Câu hỏi: Count the shortest friendship paths between A. C. Bos and Gustavo Arbelaez.
- Cypher sinh ra:

```cypher
MATCH (a:Person {firstName:"A.", lastName:"Bos"}), (b:Person {firstName:"Gustavo", lastName:"Arbelaez"})
MATCH p=shortestPath((a)-[:KNOWS*]-(b))
WITH a,b, length(p) AS shortestLength
MATCH p2=(a)-[:KNOWS*shortestLength]-(b)
RETURN count(DISTINCT p2) AS shortestFriendshipPathCount
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'A. C.', lastName: 'Bos'}), (b:Person {firstName: 'Gustavo', lastName: 'Arbelaez'}) MATCH p = allShortestPaths((a)-[:KNOWS*]-(b)) RETURN count(p)
```

- Kết quả gold: `[[1]]`
- Lỗi: `Neo.ClientError.Statement.SyntaxError: Invalid input 'shortestLength': expected a parameter, '..', 'WHERE', ']', '{' or an integer value (line 4, column 22 (offset: 204))`

**PA-02-10** (path) – nhãn `wrong_result`

- Câu hỏi: How many different shortest friendship paths connect Pedro Oliveira and Howard Nguyen?
- Cypher sinh ra:

```cypher
MATCH p = allShortestPaths((p1:Person {firstName:"Pedro", lastName:"Oliveira"})-[:KNOWS*]->(p2:Person {firstName:"Howard", lastName:"Nguyen"}))
RETURN count(p) AS numShortestPaths
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Pedro', lastName: 'Oliveira'}), (b:Person {firstName: 'Howard', lastName: 'Nguyen'}) MATCH p = allShortestPaths((a)-[:KNOWS*]-(b)) RETURN count(p)
```

- Kết quả gold: `[[5]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**PA-04-01** (path) – nhãn `wrong_result`

- Câu hỏi: How many people can Maria Onopka reach within two friendship steps?
- Cypher sinh ra:

```cypher
MATCH (m:Person {firstName:'Maria', lastName:'Onopka'})
MATCH (m)-[:KNOWS*1..2]->(p:Person)
WHERE p <> m
RETURN count(DISTINCT p) AS reachableCount
```

- Cypher gold:

```cypher
MATCH (p:Person {firstName: 'Maria', lastName: 'Onopka'})-[:KNOWS*1..2]-(f:Person) WHERE f <> p RETURN count(DISTINCT f)
```

- Kết quả gold: `[[646]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[10]]`

**PA-04-03** (path) – nhãn `wrong_result`

- Câu hỏi: Counting friends and friends of friends, how many people is Adriaen Jong connected to?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:"Adriaen", lastName:"Jong"})-[:KNOWS*1..2]->(connected:Person)
WHERE connected <> p
RETURN count(DISTINCT connected) AS totalConnections
```

- Cypher gold:

```cypher
MATCH (p:Person {firstName: 'Adriaen', lastName: 'Jong'})-[:KNOWS*1..2]-(f:Person) WHERE f <> p RETURN count(DISTINCT f)
```

- Kết quả gold: `[[779]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[133]]`

**PA-04-04** (path) – nhãn `wrong_result`

- Câu hỏi: How many people can Zhang Zhang reach within two friendship steps?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:"Zhang", lastName:"Zhang"})-[:KNOWS*1..2]->(friend)
WHERE friend <> p
RETURN count(DISTINCT friend) AS reachableCount
```

- Cypher gold:

```cypher
MATCH (p:Person {firstName: 'Zhang', lastName: 'Zhang'})-[:KNOWS*1..2]-(f:Person) WHERE f <> p RETURN count(DISTINCT f)
```

- Kết quả gold: `[[120]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**PA-04-06** (path) – nhãn `wrong_result`

- Câu hỏi: Counting friends and friends of friends, how many people is Dimitris Antoniou connected to?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:'Dimitris', lastName:'Antoniou'})
MATCH (p)-[:KNOWS*1..2]->(other:Person)
WHERE other <> p
RETURN count(DISTINCT other) AS totalConnections
```

- Cypher gold:

```cypher
MATCH (p:Person {firstName: 'Dimitris', lastName: 'Antoniou'})-[:KNOWS*1..2]-(f:Person) WHERE f <> p RETURN count(DISTINCT f)
```

- Kết quả gold: `[[406]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[79]]`

**PA-04-07** (path) – nhãn `wrong_result`

- Câu hỏi: How many people can Jose Alonso reach within two friendship steps?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:'Jose', lastName:'Alonso'})
MATCH (p)-[:KNOWS*1..2]->(q:Person)
WHERE q <> p
RETURN count(DISTINCT q) AS reachableCount
```

- Cypher gold:

```cypher
MATCH (p:Person {firstName: 'Jose', lastName: 'Alonso'})-[:KNOWS*1..2]-(f:Person) WHERE f <> p RETURN count(DISTINCT f)
```

- Kết quả gold: `[[448]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[8]]`

**PA-04-08** (path) – nhãn `wrong_result`

- Câu hỏi: How many people are at most two friendship links away from Jimmy Brown?
- Cypher sinh ra:

```cypher
MATCH (j:Person {firstName:"Jimmy", lastName:"Brown"})-[:KNOWS*1..2]->(p:Person)
WHERE p <> j
RETURN count(DISTINCT p) AS numPeople
```

- Cypher gold:

```cypher
MATCH (p:Person {firstName: 'Jimmy', lastName: 'Brown'})-[:KNOWS*1..2]-(f:Person) WHERE f <> p RETURN count(DISTINCT f)
```

- Kết quả gold: `[[327]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[10]]`

**PA-04-09** (path) – nhãn `wrong_result`

- Câu hỏi: Counting friends and friends of friends, how many people is Jun Yamada connected to?
- Cypher sinh ra:

```cypher
MATCH (jun:Person {firstName:"Jun", lastName:"Yamada"})
MATCH (jun)-[:KNOWS*1..2]->(p:Person)
WHERE p <> jun
RETURN count(DISTINCT p) AS connectedCount
```

- Cypher gold:

```cypher
MATCH (p:Person {firstName: 'Jun', lastName: 'Yamada'})-[:KNOWS*1..2]-(f:Person) WHERE f <> p RETURN count(DISTINCT f)
```

- Kết quả gold: `[[695]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[229]]`

**PA-04-10** (path) – nhãn `wrong_result`

- Câu hỏi: How many people can Celso Nascimento reach within two friendship steps?
- Cypher sinh ra:

```cypher
MATCH (c:Person {firstName:"Celso", lastName:"Nascimento"})-[:KNOWS*1..2]->(p:Person)
WHERE p <> c
RETURN count(DISTINCT p) AS reachableCount
```

- Cypher gold:

```cypher
MATCH (p:Person {firstName: 'Celso', lastName: 'Nascimento'})-[:KNOWS*1..2]-(f:Person) WHERE f <> p RETURN count(DISTINCT f)
```

- Kết quả gold: `[[309]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[129]]`

**PA-05-01** (path) – nhãn `wrong_result`

- Câu hỏi: How many friendship steps is Jun Kato from the nearest person living in Ambovombe?
- Cypher sinh ra:

```cypher
MATCH (jun:Person {firstName:"Jun", lastName:"Kato"}), (amb:City {name:"Ambovombe"}), (p:Person)-[:IS_LOCATED_IN]->(amb)
WHERE jun <> p
WITH jun, p, shortestPath((jun)-[:KNOWS*]->(p)) AS sp
RETURN length(sp) AS friendshipSteps
ORDER BY friendshipSteps
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Jun', lastName: 'Kato'}), (b:Person)-[:IS_LOCATED_IN]->(:City {name: 'Ambovombe'}) WHERE a <> b MATCH p = shortestPath((a)-[:KNOWS*]-(b)) RETURN min(length(p))
```

- Kết quả gold: `[[3]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[null]]`

**PA-05-02** (path) – nhãn `empty_result`

- Câu hỏi: What is the shortest friendship distance from Bacary Diop to anyone who lives in Dum Dum?
- Cypher sinh ra:

```cypher
MATCH (b:Person {firstName:"Bacary", lastName:"Diop"}), (d:Person)-[:IS_LOCATED_IN]->(city:City {name:"Dum Dum"})
MATCH path = shortestPath((b)-[:KNOWS*]->(d))
RETURN length(path) AS distance
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Bacary', lastName: 'Diop'}), (b:Person)-[:IS_LOCATED_IN]->(:City {name: 'Dum_Dum'}) WHERE a <> b MATCH p = shortestPath((a)-[:KNOWS*]-(b)) RETURN min(length(p))
```

- Kết quả gold: `[[2]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**PA-05-03** (path) – nhãn `wrong_result`

- Câu hỏi: At least how many friendship links separate Chito Reyes from a resident of Fuquan?
- Cypher sinh ra:

```cypher
MATCH (a:Person {firstName:"Chito", lastName:"Reyes"}), (c:City {name:"Fuquan"}), (b:Person)-[:IS_LOCATED_IN]->(c)
MATCH p = shortestPath((a)-[:KNOWS*]->(b))
RETURN length(p) AS minFriendshipLinks
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Chito', lastName: 'Reyes'}), (b:Person)-[:IS_LOCATED_IN]->(:City {name: 'Fuquan'}) WHERE a <> b MATCH p = shortestPath((a)-[:KNOWS*]-(b)) RETURN min(length(p))
```

- Kết quả gold: `[[2]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[4]]`

**PA-05-04** (path) – nhãn `wrong_result`

- Câu hỏi: How many friendship steps is Marek Kaczmarek from the nearest person living in Wah Cantonment?
- Cypher sinh ra:

```cypher
MATCH (m:Person {firstName:"Marek", lastName:"Kaczmarek"})
MATCH (c:Place:City {name:"Wah Cantonment"})
MATCH (p:Person)-[:IS_LOCATED_IN]->(c)
WHERE p <> m
OPTIONAL MATCH path = shortestPath((m)-[:KNOWS*]->(p))
WITH m, p, path
WHERE path IS NOT NULL
RETURN min(length(path)) AS friendshipSteps
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Marek', lastName: 'Kaczmarek'}), (b:Person)-[:IS_LOCATED_IN]->(:City {name: 'Wah_Cantonment'}) WHERE a <> b MATCH p = shortestPath((a)-[:KNOWS*]-(b)) RETURN min(length(p))
```

- Kết quả gold: `[[2]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[null]]`

**PA-05-05** (path) – nhãn `wrong_result`

- Câu hỏi: What is the shortest friendship distance from Ge Hu to anyone who lives in Melbourne?
- Cypher sinh ra:

```cypher
MATCH (start:Person {firstName:"Ge", lastName:"Hu"}), (mel:City {name:"Melbourne"})
MATCH (target:Person)-[:IS_LOCATED_IN]->(mel)
MATCH p=shortestPath((start)-[:KNOWS*]->(target))
RETURN min(length(p)) AS shortestFriendshipDistance
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Ge', lastName: 'Hu'}), (b:Person)-[:IS_LOCATED_IN]->(:City {name: 'Melbourne'}) WHERE a <> b MATCH p = shortestPath((a)-[:KNOWS*]-(b)) RETURN min(length(p))
```

- Kết quả gold: `[[2]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[null]]`

**PA-05-06** (path) – nhãn `timeout`

- Câu hỏi: At least how many friendship links separate Guillermo Rodriguez from a resident of Pavlodar?
- Cypher sinh ra:

```cypher
MATCH (g:Person {firstName:'Guillermo', lastName:'Rodriguez'}), (p:Person)-[:IS_LOCATED_IN]->(c:City {name:'Pavlodar'})
OPTIONAL MATCH path = shortestPath((g)-[:KNOWS*]->(p))
WHERE path IS NOT NULL
RETURN min(length(path)) AS minFriendshipLinks
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Guillermo', lastName: 'Rodriguez'}), (b:Person)-[:IS_LOCATED_IN]->(:City {name: 'Pavlodar'}) WHERE a <> b MATCH p = shortestPath((a)-[:KNOWS*]-(b)) RETURN min(length(p))
```

- Kết quả gold: `[[2]]`
- Lỗi: `Neo.ClientError.Transaction.TransactionTimedOutClientConfiguration: The transaction has been terminated. Retry your operation in a new transaction, and you should see a successful result. The transaction has not completed within the timeout specified at its start by the client. You may want to retry with a longer timeout.`

**PA-05-07** (path) – nhãn `empty_result`

- Câu hỏi: How many friendship steps is Joao Oliveira from the nearest person living in Kelaniya?
- Cypher sinh ra:

```cypher
MATCH (joao:Person {firstName:"Joao", lastName:"Oliveira"}), (kel:City {name:"Kelaniya"})
MATCH (kelPerson:Person)-[:IS_LOCATED_IN]->(kel)
MATCH p=shortestPath((joao)-[:KNOWS*]->(kelPerson))
RETURN length(p) AS friendshipSteps
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Joao', lastName: 'Oliveira'}), (b:Person)-[:IS_LOCATED_IN]->(:City {name: 'Kelaniya'}) WHERE a <> b MATCH p = shortestPath((a)-[:KNOWS*]-(b)) RETURN min(length(p))
```

- Kết quả gold: `[[3]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**PA-05-08** (path) – nhãn `empty_result`

- Câu hỏi: What is the shortest friendship distance from Shweta Kapoor to anyone who lives in Serang?
- Cypher sinh ra:

```cypher
MATCH (shweta:Person {firstName:'Shweta', lastName:'Kapoor'}), 
      (city:Place:City {name:'Serang'}), 
      (target:Person)-[:IS_LOCATED_IN]->(city)
MATCH p = shortestPath((shweta)-[:KNOWS*]->(target))
RETURN length(p) AS distance
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Shweta', lastName: 'Kapoor'}), (b:Person)-[:IS_LOCATED_IN]->(:City {name: 'Serang'}) WHERE a <> b MATCH p = shortestPath((a)-[:KNOWS*]-(b)) RETURN min(length(p))
```

- Kết quả gold: `[[3]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**PA-05-09** (path) – nhãn `empty_result`

- Câu hỏi: At least how many friendship links separate Jun He from a resident of Bender?
- Cypher sinh ra:

```cypher
MATCH (jun:Person {firstName:"Jun", lastName:"He"}), (bender:Place:City {name:"Bender"}), (resident:Person)-[:IS_LOCATED_IN]->(bender)
MATCH p=shortestPath((jun)-[:KNOWS*]->(resident))
RETURN length(p) AS minFriendshipLinks
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'Jun', lastName: 'He'}), (b:Person)-[:IS_LOCATED_IN]->(:City {name: 'Bender'}) WHERE a <> b MATCH p = shortestPath((a)-[:KNOWS*]-(b)) RETURN min(length(p))
```

- Kết quả gold: `[[2]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**PA-05-10** (path) – nhãn `wrong_result`

- Câu hỏi: How many friendship steps is John Murphy from the nearest person living in Agadez?
- Cypher sinh ra:

```cypher
MATCH (john:Person {firstName:"John", lastName:"Murphy"})
MATCH (agadez:City {name:"Agadez"})
MATCH (p:Person)-[:IS_LOCATED_IN]->(agadez)
WHERE p <> john
MATCH path = (john)-[:KNOWS*]->(p)
WITH min(length(path)) AS steps
RETURN steps
```

- Cypher gold:

```cypher
MATCH (a:Person {firstName: 'John', lastName: 'Murphy'}), (b:Person)-[:IS_LOCATED_IN]->(:City {name: 'Agadez'}) WHERE a <> b MATCH p = shortestPath((a)-[:KNOWS*]-(b)) RETURN min(length(p))
```

- Kết quả gold: `[[2]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[null]]`

## temporal (20 câu sai)

**TM-01-01** (temporal) – nhãn `execution_error`

- Câu hỏi: How many posts did Ali Lambo create in 2011?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:'Ali', lastName:'Lambo'})-[:HAS_CREATOR]->(post:Message:Post)
WHERE year(post.creationDate) = 2011
RETURN count(post) AS postCount
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Ali', lastName: 'Lambo'})<-[:HAS_CREATOR]-(p:Post) WHERE p.creationDate.year = 2011 RETURN count(DISTINCT p)
```

- Kết quả gold: `[[120]]`
- Lỗi: `Neo.ClientError.Statement.SyntaxError: Unknown function 'year' (line 2, column 7 (offset: 95))`

**TM-01-04** (temporal) – nhãn `execution_error`

- Câu hỏi: How many posts did John Chatterjee create in 2010?
- Cypher sinh ra:

```cypher
MATCH (post:Message)-[:HAS_CREATOR]->(p:Person {firstName:'John', lastName:'Chatterjee'})
WHERE year(post.creationDate) = 2010
RETURN count(post) AS postsCount
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'John', lastName: 'Chatterjee'})<-[:HAS_CREATOR]-(p:Post) WHERE p.creationDate.year = 2010 RETURN count(DISTINCT p)
```

- Kết quả gold: `[[90]]`
- Lỗi: `Neo.ClientError.Statement.SyntaxError: Unknown function 'year' (line 2, column 7 (offset: 96))`

**TM-01-05** (temporal) – nhãn `wrong_result`

- Câu hỏi: How many posts did Eugene Moke Bemba publish during 2010?
- Cypher sinh ra:

```cypher
MATCH (post:Message:Post)-[:HAS_CREATOR]->(p:Person {firstName:'Eugene', lastName:'Moke Bemba'})
WHERE post.creationDate >= datetime('2010-01-01T00:00:00') AND post.creationDate < datetime('2011-01-01T00:00:00')
RETURN count(post) AS postCount
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Eugene Moke', lastName: 'Bemba'})<-[:HAS_CREATOR]-(p:Post) WHERE p.creationDate.year = 2010 RETURN count(DISTINCT p)
```

- Kết quả gold: `[[1]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[0]]`

**TM-01-07** (temporal) – nhãn `execution_error`

- Câu hỏi: How many posts did Salma Ahmed create in 2012?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:'Salma', lastName:'Ahmed'}), (post:Message:Post)-[:HAS_CREATOR]->(p)
WHERE year(post.creationDate) = 2012
RETURN count(post) AS postCount
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Salma', lastName: 'Ahmed'})<-[:HAS_CREATOR]-(p:Post) WHERE p.creationDate.year = 2012 RETURN count(DISTINCT p)
```

- Kết quả gold: `[[3]]`
- Lỗi: `Neo.ClientError.Statement.SyntaxError: Unknown function 'year' (line 2, column 7 (offset: 102))`

**TM-01-09** (temporal) – nhãn `execution_error`

- Câu hỏi: What is the number of posts written by Mirza Kalich Ali in 2012?
- Cypher sinh ra:

```cypher
MATCH (post:Message:Post)-[:HAS_CREATOR]->(p:Person {firstName:"Mirza", lastName:"Kalich Ali"})
WHERE year(post.creationDate) = 2012
RETURN count(post) AS postCount
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Mirza Kalich', lastName: 'Ali'})<-[:HAS_CREATOR]-(p:Post) WHERE p.creationDate.year = 2012 RETURN count(DISTINCT p)
```

- Kết quả gold: `[[87]]`
- Lỗi: `Neo.ClientError.Statement.SyntaxError: Unknown function 'year' (line 2, column 7 (offset: 102))`

**TM-03-01** (temporal) – nhãn `empty_result`

- Câu hỏi: Which forum did Chito Reyes join first?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:"Chito", lastName:"Reyes"})-[r:HAS_MEMBER]->(f:Forum)
RETURN f.title
ORDER BY r.joinDate ASC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (f:Forum)-[m:HAS_MEMBER]->(:Person {firstName: 'Chito', lastName: 'Reyes'}) RETURN f.title ORDER BY m.joinDate LIMIT 1
```

- Kết quả gold: `[["Wall of Salim Ahmed Binalshibh"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**TM-03-02** (temporal) – nhãn `wrong_result`

- Câu hỏi: What was the first forum that Cedric Ako became a member of?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:"Cedric", lastName:"Ako"})<- [r:HAS_MEMBER]-(f:Forum)
RETURN f
ORDER BY r.joinDate ASC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (f:Forum)-[m:HAS_MEMBER]->(:Person {firstName: 'Cedric', lastName: 'Ako'}) RETURN f.title ORDER BY m.joinDate LIMIT 1
```

- Kết quả gold: `[["Wall of Rafael Alves"]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[{"_labels": ["Forum"], "id": 412316862802, "title": "Wall of Rafael Alves", "creationDate": "2011-02-04T07:42:43.320000000+00:00"}]]`

**TM-03-03** (temporal) – nhãn `empty_result`

- Câu hỏi: Which forum has Otto Herzigová been a member of the longest?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:"Otto", lastName:"Herzigová"})-[r:HAS_MEMBER]->(f:Forum)
RETURN f
ORDER BY r.joinDate ASC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (f:Forum)-[m:HAS_MEMBER]->(:Person {firstName: 'Otto', lastName: 'Herzigová'}) RETURN f.title ORDER BY m.joinDate LIMIT 1
```

- Kết quả gold: `[["Wall of Kamal Aziz"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**TM-03-04** (temporal) – nhãn `empty_result`

- Câu hỏi: Which forum did Anna Kofler join first?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:"Anna", lastName:"Kofler"})-[r:HAS_MEMBER]->(f:Forum)
RETURN f.title
ORDER BY r.joinDate ASC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (f:Forum)-[m:HAS_MEMBER]->(:Person {firstName: 'Anna', lastName: 'Kofler'}) RETURN f.title ORDER BY m.joinDate LIMIT 1
```

- Kết quả gold: `[["Wall of Rudolf Engel"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**TM-03-05** (temporal) – nhãn `wrong_result`

- Câu hỏi: What was the first forum that Takeshi Sato became a member of?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:'Takeshi', lastName:'Sato'})<- [r:HAS_MEMBER]-(f:Forum)
RETURN f
ORDER BY r.joinDate ASC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (f:Forum)-[m:HAS_MEMBER]->(:Person {firstName: 'Takeshi', lastName: 'Sato'}) RETURN f.title ORDER BY m.joinDate LIMIT 1
```

- Kết quả gold: `[["Wall of Bangguo Hu"]]`
- Kết quả sinh ra (1 dòng, tối đa 5 dòng đầu): `[[{"_labels": ["Forum"], "id": 206158445490, "title": "Wall of Bangguo Hu", "creationDate": "2010-07-12T16:17:58.424000000+00:00"}]]`

**TM-03-06** (temporal) – nhãn `empty_result`

- Câu hỏi: Which forum has Hideo Suzuki been a member of the longest?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:"Hideo", lastName:"Suzuki"})-[r:HAS_MEMBER]->(f:Forum)
RETURN f
ORDER BY r.joinDate ASC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (f:Forum)-[m:HAS_MEMBER]->(:Person {firstName: 'Hideo', lastName: 'Suzuki'}) RETURN f.title ORDER BY m.joinDate LIMIT 1
```

- Kết quả gold: `[["Wall of Ken Kato"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**TM-03-07** (temporal) – nhãn `empty_result`

- Câu hỏi: Which forum did Gyula Laszlo join first?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName: 'Gyula', lastName: 'Laszlo'})-[r:HAS_MEMBER]->(f:Forum)
RETURN f.title AS forumTitle
ORDER BY r.joinDate ASC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (f:Forum)-[m:HAS_MEMBER]->(:Person {firstName: 'Gyula', lastName: 'Laszlo'}) RETURN f.title ORDER BY m.joinDate LIMIT 1
```

- Kết quả gold: `[["Wall of Karl Fischer"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**TM-03-08** (temporal) – nhãn `empty_result`

- Câu hỏi: What was the first forum that Ayesha Iqbal became a member of?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:'Ayesha', lastName:'Iqbal'})-[r:HAS_MEMBER]->(f:Forum)
RETURN f
ORDER BY r.joinDate ASC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (f:Forum)-[m:HAS_MEMBER]->(:Person {firstName: 'Ayesha', lastName: 'Iqbal'}) RETURN f.title ORDER BY m.joinDate LIMIT 1
```

- Kết quả gold: `[["Wall of Ashok Singh"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**TM-03-09** (temporal) – nhãn `empty_result`

- Câu hỏi: Which forum has Mohammad Ali Hosseini been a member of the longest?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:'Mohammad', lastName:'Hosseini'})-[r:HAS_MEMBER]->(f:Forum)
RETURN f.title AS forumTitle, r.joinDate AS joinDate
ORDER BY r.joinDate ASC
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (f:Forum)-[m:HAS_MEMBER]->(:Person {firstName: 'Mohammad Ali', lastName: 'Hosseini'}) RETURN f.title ORDER BY m.joinDate LIMIT 1
```

- Kết quả gold: `[["Wall of Alexander Popov"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**TM-03-10** (temporal) – nhãn `empty_result`

- Câu hỏi: Which forum did Arturo Contreras join first?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:"Arturo", lastName:"Contreras"})-[r:HAS_MEMBER]->(f:Forum)
RETURN f.title
ORDER BY r.joinDate
LIMIT 1
```

- Cypher gold:

```cypher
MATCH (f:Forum)-[m:HAS_MEMBER]->(:Person {firstName: 'Arturo', lastName: 'Contreras'}) RETURN f.title ORDER BY m.joinDate LIMIT 1
```

- Kết quả gold: `[["Wall of Jorge Arango"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**TM-05-02** (temporal) – nhãn `execution_error`

- Câu hỏi: Which people became friends with Philibert Roindefo during 2010?
- Cypher sinh ra:

```cypher
MATCH (p:Person)-[r:KNOWS]->(phil:Person {firstName: 'Philibert', lastName: 'Roindefo'})
WHERE year(r.creationDate) = 2010
RETURN p
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Philibert', lastName: 'Roindefo'})-[k:KNOWS]-(f:Person) WHERE k.creationDate.year = 2010 RETURN f.firstName, f.lastName
```

- Kết quả gold: `[["Evangelos", "Dionysiou"], ["Claude", "Aly"], ["Salim Ahmed", "Binalshibh"], ["Peter", "Taylor"], ["Konstantinos", "Antoniou"]] … (7 dòng)`
- Lỗi: `Neo.ClientError.Statement.SyntaxError: Unknown function 'year' (line 2, column 7 (offset: 95))`

**TM-05-05** (temporal) – nhãn `empty_result`

- Câu hỏi: Which people became friends with Fritz Fischer during 2012?
- Cypher sinh ra:

```cypher
MATCH (p:Person)-[k:KNOWS]->(f:Person {firstName:'Fritz', lastName:'Fischer'})
WHERE k.creationDate >= datetime('2012-01-01T00:00:00')
  AND k.creationDate <= datetime('2012-12-31T23:59:59')
RETURN p
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Fritz', lastName: 'Fischer'})-[k:KNOWS]-(f:Person) WHERE k.creationDate.year = 2012 RETURN f.firstName, f.lastName
```

- Kết quả gold: `[["Jana", "Kerndlova"], ["Shweta", "Sharma"]]`
- Kết quả sinh ra (0 dòng, tối đa 5 dòng đầu): `[]`

**TM-05-06** (temporal) – nhãn `no_cypher`

- Câu hỏi: List the new friends Ali Lambo made in 2011.
- Cypher sinh ra:

```cypher
(trống)
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Ali', lastName: 'Lambo'})-[k:KNOWS]-(f:Person) WHERE k.creationDate.year = 2011 RETURN f.firstName, f.lastName
```

- Kết quả gold: `[["Michal", "Kaminski"], ["Takeshi", "Yamamoto"], ["Bruna", "Costa"], ["Rafael", "Alves"], ["Eduardo", "Araya"]] … (10 dòng)`

**TM-05-07** (temporal) – nhãn `execution_error`

- Câu hỏi: Who did Hamani Lambo become friends with in 2011?
- Cypher sinh ra:

```cypher
MATCH (p:Person {firstName:"Hamani", lastName:"Lambo"})-[:KNOWS {creationDate: rDate}]->(friend)
WHERE rDate >= datetime("2011-01-01T00:00:00") AND rDate < datetime("2012-01-01T00:00:00")
RETURN friend.firstName AS firstName, friend.lastName AS lastName
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Hamani', lastName: 'Lambo'})-[k:KNOWS]-(f:Person) WHERE k.creationDate.year = 2011 RETURN f.firstName, f.lastName
```

- Kết quả gold: `[["Jack", "Wilson"], ["Ammar", "David"], ["Mario", "Santos"], ["John", "Wilson"], ["Jose", "Costa"]] … (7 dòng)`
- Lỗi: `Neo.ClientError.Statement.SyntaxError: Variable `rDate` not defined (line 1, column 80 (offset: 79))`

**TM-05-10** (temporal) – nhãn `no_cypher`

- Câu hỏi: Who did Eugene Moke Bemba become friends with in 2012?
- Cypher sinh ra:

```cypher
(trống)
```

- Cypher gold:

```cypher
MATCH (:Person {firstName: 'Eugene Moke', lastName: 'Bemba'})-[k:KNOWS]-(f:Person) WHERE k.creationDate.year = 2012 RETURN f.firstName, f.lastName
```

- Kết quả gold: `[["Emperor of Brazil", "Dom Pedro II"], ["Andrei", "Kahnovich"]]`
