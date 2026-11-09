# Báo cáo Kiểm toán Chất lượng & Độ mơ hồ Tập Test (Nội bộ Bảo & Ân)

> **CẢNH BÁO BẢO MẬT (ANTI-LEAKAGE RULE):**
> File báo cáo này chứa thông tin chi tiết, mã ID, câu hỏi và Cypher của tập kiểm thử (**Test Set**). Theo quy tắc chống rò rỉ tại Mục 2 của `GIAO_VIEC_KIEM_TRA_BENCHMARK.md`:
> - **CHỈ CÓ BẢO VÀ ÂN ĐƯỢC PHÉP ĐỌC FILE NÀY.**
> - **VŨ, KHÔI, BẰNG TUYỆT ĐỐI KHÔNG MỞ, KHÔNG ĐỌC.**
> - Mọi nội dung chi tiết của câu test không được gửi qua chat nhóm hoặc đưa vào các tài liệu mở.

---

## 1. Tổng quan kiểm toán tập Test

- **Người thực hiện:** Đặng Thiên Ân (MSSV: 23520003) - Task T57.
- **Tập dữ liệu:** `DoAn/eval/questions/test.json` (150 câu, 15 template: `LK-01, 02, 05`, `AG-02, 04, 05`, `MH-02, 04, 05`, `PA-02, 04, 05`, `TM-01, 03, 05`).
- **Nguồn dữ liệu đánh giá:** 
  - B3 (`openai/gpt-oss-120b`, zero-shot): `results/runs/test/b1_zeroshot__openai-gpt-oss-120b__run{1,2,3}.json`
  - B1 (`openai/gpt-oss-20b`, zero-shot): `results/runs/test/b1_zeroshot__openai-gpt-oss-20b__run{1,2}.json`
  - Khung chấm Oracle: `results/runs/test/oracle__none__run1.json`

---

## 2. Phân tích các câu sai "cứng đầu" của B3 (Sai ≥ 2/3 lượt chạy)

Trên 150 câu test, model mạnh nhất **B3 (gpt-oss-120b)** đạt trung bình 78.9% (116/150 ở run 1, 121/150 ở run 2, 118/150 ở run 3).
Có chính xác **30 câu hỏi** mà B3 bị sai từ 2 lượt trở lên (**stubborn errors**). Dưới đây là phân loại chi tiết từng câu theo 5 nhãn chuẩn:

| Nhãn | Số lượng | Tỉ lệ trong nhóm sai | Ý nghĩa cốt lõi |
|---|---|---|---|
| `be_mat` | **23** | 76.7% | Logic Cypher đúng nhưng sai cách viết giá trị (bẫy dấu `_`, tách sai họ tên đệm) |
| `model_sai` | **6** | 20.0% | Model đảo chiều quan hệ, lỗi cú pháp gán biến thuộc tính, sai kiểu DateTime vs Date |
| `mo_ho` | **1** | 3.3% | Hòa hạng (tie-break) không có sắp xếp phụ hoặc mơ hồ đếm DISTINCT |
| `gold_sai` | **0** | 0.0% | Không có Cypher gold nào vi phạm hoàn toàn logic đồ thị |
| `cham_qua_chat` | Ghi nhận ở B1 | - | Trả về cả node thay vì thuộc tính `name` (gặp ở B1: `LK-02-09`) |

---

### 2.1. Phân tích tâm điểm: Template AG-05 (0% ở cả B1 và B3 trên mọi lượt chạy)

Template `AG-05` ("How many posts are tagged with {tag}?") gồm 10 câu test (`AG-05-01` đến `AG-05-10`).
- **Hiện tượng:** Cả B1 và B3 đều đạt **0/10 (0.0%)** trên tất cả các lượt chạy độc lập.
- **Nguyên nhân gốc rễ:**
  - Trong Neo4j LDBC SNB SF0.1, nhãn `Tag` lưu thuộc tính `name` theo chuẩn tên định danh có dấu gạch dưới `_`, ví dụ: `'Phil_Spector'`, `'Bob_Dylan'`, `'Left_Behind'`, `'Brian_Eno'`.
  - Trong câu hỏi tự nhiên của benchmark, tên tag được hiển thị với dấu cách tự nhiên và bao quanh bởi dấu ngoặc kép: `"Phil Spector"`, `"Left Behind"`, `"Brian Eno"`.
  - Không có bất kỳ dòng nào trong prompt zero-shot của B1/B3 cung cấp quy ước rằng tên Tag trong cơ sở dữ liệu phải nối bằng dấu `_`.
  - Do đó, LLM sinh ra truy vấn: `MATCH (m:Post)-[:HAS_TAG]->(t:Tag {name: 'Phil Spector'}) RETURN count(m)`. Truy vấn này hoàn toàn chính xác về mặt logic và ngữ nghĩa, nhưng khớp literal thất bại trong Neo4j và trả về `0` dòng (hoặc count = 0), bị judge kết luận `empty_result` hoặc `wrong_result`.
- **Kết luận nhãn:** Toàn bộ 10 câu `AG-05` được gán nhãn **`be_mat`**.

---

### 2.2. Danh sách chi tiết 30 câu sai cứng đầu của B3 kèm nhãn

#### Nhóm 1: Bẫy dấu gạch dưới `_` trong tên thực thể (18 câu) - Nhãn `be_mat`

1. **`AG-02-02`** (`be_mat`): In United Kingdom, which city do the largest number of people live in?
   - Tham số DB: `Country {name: 'United_Kingdom'}`. Model viết: `'United Kingdom'`. Kết quả: `empty_result`.
2. **`AG-02-03`** (`be_mat`): What is the most populated city of Democratic Republic of the Congo in the network?
   - Tham số DB: `Country {name: 'Democratic_Republic_of_the_Congo'}`. Model viết: `'Democratic Republic of the Congo'`.
3. **`AG-02-04`** (`be_mat`): Which city in Czech Republic has the most residents?
   - Tham số DB: `Country {name: 'Czech_Republic'}`. Model viết: `'Czech Republic'`.
4. **`AG-04-02`** (`be_mat`): In Czech Republic, which tag was used in the highest number of posts?
   - Tham số DB: `Country {name: 'Czech_Republic'}`. Model viết: `'Czech Republic'`.
5. **`AG-04-03`** (`be_mat`): Which tag was used the most in posts by people in South Korea?
   - Tham số DB: `Country {name: 'South_Korea'}`. Model viết: `'South Korea'`.
6. **`AG-04-07`** (`be_mat`): What tag appears most often on posts created by people living in Sri Lanka?
   - Tham số DB: `Country {name: 'Sri_Lanka'}`. Model viết: `'Sri Lanka'`.
7. **`AG-05-01`** (`be_mat`): How many posts are tagged with "Phil Spector"? (DB: `Phil_Spector`)
8. **`AG-05-02`** (`be_mat`): What is the count of posts that have the "Left Behind" tag? (DB: `Left_Behind`)
9. **`AG-05-03`** (`be_mat`): Count the number of posts with tag "Color Me Barbra". (DB: `Color_Me_Barbra`)
10. **`AG-05-04`** (`be_mat`): How many posts are tagged with "William Randolph Hearst"? (DB: `William_Randolph_Hearst`)
11. **`AG-05-05`** (`be_mat`): What is the count of posts that have the "Christopher Lee" tag? (DB: `Christopher_Lee`)
12. **`AG-05-06`** (`be_mat`): Count the number of posts with tag "Kaia Kanepi". (DB: `Kaia_Kanepi`)
13. **`AG-05-07`** (`be_mat`): How many posts are tagged with "Pierre Trudeau"? (DB: `Pierre_Trudeau`)
14. **`AG-05-08`** (`be_mat`): What is the count of posts that have the "I Walk the Line" tag? (DB: `I_Walk_the_Line`)
15. **`AG-05-09`** (`be_mat`): Count the number of posts with tag "Good Vibrations". (DB: `Good_Vibrations`)
16. **`AG-05-10`** (`be_mat`): How many posts are tagged with "Brian Eno"? (DB: `Brian_Eno`)
17. **`PA-05-02`** (`be_mat`): What is the length of the shortest path between Dum Dum and Saint-Denis?
   - Tham số DB: `City {name: 'Dum_Dum'}`. Model viết: `'Dum Dum'`.
18. **`PA-05-04`** (`be_mat`): How long is the shortest path from Wah Cantonment to Niterói?
   - Tham số DB: `City {name: 'Wah_Cantonment'}`. Model viết: `'Wah Cantonment'`.

---

#### Nhóm 2: Tách họ tên người không chuẩn (5 câu) - Nhãn `be_mat`

Khi tên người gồm 3 hoặc 4 từ, câu hỏi tự nhiên không chỉ rõ đâu là `firstName` và đâu là `lastName`. Schema LDBC tách bất đối xứng khiến model đoán sai:
19. **`LK-02-03`** (`be_mat`): Who are the employers of Esti Mamo Dego?
    - DB: `firstName: 'Esti Mamo', lastName: 'Dego'`. Model run 2 & 3: `firstName: 'Esti', lastName: 'Dego'`. (Riêng run 1 model dùng `CONTAINS` nên tình cờ đúng).
20. **`PA-02-04`** (`be_mat`): How many different shortest friendship paths connect David Agudelo and Mamoon Eshaq 0 Amin?
    - DB: `firstName: 'Mamoon Eshaq 0', lastName: 'Amin'`. Model: `firstName: 'Mamoon', lastName: 'Eshaq 0 Amin'`.
21. **`TM-01-05`** (`be_mat`): How many posts did Eugene Moke Bemba publish during 2010?
    - DB: `firstName: 'Eugene Moke', lastName: 'Bemba'`. Model: `firstName: 'Eugene', lastName: 'Moke Bemba'`.
22. **`TM-01-09`** (`be_mat`): What is the number of posts written by Mirza Kalich Ali in 2012?
    - DB: `firstName: 'Mirza Kalich', lastName: 'Ali'`. Model run 2 & 3: `firstName: 'Mirza', lastName: 'Kalich Ali'`.
23. **`TM-05-10`** (`be_mat`): Who did Eugene Moke Bemba become friends with in 2012?
    - DB: `firstName: 'Eugene Moke', lastName: 'Bemba'`. Model: `firstName: 'Eugene', lastName: 'Moke Bemba'`.

---

#### Nhóm 3: Sai sót logic và cú pháp của Model (6 câu) - Nhãn `model_sai`

24. **`TM-03-03`** (`model_sai`): Which forum has Otto Herzigová been a member of the longest?
    - Model run 1 & 3: Viết đảo chiều quan hệ: `(p:Person)-[:HAS_MEMBER]->(f:Forum)`. Trong schema LDBC, chiều hợp lệ là `(f:Forum)-[:HAS_MEMBER]->(p:Person)`.
25. **`TM-05-02`** (`model_sai`): Which people became friends with Philibert Roindefo during 2010?
    - Model run 1 & 3: Lọc thời gian bằng `k.creationDate >= date('2010-01-01')`. Trong Neo4j, `creationDate` là `DateTime`, việc so sánh `DateTime >= Date` dẫn đến lỗi kiểu hoặc trả về tập rỗng.
26. **`TM-05-03`** (`model_sai`): List the new friends Christos Angello made in 2012.
    - Model run 1 & 2: Viết cú pháp không hợp lệ trong Cypher: `-[:KNOWS {creationDate: cd}]->` thay vì gán biến quan hệ `-[k:KNOWS]-`.
27. **`TM-05-07`** (`model_sai`): Who did Hamani Lambo become friends with in 2011?
    - Model run 1 & 2 bị lỗi cú pháp tương tự câu TM-05-03. Run 3 thêm cột trả về không cần thiết.
28. **`TM-05-08`** (`model_sai`): Which people became friends with Werner Muller during 2010?
    - Model run 1 & 3: Dùng hàm `date('2010-01-01')` so sánh với `DateTime`.
29. **`TM-05-09`** (`model_sai`): List the new friends Gabriela Rodriguez made in 2012.
    - Model run 1 & 2: Lỗi cú pháp `[:KNOWS {creationDate: cd}]`.

---

#### Nhóm 4: Mơ hồ phân định thứ hạng (1 câu) - Nhãn `mo_ho`

30. **`MH-02-06`** (`mo_ho`): Among the friends of Michel David, which university has the most students?
    - Gold: `ORDER BY n DESC LIMIT 1`.
    - Khi có nhiều trường đại học cùng có số lượng sinh viên bằng nhau (ví dụ đều là 1), việc không có tiêu chí phụ sắp xếp theo tên (`ORDER BY n DESC, u.name ASC`) khiến Neo4j trả về trường đại học phụ thuộc vào thứ tự duyệt đồ thị, dẫn đến model bị phạt `wrong_result`.

---

## 3. Rà soát chất lượng câu chữ trên toàn bộ 242 câu

Qua rà soát chi tiết cả 92 câu dev và 150 câu test:

### 3.1. Hiện tượng gợi ý lộ liễu (Prompt Leakage)
- Có đúng **20 câu hỏi** (10 câu `AG-03` ở dev và 10 câu `AG-05` ở test) sử dụng dấu ngoặc kép bọc tên tag: `"{tag}"`.
- *Đánh giá:* Dấu ngoặc kép đóng vai trò như một "nhãn biên thực thể" nhân tạo, giúp model trích xuất tên tag dễ dàng hơn rất nhiều so với câu hỏi tự nhiên thực tế.

### 3.2. Lỗi ngữ pháp và sự mất tự nhiên trong ngôn ngữ
- **Thiếu mạo từ xác định "the":**
  - Các câu chứa tên quốc gia có danh từ chung (`United Kingdom`, `Czech Republic`, `Democratic Republic of the Congo`) bị thiếu "the", ví dụ:
    - `AG-02-02`: *"In United Kingdom..."* -> Chuẩn: *"In the United Kingdom..."*
    - `AG-02-04`: *"Which city in Czech Republic..."* -> Chuẩn: *"in the Czech Republic..."*
- **Sử dụng đại từ số ít không tự nhiên:**
  - `MH-03-02, 05, 08`: *"Who among [Person]'s friends lives in the same city as them?"* -> Sử dụng "as them" thay vì "as him/her" hoặc "shares their city" gây lấn cấn về ngữ nghĩa số ít/số nhiều.
- **Câu thức mệnh lệnh kết thúc bằng dấu chấm thay vì dấu hỏi:**
  - 18 câu dạng `"List the friends..."`, `"Where does X live? Give the city."` thiếu dấu hỏi chấm ở cuối hoặc ghép câu cụt.

---

## 4. Tóm lược kiến nghị kỹ thuật gửi Trưởng nhóm (Bảo)

1. **Khắc phục bẫy `_` ngay trong Judge:**
   - Trong hàm so sánh kết quả hoặc so sánh chuỗi literal của `judge`, tự động thay thế `_` thành khoảng trắng.
   - Hoặc thêm 1 dòng quy ước trong prompt: *"Database entity names use underscores instead of spaces (e.g. 'United_Kingdom', 'Phil_Spector')"*. Điều này sẽ phục hồi ngay lập tức 18 câu test cho các model baseline.
2. **Xử lý tách họ tên người:**
   - Trong judge, chấp nhận kết quả nếu model dùng `WHERE p.firstName + ' ' + p.lastName = $fullName` hoặc cho phép trả về `p.name`.
3. **Bổ sung sắp xếp phụ cho các câu "most":**
   - Thêm `ORDER BY n DESC, entity.name ASC LIMIT 1` để tránh lỗi do thứ tự trả về không tất định khi hòa hạng.
