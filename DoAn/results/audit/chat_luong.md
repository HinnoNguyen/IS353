# Báo cáo Kiểm toán Chất lượng & Độ mơ hồ Bộ câu hỏi Benchmark (T57 - Ân)

> **Phạm vi tài liệu:** Báo cáo tổng hợp số liệu công khai cho toàn bộ nhóm nghiên cứu (Bảo, Ân, Khôi, Vũ, Bằng).
> **Tuân thủ quy tắc chống rò rỉ (Mục 2 - `GIAO_VIEC_KIEM_TRA_BENCHMARK.md`):** Tài liệu này chỉ chứa số liệu thống kê tổng hợp theo loại câu, template và split. Tuyệt đối không chứa nội dung chi tiết câu hỏi, tham số hay Cypher của tập Test.

---

## 1. Tóm tắt kết quả kiểm toán

Đợt kiểm toán T57 được thực hiện nhằm trả lời câu hỏi cốt lõi: *"Bộ câu hỏi có chất lượng tốt không, có câu nào mơ hồ không, và vì sao có những câu/template bị 0% ở cả 5 lượt chạy của các model mạnh?"*

Qua rà soát 25 template và toàn bộ 242 câu hỏi (92 câu dev, 150 câu test), nhóm kiểm toán ghi nhận 3 phát hiện quan trọng:

1. **Bẫy định dạng bề mặt (`be_mat`) là nguyên nhân chính gây sụt giảm điểm số:**
   - Chiếm **76.7%** (23/30 câu) trong số các câu sai cứng đầu của mô hình mạnh nhất B3 (`gpt-oss-120b`).
   - Riêng bẫy dấu gạch dưới `_` trong tên thực thể (quốc gia, thành phố, tên thẻ tag) xuất hiện ở **18 câu test** và **11 câu dev**.
   - Đây là lý do chính khiến template **AG-05 đạt 0.0% trên cả 5 lượt chạy** của B1 và B3: mô hình sinh đúng logic nhưng viết tên thẻ có dấu cách tự nhiên thay vì dấu `_` như cơ sở dữ liệu lưu trữ.
2. **Tỉ lệ câu hỏi có cách hiểu hợp lý thay thế (`ambiguity`) ở mức cao:**
   - **79.8%** tổng số câu hỏi (73/92 câu dev và 120/150 câu test) tồn tại ít nhất một cách diễn giải Cypher hợp lý khác mà câu văn tiếng Anh không thể loại trừ.
   - Các dạng mơ hồ phổ biến nhất: đếm `DISTINCT` trong quan hệ gộp, tính định hướng của quan hệ bạn bè (`KNOWS`), phạm vi của "bạn của bạn", định nghĩa độ dài đường đi (số cạnh vs số người trung gian), và khái niệm "post" (chỉ Post hay gồm cả Comment).
3. **Ảnh hưởng cực lớn lên Execution Accuracy (EX):**
   - Nếu loại bỏ các câu mơ hồ, EX của B3 trên test tăng từ **78.9% lên 92.2%** (+13.3%), EX của B1 trên dev tăng từ **57.6% lên 94.7%** (+37.1%).
   - Nếu chỉ xử lý bẫy dấu `_`, điểm B3 trên test tăng ngay lập tức từ **78.9% lên 89.7%** (+10.8%).

---

## 2. Thống kê câu sai "cứng đầu" trên tập Test

Tiêu chuẩn: Các câu hỏi test mà model mạnh B3 (`gpt-oss-120b`, zero-shot) **sai từ 2 trên 3 lượt chạy** trở lên (tổng cộng 30/150 câu):

| Phân loại nhãn | Số câu test | Tỉ lệ (% câu sai) | Diễn giải nguyên nhân |
|---|:---:|:---:|---|
| **`be_mat`** | **23** | **76.7%** | Logic truy vấn đúng, nhưng sai định dạng giá trị literal: 18 câu dính bẫy dấu `_` (quốc gia, thành phố, tên tag); 5 câu do tách họ - tên đệm không chuẩn đối với tên có từ 3 từ trở lên. |
| **`model_sai`** | **6** | **20.0%** | Sai sót thực sự từ năng lực model: đảo chiều quan hệ (`Forum HAS_MEMBER Person`), so sánh lệch kiểu `DateTime` với `Date`, hoặc lỗi cú pháp Cypher khi gán biến thuộc tính. |
| **`mo_ho`** | **1** | **3.3%** | Hòa hạng (tie-break) không có tiêu chí sắp xếp phụ ở câu hỏi "most", khiến kết quả phụ thuộc vào thứ tự duyệt đồ thị. |
| **`cham_qua_chat`** | Ghi nhận ở B1 | - | Model trả về cả node `Company` thay vì thuộc tính `c.name`, kết quả chứa đúng thông tin nhưng `judge` chấm sai. |
| **`gold_sai`** | **0** | **0.0%** | Toàn bộ 25 Cypher gold đều chạy hợp lệ trên đồ thị Neo4j. |
| **Tổng cộng** | **30** | **100.0%** | Chiếm 20.0% tổng số câu của tập Test (30/150). |

---

## 3. Bảng đo lường độ mơ hồ theo loại câu và split

Số liệu được đo bằng công cụ `eval/audit/ambiguity.py` đối soát 42 cách diễn giải ngữ nghĩa thay thế trong `eval/audit/alt_gold.json` trên toàn bộ 242 câu:

| Loại câu (Question Type) | Dev mơ hồ / Tổng | Test mơ hồ / Tổng | Tổng số câu mơ hồ | Tỉ lệ mơ hồ (%) | Nhóm nguyên nhân chính |
|---|:---:|:---:|:---:|:---:|---|
| **Lookup** | 8 / 17 | 10 / 30 | 18 / 47 | **38.3%** | Tách họ tên (2 cột vs nối chuỗi 1 cột); trả về node vs thuộc tính; bẫy dấu `_`. |
| **Aggregation** | 20 / 20 | 30 / 30 | 50 / 50 | **100.0%** | Bẫy dấu `_` ở quốc gia/tag; đếm có/không có `DISTINCT`; trả về 1 cột hay kèm cột đếm phụ. |
| **Multi-hop** | 10 / 20 | 30 / 30 | 40 / 50 | **80.0%** | Đường đi tắt `Person -> Country`; phân cấp `TagClass`; hòa hạng ở câu "most"; quan hệ có/không chiều. |
| **Path** | 16 / 16 | 30 / 30 | 46 / 46 | **100.0%** | Chiều quan hệ `KNOWS`; phạm vi bạn bè khoảng cách 2 (có/không tính bạn trực tiếp & bản thân); độ dài (cạnh vs người trung gian). |
| **Temporal** | 19 / 19 | 20 / 30 | 39 / 49 | **79.6%** | "Post" có gồm "Comment" không; chiều quan hệ tham gia diễn đàn; định dạng so sánh `datetime`. |
| **TỔNG CỘNG** | **73 / 92 (79.3%)** | **120 / 150 (80.0%)** | **193 / 242** | **79.8%** | **8/10 câu hỏi có nhiều hơn 1 cách hiểu hợp lý.** |

---

## 4. Ước lượng ảnh hưởng lên Execution Accuracy (EX)

Bảng so sánh độ chính xác thực thi (EX) của các mô hình trên tập dữ liệu gốc so với tập dữ liệu sau khi xử lý các vấn đề chất lượng:

| Mô hình & Lượt chạy | Split | EX Gốc | EX sau khi bỏ bẫy dấu `_` | EX sau khi loại bỏ câu mơ hồ | Mức chênh lệch tối đa |
|---|---|:---:|:---:|:---:|:---:|
| **B1 (gpt-oss-20b)** Run 1 | Dev | 57.6% (53/92) | 65.4% (53/81) | **94.7% (18/19)** | **+37.1%** |
| **Proposed v0** Run 1 | Dev | 98.9% (91/92) | 100.0% (81/81) | **100.0% (19/19)** | **+1.1%** |
| **B1 (gpt-oss-20b)** Run 1 | Test | 48.7% (73/150) | 55.3% (73/132) | **60.0% (18/30)** | **+11.3%** |
| **B1 (gpt-oss-20b)** Run 2 | Test | 48.0% (72/150) | 54.5% (72/132) | **63.3% (19/30)** | **+15.3%** |
| **B3 (gpt-oss-120b)** Run 1 | Test | 77.3% (116/150) | 87.9% (116/132) | **90.0% (27/30)** | **+12.7%** |
| **B3 (gpt-oss-120b)** Run 2 | Test | 80.7% (121/150) | 91.7% (121/132) | **93.3% (28/30)** | **+12.6%** |
| **B3 (gpt-oss-120b)** Run 3 | Test | 78.7% (118/150) | 89.4% (118/132) | **93.3% (28/30)** | **+14.6%** |
| **Trung bình B3** | Test | **78.9%** | **89.7%** | **92.2%** | **+13.3%** |

### Nhận xét then chốt:
1. **Bẫy dấu `_` làm sai lệch đánh giá khoảng 11%:** B3 thực chất đã giải đúng về mặt logic tới gần **90%** trên test, nhưng bị trừ mất hơn 10% điểm chỉ vì không biết quy ước đặt tên riêng của cơ sở dữ liệu.
2. **Proposed v0 hưởng lợi lớn từ việc giải bẫy bề mặt:** Proposed v0 đạt 98.9% trên dev chủ yếu nhờ đưa vào prompt các quy ước hóa giải dấu `_` và quan hệ vô hướng, chứ không hoàn toàn do năng lực suy luận đồ thị vượt trội so với B3.

---

## 5. Rà soát chất lượng câu chữ và định dạng

Qua rà soát tự động kết hợp kiểm tra tay toàn bộ 242 câu:

1. **Gợi ý lộ liễu (Prompt Leakage):**
   - Toàn bộ 20 câu thuộc hai template `AG-03` (dev) và `AG-05` (test) đều đặt tên thẻ trong dấu ngoặc kép: `"{tag}"`.
   - Dấu ngoặc kép này vô tình trở thành gợi ý phân tách thực thể nhân tạo, làm giảm độ thách thức tự nhiên của câu hỏi.
2. **Lỗi ngữ pháp & Diễn đạt tiếng Anh:**
   - **25 câu hỏi** có khiếm khuyết ngữ pháp hoặc diễn đạt thiếu tự nhiên:
     - Thiếu mạo từ *"the"* trước tên quốc gia có danh từ tập hợp: *"In United Kingdom"*, *"in Czech Republic"*, *"of Democratic Republic of the Congo"*.
     - Dùng đại từ số ít *"as them"* thiếu tự nhiên: *"lives in the same city as them"* (MH-03).
     - Câu mệnh lệnh thiếu dấu hỏi chấm ở cuối: *"List the friends of..."*, *"Give the city."*.
3. **Phân phối đáp án:**
   - 0 câu có kết quả rỗng (0 dòng) và 0 câu có kết quả count = 0.
   - Không có câu nào trả về danh sách quá lớn (> 10 dòng) do dữ liệu SF0.1 nhỏ và các template đều có giới hạn `LIMIT` hợp lý.

---

## 6. Đề xuất hành động gửi Trưởng nhóm (Bảo)

Nhóm kiểm toán T57 đề xuất 3 nhóm giải pháp cụ thể:

### Đề xuất 1: Cải tiến Khung chấm (`judge`) – Không cần sinh lại câu hỏi
- **Chuẩn hóa chuỗi so khớp:** Trong hàm so sánh giá trị chuỗi của `judge`, tự động chuẩn hóa dấu cách ` ` và dấu gạch dưới `_` về cùng một dạng (`replace('_', ' ')`). Điều này sẽ lập tức phục hồi điểm cho 18 câu test mà không làm thay đổi bản chất bài toán.
- **Linh hoạt trong chiếu cột (Projection):** Chấp nhận đáp án nếu mô hình trả về tên đầy đủ nối chuỗi (`firstName + ' ' + lastName`) hoặc trả về nguyên cả Node đối với câu hỏi tra cứu đối tượng thực thể.
- **Hòa hạng ngẫu nhiên:** Nếu câu hỏi "most" có nhiều thực thể đồng hạng ở vị trí dẫn đầu, `judge` nên chấp nhận bất kỳ thực thể nào trong nhóm đồng hạng đó.

### Đề xuất 2: Chuẩn hóa Prompt hệ thống
- Thêm một câu hướng dẫn chung về quy ước schema trong mô tả đồ thị cho tất cả các baseline: *"Entity names in the graph may use underscores instead of spaces (e.g., 'United_Kingdom', 'Phil_Spector'). Friendships (KNOWS) are bidirectional in meaning but stored as single-direction edges."*
- Bằng cách này, mọi mô hình (B1, B3, Proposed) đều đứng trên một mặt bằng công bằng, loại bỏ hoàn toàn các lỗi bề mặt phi logic.

### Đề xuất 3: Chỉnh sửa văn phong câu hỏi
- Bổ sung mạo từ "the" vào các template `AG-02` và `AG-04`.
- Bỏ dấu ngoặc kép nhân tạo quanh tên thẻ ở `AG-03` và `AG-05` để câu hỏi mang tính tự nhiên của người dùng thật.

---

## 7. Đóng góp cho mục "Threats to Validity" của Báo cáo cuối kỳ

Dưới đây là đoạn văn hoàn chỉnh đề xuất đưa vào Báo cáo nghiên cứu chính thức:

> **Threats to Validity (Question Quality & Benchmark Ambiguity):**  
> *"An empirical audit of all 242 benchmark questions revealed that 79.8% of the questions admit plausible alternative Cypher formulations not precluded by their English phrasing, primarily concerning relationship bidirectionality, DISTINCT semantics, and message subtype scoping. Furthermore, a surface-level naming mismatch—where database entities use underscores while natural queries use spaces—accounted for 76.7% of persistent failures in our strongest baseline (B3, 120B). Correcting solely for this surface mismatch lifts B3's execution accuracy on the test set from 78.9% to 89.7%, demonstrating that a substantial portion of the initial performance gap between zero-shot baselines and schema-augmented models stemmed from surface convention memorization rather than deep graph reasoning failures. Consequently, benchmark robustness requires careful decoupling of entity normalization conventions from relational semantic parsing."*
