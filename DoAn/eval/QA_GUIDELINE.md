# Guideline xây dựng bộ câu hỏi QA (Nhóm 13 – A.22)

Mục tiêu: 6 người cùng viết câu hỏi nhưng ra **một bộ dữ liệu nhất quán**, mỗi câu có **đúng một đáp án**, và **không rò rỉ** giữa tập dev và tập test. Mọi câu hỏi phải tuân theo file này; chỗ nào chưa rõ thì thảo luận rồi **cập nhật file**, không tự quyết riêng.

---

## 1. Năm loại câu hỏi

| Loại | Định nghĩa | Ví dụ |
|---|---|---|
| `lookup` | Đọc thuộc tính / hàng xóm 1 bước của một thực thể | *Which city does Alfred Hoffmann live in?* |
| `aggregation` | Đếm, tìm lớn nhất/nhỏ nhất trên toàn đồ thị hoặc một nhóm | *Which forum has the most members?* |
| `multi_hop` | Đi qua ≥ 2 quan hệ | *At which university do most of Alfred Hoffmann's friends study?* |
| `path` | Đường đi / khoảng cách giữa hai thực thể | *What is the length of the shortest friendship path between A and B?* |
| `temporal` | Có điều kiện thời gian (năm, khoảng ngày) | *How many posts did Anupam Reddy create in 2011?* |

Một câu chỉ thuộc **một** loại chính. Nếu vừa multi-hop vừa temporal → xếp theo yếu tố khó nhất và ghi chú trong trường `note`.

## 2. Quy ước ngữ nghĩa (bắt buộc, áp dụng cho cả câu hỏi và Cypher gold)

| Cụm từ trong câu hỏi | Nghĩa thống nhất | Cypher |
|---|---|---|
| "friend(s) of X", "X knows" | Quan hệ KNOWS **không xét chiều** | `(x)-[:KNOWS]-(f)` |
| "friends of friends of X" | Cách đúng 2 bước, **không gồm** X và bạn trực tiếp của X | `-[:KNOWS*2]-` + `WHERE x <> p AND NOT (p)-[:KNOWS]-(x)` |
| "post(s)" | Chỉ `Post` | `(:Post)` |
| "comment(s)" | Chỉ `Comment` | `(:Comment)` |
| "message(s)" | Cả Post và Comment | `(:Message)` |
| "lives in <country>" | Person → City → Country | `(:Person)-[:IS_LOCATED_IN]->(:City)-[:IS_PART_OF]->(:Country)` |
| "works at" / "studies at" | `WORK_AT` → Company / `STUDY_AT` → University | |
| "in <year>" | Theo **UTC**, năm của `creationDate` | `m.creationDate.year = 2011` |
| "how many people/posts…" | Luôn đếm **không trùng** | `count(DISTINCT x)` |
| "the most / the largest" | Trả **một** kết quả duy nhất | `ORDER BY n DESC LIMIT 1` |

Lý do KNOWS phải không xét chiều: trong dữ liệu mỗi cặp bạn bè chỉ được lưu **một cạnh theo một chiều** (đã kiểm tra trên `person_knows_person_0_0.csv`: 14.073 cạnh, 0 cặp lưu cả hai chiều). Viết `-[:KNOWS]->` sẽ bỏ sót khoảng một nửa số bạn.

Tên trong câu hỏi viết **tự nhiên** ("United States", "Muammar Gaddafi"); Cypher gold dùng **giá trị thật trong DB** (`United_States`, `Muammar_Gaddafi`).

## 3. Mỗi câu phải có đúng một đáp án — loại bỏ nếu

1. Đáp án **rỗng** hoặc bằng **0** (câu Cypher sai cũng dễ ra 0 → không phân biệt được).
2. Câu "the most / the least" bị **đồng hạng** ở vị trí đầu.
3. Người được nhắc tới **trùng họ tên** với người khác (DB có 166 họ tên bị trùng) — kiểm tra bằng
   `MATCH (p:Person {firstName:$f, lastName:$l}) RETURN count(p)` phải bằng 1.
4. Câu **mơ hồ**: hai người đọc có thể hiểu khác nhau mà quy ước ở mục 2 chưa giải quyết.
5. Đáp án quá lớn (> 20 dòng) với câu dạng liệt kê → đổi thành câu đếm.
6. Truy vấn gold chạy quá 10 giây.

## 4. Định dạng một câu hỏi

```json
{
  "id": "MH-03-07",
  "template_id": "MH-03",
  "type": "multi_hop",
  "question": "At which university do the largest number of Alfred Hoffmann's friends study?",
  "gold": "MATCH (:Person {firstName:'Alfred', lastName:'Hoffmann'})-[:KNOWS]-(f:Person)-[:STUDY_AT]->(u:University) RETURN u.name, count(DISTINCT f) AS n ORDER BY n DESC LIMIT 1",
  "params": {"firstName": "Alfred", "lastName": "Hoffmann"},
  "author": "Vũ",
  "checked_by": "",
  "note": ""
}
```

- `RETURN` của gold: **cột đáp án trước**, cột đếm phụ đặt tên `n` (script chấm điểm bỏ qua cột `n`).
- **Không ghi đáp án bằng tay** — đáp án luôn là kết quả chạy `gold` trên Neo4j.
- `id` = `template_id` + số thứ tự.

## 5. Quy trình

1. **Viết template** (mỗi người phụ trách một loại, 4–6 template/loại): câu hỏi có chỗ trống + Cypher có tham số. **Tự viết**, không chép/diễn đạt lại các truy vấn Interactive/BI công khai của LDBC (tránh việc LLM đã thấy chúng khi huấn luyện).
2. **Viết 2–3 cách diễn đạt** khác nhau cho mỗi template để câu hỏi không lặp một khuôn.
3. **Sinh câu** bằng script: lấy tham số ngẫu nhiên từ đồ thị (seed cố định), ~8–10 câu/template.
4. **Lọc tự động** theo mục 3 + kiểm tra cú pháp, câu trùng nhau.
5. **Kiểm tra chéo** (mục 6).
6. **Chia dev/test** (mục 7) rồi **đóng băng** tập test.

## 6. Kiểm tra chéo (giảm lỗi đáp án)

- Lấy ngẫu nhiên **20% câu mỗi loại**; một người **khác tác giả** đọc câu hỏi và **tự viết Cypher độc lập** (không xem gold).
- Chạy cả hai: kết quả khớp → đồng thuận. Báo **tỉ lệ đồng thuận** trong báo cáo.
- Không khớp → hai người thảo luận: lỗi do gold thì sửa gold; do câu mơ hồ thì sửa câu hoặc bổ sung quy ước ở mục 2; không thống nhất được thì **loại câu**.
- Nếu tỉ lệ đồng thuận của một loại < 90% → kiểm tra lại toàn bộ loại đó.

## 7. Chia dev/test và chống rò rỉ dữ liệu

- Chia **theo template**: mọi câu sinh từ một template nằm cùng một phía. Dev ≈ 30% template, test ≈ 70%, mỗi loại câu hỏi đều có mặt ở cả hai phía.
- **Thực thể không trùng**: người/tag/forum đã xuất hiện trong dev thì không dùng làm tham số trong test.
- **Ví dụ few-shot, chỉnh prompt, viết luật cho baseline rule-based (B0)**: chỉ dùng **dev**.
- **Test chạy một lần cuối** cho mỗi cấu hình; không sửa prompt/luật sau khi xem kết quả test.
- **Vòng tự sửa lỗi** của pipeline chỉ được nhận thông báo lỗi thực thi / kết quả rỗng — **không bao giờ** nhận đáp án gold.
- Đóng băng test: lưu file `test.json` kèm mã băm (SHA-256) trong báo cáo; mọi thay đổi sau đó phải ghi lý do.

## 8. Checklist trước khi nộp câu hỏi

- [ ] Đúng một loại, đúng quy ước mục 2
- [ ] Gold chạy được, đáp án không rỗng/0, không đồng hạng, thực thể không trùng tên
- [ ] Câu hỏi tự nhiên, không lộ tên nhãn/thuộc tính kỹ thuật (không viết "IS_LOCATED_IN", "firstName")
- [ ] Không chép truy vấn LDBC công khai
- [ ] Đã điền `author`; câu thuộc mẫu kiểm tra chéo đã có `checked_by`
