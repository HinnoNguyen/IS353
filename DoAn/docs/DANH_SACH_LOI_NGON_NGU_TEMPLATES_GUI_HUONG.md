# Danh sách Template Cũ có Lỗi Ngôn ngữ & Khuyến nghị Xây dựng Test2 (Gửi Hương)

> **Người lập:** Ân (Phụ trách kiểm toán chất lượng benchmark T57 & T62a, Module B T32)  
> **Người nhận:** Hương (Phụ trách xây dựng bộ câu hỏi kiểm thử mù Test2 - T58)  
> **Thời điểm cập nhật:** 23/11/2026 (Hạn chót: 24/11/2026)  
> **Mục đích:** Bàn giao danh sách toàn bộ các khiếm khuyết ngôn ngữ tiếng Anh, điểm mơ hồ ngữ nghĩa Nhóm (i) và lỗi cú pháp diễn đạt trong 25 template cũ (thuộc 5 nhóm câu hỏi) nhằm giúp Hương chuẩn hóa câu từ khi sinh câu hỏi cho tập **Test2**, bảo đảm tính chặt chẽ và không lặp lại các bẫy chất lượng của benchmark cũ.

---

## 1. Bảng tổng hợp chi tiết lỗi ngôn ngữ theo từng Template cũ

Dưới đây là rà soát chi tiết trên toàn bộ 25 template cũ của 5 nhóm câu hỏi:

### A. Nhóm Aggregation (Gom nhóm & Thống kê)

| Mã Template | Câu tiếng Anh trong template cũ | Lỗi ngôn ngữ / Ngữ nghĩa / Cú pháp | Đề xuất sửa đổi chuẩn hóa cho Test2 |
|---|---|---|---|
| **AG-01** | *"How many people live in {country}?"*<br>*"What is the number of people living in {country}?"*<br>*"How many residents of {country} are there in the network?"* | **Thiếu mạo từ xác định "the":** Khi `{country}` là quốc gia có danh từ tập hợp (ví dụ: *United Kingdom*, *United States*, *Czech Republic*, *Netherlands*), câu trở thành *"live in United Kingdom"* (sai ngữ pháp tiếng Anh). | Thêm quy tắc chèn mạo từ *"the"* trước các quốc gia danh từ tập hợp, hoặc điều chỉnh: *"How many people live in the country of {country}?"* |
| **AG-02** | *"In {country}, which city do the largest number of people live in?"* | **Lỗi hòa hợp chủ vị (Subject-Verb agreement):** Cụm *"the largest number of people"* làm chủ ngữ, dùng trợ động từ *"do"* thiếu tự nhiên; vị trí giới từ *"in"* cuối câu tạo cấu trúc cồng kềnh.<br>**Thiếu tiêu chí hòa hạng (Tie-break):** Câu hỏi "most" nếu có 2 thành phố bằng điểm sẽ phụ thuộc vào thứ tự duyệt đồ thị ngẫu nhiên. | Sửa thành: *"In which city of {country} does the largest number of people reside?"*<br>Bổ sung tiêu chí hòa hạng: *"If tied, rank alphabetically by city name."* |
| **AG-03** | *"How many posts are tagged with \"{tag}\"?"*<br>*"What is the number of posts that have the tag \"{tag}\"?"* | **Mơ hồ ngữ nghĩa Nhóm (i):** Từ *"posts"* trong LDBC SNB dễ gây hiểu nhầm: chỉ tính bài đăng gốc (`:Post`) hay tính cả bình luận (`:Comment` cũng thuộc lớp cha `:Message`). | Làm rõ tường minh: *"How many posts (excluding comments) are tagged with \"{tag}\"?"* hoặc *"How many original posts carry the tag \"{tag}\"?"* |
| **AG-04** | *"Which company in {country} has the most employees?"*<br>*"What is the biggest employer in {country}, by number of employees?"* | **Thiếu mạo từ "the":** Tương tự AG-01 khi gặp *United Kingdom*.<br>**Thiếu tiêu chí hòa hạng:** Chưa có quy định phụ khi 2 công ty có cùng số lượng nhân viên cao nhất. | Sửa thành: *"Among companies located in {the_country}, which one employs the highest number of people? (If tied, choose alphabetically by company name)"*. |
| **AG-05** | *"How many people are interested in \"{tag}\"?"*<br>*"What is the number of people with an interest in \"{tag}\"?"* | **Mơ hồ ngữ nghĩa Nhóm (i):** *"interested in"* bị đa nghĩa: là người dùng có sở thích trong hồ sơ cá nhân (`(:Person)-[:HAS_INTEREST]->(:Tag)`) hay là người like bài viết gắn tag (`(:Person)-[:LIKES]->(:Post)-[:HAS_TAG]->(:Tag)`). | Làm rõ trực tiếp: *"How many people have the tag \"{tag}\" listed in their profile interests?"* |

---

### B. Nhóm Lookup (Tra cứu thuộc tính trực tiếp)

| Mã Template | Câu tiếng Anh trong template cũ | Lỗi ngôn ngữ / Ngữ nghĩa / Cú pháp | Đề xuất sửa đổi chuẩn hóa cho Test2 |
|---|---|---|---|
| **LK-01** | *"Where does {firstName} {lastName} live? Give the city."* | **Câu ghép mệnh lệnh kèm dấu chấm:** Câu kết hợp giữa câu hỏi và câu mệnh lệnh cộc lốc (*"Give the city."*), làm lệch cấu trúc câu hỏi tự nhiên chuẩn. | Chuẩn hóa thành 1 câu hỏi duy nhất: *"In which city does {firstName} {lastName} reside?"* |
| **LK-02** | *"List the companies where {firstName} {lastName} works."* | **Câu mệnh lệnh kết thúc bằng dấu chấm ".":** Bộ câu hỏi QA chuẩn cần nhất quán định dạng câu hỏi (chấm hỏi "?") thay vì xen lẫn câu mệnh lệnh kết thúc bằng dấu chấm. | Đổi sang câu hỏi: *"Which companies does {firstName} {lastName} work for?"* |
| **LK-03** | *"At which university is {firstName} {lastName} a student?"* | **Lệch thì thời gian (Tense mismatch):** Quan hệ `STUDY_AT` trong LDBC là lịch sử học tập (có `classYear`), dùng *"is a student"* (hiện tại đơn) có thể không phù hợp với cựu sinh viên. | Dùng thì quá khứ/hoàn thành hoặc trung tính: *"Which university did {firstName} {lastName} attend?"* |
| **LK-04** | *"What is {firstName} {lastName}'s birthday?"* | Không có lỗi ngữ pháp nghiêm trọng; thuộc tính `birthday` kiểu Date. | Giữ nguyên: *"What is the date of birth of {firstName} {lastName}?"* |
| **LK-05** | *"{city} is a city of which country?"* | **Trật tự từ không tự nhiên (Inverted statement as question):** Câu khẳng định gắn từ nghi vấn ở đuôi mang văn phong nói, thiếu trang trọng. | Sửa thành: *"Which country is the city of {city} located in?"* hoặc *"In which country does the city of {city} lie?"* |

---

### C. Nhóm Multi-hop (Đa chặng)

| Mã Template | Câu tiếng Anh trong template cũ | Lỗi ngôn ngữ / Ngữ nghĩa / Cú pháp | Đề xuất sửa đổi chuẩn hóa cho Test2 |
|---|---|---|---|
| **MH-01** | *"{firstName} {lastName} lives in which country?"* | **Văn phong đàm thoại (Colloquial echo question):** Trật tự từ chưa chuẩn mực cho câu hỏi trích xuất thông tin. | Chuẩn hóa: *"In which country does {firstName} {lastName} live?"* |
| **MH-02** | *"At which university do the largest number of {firstName} {lastName}'s friends study?"* | **Thiếu tiêu chí hòa hạng (Tie-break):** Nếu số bạn bè học tại 2 trường đại học bằng nhau, không xác định được trường nào đứng đầu. | Thêm tiêu chí phụ: *"Which university is attended by the greatest number of {firstName} {lastName}'s friends? If tied, select the one that comes first alphabetically."* |
| **MH-03** | *"Who among {firstName} {lastName}'s friends lives in the same city as them?"*<br>*"List the friends of {firstName} {lastName} who share their city of residence."* | **Lệch ngữ pháp số ít/số nhiều (Pronoun mismatch):** Dùng *"as them"* đi kèm với động từ số ít *"lives"* gây gượng gạo; câu thứ 3 là câu mệnh lệnh kết thúc bằng dấu chấm. | Chuẩn hóa: *"Which friends of {firstName} {lastName} reside in the same city as {firstName} {lastName}?"* |
| **MH-04** | *"{firstName} {lastName} works at companies located in which countries?"* | **Trật tự câu đảo không chuẩn:** Câu trần thuật biến thể thành câu hỏi cuối đuôi. | Chuẩn hóa: *"In which countries are the employers of {firstName} {lastName} located?"* |
| **MH-05** | *"Most of the topics {firstName} {lastName} is interested in fall into which category?"* | **Trật tự từ thiếu tự nhiên & Thiếu tie-break:** Cấu trúc đuôi; đồng thời thiếu tiêu chí phân định khi 2 nhóm chủ đề (TagClass) bằng số lượng. | Chuẩn hóa: *"Which category contains the largest number of topics {firstName} {lastName} is interested in? (Ties broken alphabetically)"*. |

---

### D. Nhóm Path (Đường đi mạng xã hội)

| Mã Template | Câu tiếng Anh trong template cũ | Lỗi ngôn ngữ / Ngữ nghĩa / Cú pháp | Đề xuất sửa đổi chuẩn hóa cho Test2 |
|---|---|---|---|
| **PA-01** | *"How many friendship steps separate {firstName1} {lastName1} from {firstName2} {lastName2}?"* | **Mơ hồ ngữ nghĩa Nhóm (i) nghiêm trọng:** Khái niệm *"friendship steps"* có 2 cách hiểu phổ biến: (a) số cạnh quan hệ `length(p)`, hoặc (b) số người trung gian ở giữa `length(p) - 1`. | Diễn đạt chuẩn xác: *"What is the length of the shortest friendship path (number of friendship links/edges) connecting {firstName1} {lastName1} and {firstName2} {lastName2}?"* |
| **PA-02** | *"Count the shortest friendship paths between {firstName1} {lastName1} and {firstName2} {lastName2}."* | **Câu mệnh lệnh dùng dấu chấm:** Định dạng câu lệnh thay vì câu hỏi trực tiếp. | Đổi thành: *"How many distinct shortest friendship paths exist between {firstName1} {lastName1} and {firstName2} {lastName2}?"* |
| **PA-03** | *"List the common friends of {firstName1} {lastName1} and {firstName2} {lastName2}."* | **Câu mệnh lệnh dùng dấu chấm:** Tương tự PA-02. | Đổi thành: *"Who are the mutual friends of {firstName1} {lastName1} and {firstName2} {lastName2}?"* |
| **PA-04** | *"How many people can {firstName} {lastName} reach within two friendship steps?"* | **Mơ hồ ranh giới (Boundary ambiguity):** Cụm từ không làm rõ: (a) có tính bạn trực tiếp (khoảng cách 1) không, và (b) có tính bản thân người đó không. | Diễn đạt minh bạch: *"How many people (excluding themselves) can {firstName} {lastName} reach within at most two friendship hops (including direct friends and friends-of-friends)?"* |
| **PA-05** | *"How many friendship steps is {firstName} {lastName} from the nearest person living in {city}?"* | **Mơ hồ "friendship steps":** Tương tự PA-01, cần làm rõ số bước là số cạnh hay số người trung gian. | Diễn đạt chuẩn: *"What is the minimum number of friendship edges separating {firstName} {lastName} from any person living in {city}?"* |

---

### E. Nhóm Temporal (Thời gian & Sự kiện)

| Mã Template | Câu tiếng Anh trong template cũ | Lỗi ngôn ngữ / Ngữ nghĩa / Cú pháp | Đề xuất sửa đổi chuẩn hóa cho Test2 |
|---|---|---|---|
| **TM-01** | *"How many posts did {firstName} {lastName} create in {year}?"* | **Mơ hồ khái niệm bài đăng (Post vs Message):** Không làm rõ chỉ đếm bài viết gốc (`:Post`) hay gồm cả bình luận (`:Comment`). | Sửa thành: *"How many original posts (excluding comments) did {firstName} {lastName} publish in {year}?"* |
| **TM-02** | *"How many people joined the network in {monthName} {year}?"* | Không có lỗi ngữ pháp. Rất rõ ràng. | Giữ nguyên. |
| **TM-03** | *"Which forum has {firstName} {lastName} been a member of the longest?"* | **Dễ hiểu nhầm sang thời lượng:** *"longest"* dễ hiểu sang tổng thời gian tham gia, trong khi Cypher gold chỉ lấy forum có `joinDate` sớm nhất (`ORDER BY m.joinDate ASC LIMIT 1`). | Chuẩn hóa: *"Which forum did {firstName} {lastName} join earliest?"* |
| **TM-04** | *"What is the number of comments {firstName} {lastName} wrote during Q{quarter} {year}?"* | Cần kiểm tra định dạng quý chuẩn (tháng 1–3, 4–6, v.v.). | Giữ nguyên: *"How many comments did {firstName} {lastName} create in quarter {quarter} of {year}?"* |
| **TM-05** | *"List the new friends {firstName} {lastName} made in {year}."* | **Câu mệnh lệnh dùng dấu chấm:** Thiếu đồng bộ với định dạng câu hỏi. | Chuẩn hóa: *"Which people became friends with {firstName} {lastName} during the year {year}?"* |

---

## 2. Bốn khuyến nghị trọng tâm cho Hương khi tạo tập Test2

1. **Khắc phục triệt để mơ hồ Nhóm (i) (Định nghĩa ngữ nghĩa rõ ràng):**
   - Phân biệt rõ giữa `Post` (bài viết gốc) và `Message` (gồm cả Comment).
   - Phân biệt rõ `friendship steps` là số cạnh liên kết (`edges / links`), tránh gây nhầm sang số người trung gian.
   - Làm rõ phạm vi bạn của bạn: có bao gồm bạn trực tiếp không (`within at most two hops`).
   - Làm rõ `interested in`: chỉ tính thuộc tính sở thích trong profile (`has interest tag`).

2. **Bổ sung tiêu chí hòa hạng (Tie-breaking) cho toàn bộ câu hỏi "most / largest":**
   - Ở các template tìm top 1 (`LIMIT 1`), câu hỏi phải luôn kèm tiêu chí phụ như *"alphabetically by name"* hoặc khi sinh dữ liệu ngẫu nhiên, Hương cần chạy câu lệnh kiểm tra (`check`) để đảm bảo hạng 1 và hạng 2 **không bao giờ bằng điểm nhau**.

3. **Chuẩn hóa ngữ pháp & dấu câu tiếng Anh:**
   - 100% câu hỏi kết thúc bằng dấu chấm hỏi `?`. Không dùng câu mệnh lệnh kết thúc bằng dấu chấm `.`.
   - Luôn bổ sung mạo từ xác định *"the"* trước các quốc gia danh từ tập hợp (The United Kingdom, The United States, The Czech Republic, The Netherlands, The Philippines).

4. **Giữ nguyên tên thực thể tự nhiên (Natural Names with Spaces):**
   - Không chèn dấu gạch dưới `_` nhân tạo vào câu hỏi (ví dụ: viết "Hong Kong", "New Zealand", "Tilda Swinton").
   - Module (B) `entity_link.py` của Ân đã được nâng cấp hoàn thiện: tự động truy vấn Full-Text Index trong Neo4j để ánh xạ chính xác sang CSDL, đồng thời khi một tên khớp cả `Country` và `Tag` (như "France", "Hong Kong"), Module (B) sẽ liệt kê cả hai để model chọn lựa chính xác theo ngữ cảnh.

---

## 3. Bản tin nhắn mẫu để gửi Hương

```text
Chào Hương,
Mình (Ân) gửi bạn danh sách chi tiết các khiếm khuyết ngôn ngữ, lỗi ngữ pháp và điểm mơ hồ ngữ nghĩa trong 25 template cũ của nhóm mình (phục vụ bạn hoàn thiện tập kiểm thử mù Test2 - T58):

1. File tài liệu đầy đủ đã lưu tại: docs/DANH_SACH_LOI_NGON_NGU_TEMPLATES_GUI_HUONG.md
2. Ba điểm quan trọng nhất cần lưu ý khi viết câu hỏi Test2:
   - Làm rõ khái niệm ngữ nghĩa: "posts" (ghi rõ có gồm comments không), "friendship steps" (ghi rõ là số cạnh/links hay số người ở giữa), "interested in" (ghi rõ là tag trong profile).
   - Các câu hỏi tìm top 1 (most/largest): bắt buộc có tie-breaker phụ (ví dụ "alphabetically by name") hoặc check không để đồng hạng dẫn đầu.
   - Ngữ pháp & dấu câu: 100% câu kết thúc bằng dấu "?"; thêm "the" trước các quốc gia dạng tập hợp (The United Kingdom, The Czech Republic...); giữ nguyên tên thực thể có dấu cách tự nhiên vì Module (B) của mình đã hoàn thiện liên kết đa hình và bẫy dấu "_" qua full-text index rồi nhé!

Bạn xem file chi tiết nhé, nếu cần trao đổi thêm phần nào cứ nhắn mình!
```
