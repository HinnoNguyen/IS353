# Thống kê đồ thị LDBC SNB SF0.1 trong Neo4j

## Node theo nhãn

| label | count |
|---|---|
| Message | 286,744 |
| Comment | 151,043 |
| Post | 135,701 |
| Tag | 16,080 |
| Forum | 13,750 |
| Organisation | 7,955 |
| University | 6,380 |
| Company | 1,575 |
| Person | 1,528 |
| Place | 1,460 |
| City | 1,343 |
| Country | 111 |
| TagClass | 71 |
| Continent | 6 |

## Cạnh theo kiểu (nguồn → đích)

| pattern | count |
|---|---|
| Comment -[HAS_TAG]-> Tag | 191,303 |
| Comment -[HAS_CREATOR]-> Person | 151,043 |
| Comment -[IS_LOCATED_IN]-> Place | 151,043 |
| Forum -[CONTAINER_OF]-> Post | 135,701 |
| Post -[HAS_CREATOR]-> Person | 135,701 |
| Post -[IS_LOCATED_IN]-> Place | 135,701 |
| Forum -[HAS_MEMBER]-> Person | 123,268 |
| Comment -[REPLY_OF]-> Comment | 76,787 |
| Comment -[REPLY_OF]-> Post | 74,256 |
| Person -[LIKES]-> Comment | 62,225 |
| Post -[HAS_TAG]-> Tag | 51,118 |
| Forum -[HAS_TAG]-> Tag | 47,697 |
| Person -[LIKES]-> Post | 47,215 |
| Person -[HAS_INTEREST]-> Tag | 35,475 |
| Tag -[HAS_TYPE]-> TagClass | 16,080 |
| Person -[KNOWS]-> Person | 14,073 |
| Forum -[HAS_MODERATOR]-> Person | 13,750 |
| Organisation -[IS_LOCATED_IN]-> Place | 7,955 |
| Person -[WORK_AT]-> Organisation | 3,313 |
| Person -[IS_LOCATED_IN]-> Place | 1,528 |
| Place -[IS_PART_OF]-> Place | 1,454 |
| Person -[STUDY_AT]-> Organisation | 1,209 |
| TagClass -[IS_SUBCLASS_OF]-> TagClass | 70 |

## Tổng quan

| nodes | edges |
|---|---|
| 327,588 | 1,477,965 |

## Mạng bạn bè KNOWS (vô hướng)

| persons | min_degree | max_degree | avg_degree | median_degree | isolated |
|---|---|---|---|---|---|
| 1,528 | 0 | 340 | 18.42 | 9 | 171 |

## Khoảng thời gian dữ liệu

| first_message | last_message |
|---|---|
| 2010-01-06 | 2012-09-13 |

## Top 5 người nhiều bạn nhất

| person | friends |
|---|---|
| Emperor of Brazil Dom Pedro II (id 26388279067534) | 340 |
| Alfred Hoffmann (id 32985348834375) | 338 |
| K. Bose (id 2199023256816) | 269 |
| The Kunda (id 24189255811566) | 256 |
| Salim Ahmed Binalshibh (id 6597069767242) | 230 |
