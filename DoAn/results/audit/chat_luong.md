# Báo cáo Kiểm toán Chất lượng & Độ mơ hồ Bộ câu hỏi Benchmark (T57 & T62a - Ân)

> **Phạm vi tài liệu:** Báo cáo kiểm toán chất lượng và độ mơ hồ benchmark (bản cập nhật T62a hiệu chỉnh phân loại mơ hồ và cập nhật tiến độ giải pháp cuối kỳ).
> **Tuân thủ quy tắc chống rò rỉ (Mục 2 - `GIAO_VIEC_KIEM_TRA_BENCHMARK.md` & `GIAO_VIEC_CUOI_KY.md`):** Tài liệu này chỉ chứa số liệu thống kê tổng hợp theo loại câu, template và split. Tuyệt đối không trích dẫn nội dung chi tiết câu hỏi, tham số, ID cụ thể hay Cypher của tập Test. Mọi ví dụ minh họa và thử nghiệm can thiệp chỉ được thực hiện trên `dev` và `dev_zero`.

---

## 1. Tóm tắt kết quả kiểm toán (Hiệu chỉnh T62a)

Đợt kiểm toán T57 ban đầu được thực hiện nhằm trả lời: *"Bộ câu hỏi có chất lượng tốt không, có câu nào mơ hồ không, và vì sao có những câu/template bị 0% ở cả 5 lượt chạy của các model mạnh?"*

Ở bản cập nhật T62a, nhóm kiểm toán đã **tách bạch rõ ràng khái niệm "mơ hồ" thành hai nhóm riêng biệt**:
- **Nhóm (i) – Mơ hồ ngôn ngữ tự nhiên (Câu tiếng Anh có nhiều nghĩa hợp lý):** Câu hỏi tiếng Anh không đủ thông tin loại trừ các cách hiểu khác nhau (vd: *"posts"* có gồm Comment không; độ dài đường đi tính theo số cạnh hay số người trung gian; *"bạn của bạn"* khoảng cách 2 có gồm bạn trực tiếp và bản thân không; câu hỏi *"most"* thiếu tiêu chí phụ khi hòa hạng). **Chỉ có nhóm (i) này mới được tính là độ mơ hồ thực sự của benchmark.**
- **Nhóm (ii) – Lỗi mô hình hoặc bẫy cấu trúc schema đồ thị:** Các vấn đề do thiết kế đồ thị hoặc giới hạn của LLM (chiều quan hệ `KNOWS`, đường đi tắt `Person -> Country`, trả về nguyên Node thay vì thuộc tính, thiếu cột đếm phụ). Đây là bài toán về mô hình hóa đồ thị và năng lực sinh Cypher, **không phải lỗi ngữ nghĩa của câu hỏi**.

Sau khi hiệu chỉnh:
1. **Tỉ lệ mơ hồ thực sự (Nhóm i) là 28.1% (68/242 câu):** gồm 28/92 câu dev (30.4%) và 40/150 câu test (26.7%), tập trung chủ yếu ở loại câu `Path`, `Aggregation` và `Temporal`.
2. **Bẫy định dạng bề mặt (`be_mat`) chiếm 76.7% câu sai cứng đầu của B3:** Mô hình hiểu đúng logic quan hệ đồ thị nhưng trượt điểm vì bẫy dấu `_` trong tên thực thể (`Tag`, `Country`, `City`) hoặc tách sai họ tên nhiều từ (`Person`).
3. **Giải pháp chính đáng cuối kỳ:** Nhóm đã xây dựng Module (B) `entity_link.py` (T32) dùng full-text index trong Neo4j để tự động chuẩn hóa thực thể từ CSDL thay vì viết quy ước nhân tạo trong prompt.

---

## 2. Thống kê câu sai "cứng đầu" trên tập Test

Tiêu chuẩn: Các câu hỏi test mà model mạnh B3 (`gpt-oss-120b`, zero-shot) **sai từ 2 trên 3 lượt chạy** trở lên (tổng cộng 30/150 câu):

| Phân loại nhãn | Số câu test | Tỉ lệ (% câu sai) | Diễn giải nguyên nhân |
|---|:---:|:---:|---|
| **`be_mat`** | **23** | **76.7%** | Logic truy vấn đúng, nhưng sai định dạng giá trị literal: 18 câu do bẫy dấu `_` (quốc gia, thành phố, tên tag); 5 câu do tách họ - tên đệm không chuẩn đối với tên có từ 3 từ trở lên. |
| **`model_sai`** | **6** | **20.0%** | Sai sót từ năng lực model: đảo chiều quan hệ, so sánh lệch kiểu `DateTime` với `Date`, hoặc lỗi cú pháp Cypher khi gán biến. |
| **`mo_ho` (Nhóm i)** | **1** | **3.3%** | Hòa hạng (tie-break) không có tiêu chí sắp xếp phụ ở câu hỏi "most", khiến kết quả phụ thuộc vào thứ tự duyệt đồ thị của Neo4j. |
| **`cham_qua_chat`** | Ghi nhận ở B1 | - | Model trả về cả node `Company` thay vì thuộc tính `c.name`, kết quả chứa đúng thông tin nhưng `judge` chấm sai. |
| **`gold_sai`** | **0** | **0.0%** | Toàn bộ 25 Cypher gold đều chạy hợp lệ và logic chuẩn trên đồ thị Neo4j. |
| **Tổng cộng** | **30** | **100.0%** | Chiếm 20.0% tổng số câu của tập Test (30/150). |

---

## 3. Bảng đo lường độ mơ hồ thực sự (Nhóm i) theo loại câu và split

Số liệu hiệu chỉnh T62a chỉ tính các câu hỏi thuộc **Nhóm (i) – câu tiếng Anh có nhiều cách hiểu hợp lý**:
- `AG-03` & `TM-01`: *"posts"* hiểu là riêng `:Post` hay toàn bộ `:Message` (bao gồm `:Comment`).
- `AG-05`: *"interested in"* hiểu là sở thích `:HAS_INTEREST` hay thích các bài viết `:LIKES->:Post->:HAS_TAG`.
- `PA-01` & `PA-05`: Độ dài đường đi *"friendship steps"* tính theo số cạnh `length(p)` hay số người trung gian `length(p) - 1`.
- `PA-04`: *"reach within two friendship steps"* có bao gồm bạn bè trực tiếp (khoảng cách 1) và chính bản thân không.
- `TM-04`: *"comments"* hiểu là riêng `:Comment` hay toàn bộ `:Message` trong quý.

| Loại câu (Question Type) | Dev mơ hồ / Tổng | Test mơ hồ / Tổng | Tổng số câu mơ hồ (Nhóm i) | Tỉ lệ mơ hồ (%) | Bản chất ngữ nghĩa mơ hồ |
|---|:---:|:---:|:---:|:---:|---|
| **Lookup** | 0 / 17 | 0 / 30 | 0 / 47 | **0.0%** | Câu hỏi hỏi đích danh một thuộc tính, không có đa nghĩa ngôn ngữ. |
| **Aggregation** | 10 / 20 | 10 / 30 | 20 / 50 | **40.0%** | Đa nghĩa giữa khái niệm "posts" và "messages"; phạm vi của "interested in". |
| **Multi-hop** | 0 / 20 | 0 / 30 | 0 / 50 | **0.0%** | Các câu hỏi đa chặng có ngữ nghĩa tiếng Anh rõ ràng (các lỗi gặp phải thuộc Nhóm ii - bẫy cấu trúc đồ thị). |
| **Path** | 9 / 16 | 20 / 30 | 29 / 46 | **63.0%** | Định nghĩa khoảng cách bước bạn bè (số cạnh vs số người ở giữa); phạm vi bạn của bạn khoảng cách 2. |
| **Temporal** | 9 / 19 | 10 / 30 | 19 / 49 | **38.8%** | Phân định khái niệm bài viết ("posts" / "comments" vs "messages") trong khoảng thời gian. |
| **TỔNG CỘNG** | **28 / 92 (30.4%)** | **40 / 150 (26.7%)** | **68 / 242** | **28.1%** | **Khoảng 2.8/10 câu hỏi tồn tại nhiều hơn 1 cách hiểu tiếng Anh hợp lý.** |

> *Ghi chú hiệu chỉnh:* Bản báo cáo T57 cũ ghi nhận tỉ lệ 79.8% do tính gộp cả các quy ước đồ thị Nhóm (ii) (như chiều của quan hệ `KNOWS`, việc nối tắt `Person -> Country`, và việc trả về 1 cột hay kèm cột phụ). Khi tách bạch đúng đắn, tỉ lệ mơ hồ thực chất của bộ câu hỏi chỉ là **28.1%**.

---

## 4. Tác động của bẫy dữ liệu bề mặt (dấu `_`) lên Execution Accuracy (EX)

Để đo lường khách quan mức độ ảnh hưởng của bẫy đặt tên riêng trong cơ sở dữ liệu (`Tag`, `Country`, `City` dùng dấu `_` thay vì dấu cách tự nhiên), bảng dưới đây so sánh điểm EX gốc với điểm EX khi **loại trừ các câu chứa bẫy `_` khỏi mẫu số** (mẫu số dev giảm từ 92 xuống 81; mẫu số test giảm từ 150 xuống 132 câu):

> ⚠️ **Lưu ý quan trọng:** Cột *"EX khi loại trừ câu dính bẫy `_`"* là phép đo lọc bỏ các câu hỏi này ra khỏi tập đánh giá (giảm mẫu số), **hoàn toàn không sửa đổi câu trả lời hay can thiệp vào câu Cypher của mô hình**.

| Mô hình & Lượt chạy | Split | EX Gốc (Mẫu số đầy đủ) | EX khi loại trừ câu dính bẫy `_` (Loại khỏi mẫu số) | Chênh lệch độ chính xác |
|---|---|:---:|:---:|:---:|
| **B1 (gpt-oss-20b)** Run 1 | Dev | 57.6% (53/92) | 65.4% (53/81) | **+7.8%** |
| **Proposed v0** Run 1 | Dev | 98.9% (91/92) | 100.0% (81/81) | **+1.1%** |
| **B1 (gpt-oss-20b)** Run 1 | Test | 48.7% (73/150) | 55.3% (73/132) | **+6.6%** |
| **B1 (gpt-oss-20b)** Run 2 | Test | 48.0% (72/150) | 54.5% (72/132) | **+6.5%** |
| **B3 (gpt-oss-120b)** Run 1 | Test | 77.3% (116/150) | 87.9% (116/132) | **+10.6%** |
| **B3 (gpt-oss-120b)** Run 2 | Test | 80.7% (121/150) | 91.7% (121/132) | **+11.0%** |
| **B3 (gpt-oss-120b)** Run 3 | Test | 78.7% (118/150) | 89.4% (118/132) | **+10.7%** |
| **Trung bình B3** | Test | **78.9%** | **89.7%** | **+10.8%** |

### Nhận xét cốt lõi:
1. **Bẫy định dạng bề mặt làm méo mó đánh giá thực chất ~11%:** Mô hình mạnh B3 đã giải đúng logic đồ thị tới gần **90%** trên tập test, nhưng bị trừ mất hơn 10% điểm chỉ vì quy ước đặt tên riêng của cơ sở dữ liệu.
2. **Cơ sở cho Module (B) trong Pipeline đề xuất:** Việc đưa quy ước bẫy `_` vào prompt của Module (A) hay Proposed v0 tuy giúp tăng điểm nhưng dễ bị coi là mẹo bề mặt (như báo cáo rò rỉ T56 của Khôi chỉ ra). Do đó, **cách giải quyết chính đáng và khoa học nhất là Module (B) Entity Linking (T32 - Ân)**: tra cứu động trong CSDL thông qua Full-Text Index để ánh xạ tên tự nhiên sang đúng định dạng CSDL trước khi đưa vào sinh Cypher.

---

## 5. Rà soát chất lượng câu chữ & Khắc phục phân phối đáp án

1. **Gợi ý dấu ngoặc kép:** Các câu hỏi về Tag ở dev đều đặt tên thẻ trong dấu ngoặc kép `"{tag}"`, vô tình tạo gợi ý phân tách thực thể nhân tạo. Module (B) đã được thiết kế để trích xuất cả thực thể trong ngoặc kép lẫn cụm từ viết hoa tự do ngoài ngoặc kép.
2. **Khiếm khuyết diễn đạt tiếng Anh:**
   - Thiếu mạo từ *"the"* trước tên quốc gia có danh từ tập hợp (như *"United Kingdom"*, *"Czech Republic"*).
   - Dùng đại từ số ít *"as them"* thiếu tự nhiên (*"lives in the same city as them"*).
   - Câu mệnh lệnh thiếu dấu hỏi chấm.
3. **Phân phối đáp án & Bổ sung tập Dev Zero (T59 & T60):**
   - Đợt kiểm toán T57 phát hiện bộ câu hỏi gốc có 0 câu rỗng và 0 câu có kết quả count = 0, tiềm ẩn nguy cơ mô hình luôn giả định phải có dữ liệu.
   - Nhóm nghiên cứu đã bổ sung tập `dev_zero.json` (T59 - Bằng) gồm 20 câu (2 câu/template dev) có đáp án đúng là rỗng hoặc 0 (oracle 20/20).
   - Khung chấm `judge` (T60 - Khôi) đã được cập nhật và kiểm thử toàn diện (`tests/test_judge.py`) để chấm chuẩn xác các trường hợp đáp án rỗng và count = 0.

---

## 6. Khuyến nghị gửi Hương để xây dựng tập kiểm thử mù Test2

Nhằm tránh lặp lại các vấn đề ngữ nghĩa Nhóm (i) và bẫy định dạng trên tập **Test2**, nhóm kiểm toán khuyến nghị:

| Nhóm vấn đề | Template cũ gặp lỗi | Khuyến nghị chỉnh sửa cho Test2 |
|---|---|---|
| **Định nghĩa "Post" vs "Message"** | `AG-03`, `TM-01` | Nêu rõ trong câu hỏi: *"posts (excluding comments)"* hoặc *"posts and comments"* để loại trừ đa nghĩa phân cấp subtype trong LDBC. |
| **Độ dài đường đi bạn bè** | `PA-01`, `PA-05` | Dùng diễn đạt chuẩn xác: *"How many friendship edges / links"* thay vì *"friendship steps"* (dễ gây nhầm sang số người trung gian `steps - 1`). |
| **Phạm vi bạn của bạn** | `PA-04` | Làm rõ: *"friends of friends who are not direct friends"* hoặc *"reachable within at most two steps"*. |
| **Khái niệm "interested in"** | `AG-05` | Diễn đạt rõ ràng: *"have interest tag X in their profile"* để tránh hiểu nhầm sang hành động like bài viết gắn tag. |
| **Hòa hạng ở câu hỏi "most"** | `AG-02`, `AG-04`, `MH-02`, `MH-05` | Bổ sung tiêu chí sắp xếp phụ (tie-breaker), ví dụ *"alphabetically by name"*, hoặc đảm bảo tham số sinh ra không có hai thực thể đồng hạng ở vị trí dẫn đầu. |
| **Tên thực thể tự nhiên** | Các câu về quốc gia / tag | Giữ nguyên tên tự nhiên có dấu cách (không chèn dấu `_` nhân tạo) để đánh giá năng lực liên kết thực thể (Entity Linking) của hệ thống. |

---

## 7. Đóng góp cho mục "Threats to Validity" của Báo cáo cuối kỳ

Dưới đây là đoạn văn đề xuất đưa vào Báo cáo nghiên cứu chính thức:

> **Threats to Validity (Question Quality & Benchmark Ambiguity):**  
> *"An empirical audit of all 242 benchmark questions revealed that 28.1% of the questions (68/242) exhibit genuine linguistic ambiguity in their English phrasing—principally regarding message subtype scoping ('posts' vs. all messages), path length definitions (edge count vs. intermediate hops), and friend-of-friend boundaries. Furthermore, a surface-level naming mismatch—where database entities store underscores while natural language queries use spaces—accounted for 76.7% of persistent failures in our strongest baseline (B3, 120B). Excluding these underscore-affected instances from the denominator lifts B3's execution accuracy on the test set from 78.9% to 89.7% (+10.8%), demonstrating that a significant fraction of initial errors stemmed from surface convention memorization rather than relational reasoning failures. Consequently, our proposed framework decouples entity resolution via full-text graph indexing (Module B) from semantic Cypher generation, ensuring both benchmark robustness and fair evaluation without artificial prompt heuristics."*
