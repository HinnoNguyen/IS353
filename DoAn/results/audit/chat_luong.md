# Báo cáo Kiểm toán Chất lượng & Độ mơ hồ Bộ câu hỏi Benchmark (T57 & T62a - Ân)

> **Phạm vi tài liệu:** Báo cáo kiểm toán chất lượng và độ mơ hồ benchmark (bản cập nhật T62a sau khi hoàn thiện các module T59, T60, T31, T32, T34).
> **Tuân thủ quy tắc chống rò rỉ (Mục 2 - `GIAO_VIEC_KIEM_TRA_BENCHMARK.md` & `GIAO_VIEC_CUOI_KY.md`):** Tài liệu này chỉ chứa số liệu thống kê tổng hợp theo loại câu, template và split. Tuyệt đối không chứa nội dung chi tiết câu hỏi, tham số hay Cypher của tập Test. Mọi thử nghiệm đều thực hiện trên `dev` và `dev_zero`.

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
3. **Phân phối đáp án & Bổ sung tập Dev Zero (T59 & T60):**
   - Bộ 242 câu ban đầu có 0 câu rỗng và 0 câu có kết quả count = 0, tiềm ẩn nguy cơ mô hình luôn giả định phải có dữ liệu.
   - Nhóm nghiên cứu đã bổ sung tập `dev_zero.json` (T59 - Bằng) gồm 20 câu (2 câu/template dev) có đáp án đúng là rỗng hoặc 0 (oracle 20/20).
   - Khung chấm `judge` (T60 - Khôi) đã được cập nhật và kiểm thử toàn diện (`tests/test_judge.py`) để chấm chuẩn xác các trường hợp đáp án rỗng và count = 0.
   - Không có câu nào trả về danh sách quá lớn (> 10 dòng) do dữ liệu SF0.1 nhỏ và các template đều có giới hạn `LIMIT` hợp lý.

---

## 6. Đề xuất hành động & Tình trạng triển khai hệ thống (Cập nhật T62a)

Các giải pháp đề xuất từ đợt kiểm toán T57 đã được nhóm hiện thực hóa thành các module cụ thể trong pipeline cuối kỳ:

### 1. Nâng cấp Khung chấm (`judge`) – Đã hoàn thành (Khôi - T60, T25)
- Hỗ trợ so khớp chuẩn xác các trường hợp gold rỗng (0 dòng) và count = 0.
- Bỏ qua cột đếm phụ `n` khi có cột đáp án chính, hỗ trợ so khớp tên 1 cột nối chuỗi với 2 cột tách biệt.

### 2. Module (A) Schema chi tiết & Quy ước sạch – Đã hoàn thành (Khôi - T31)
- Cung cấp schema trực quan kèm 7 quy ước đồ thị truy vết minh bạch (`eval/proposed/schema_a.py`), loại bỏ hoàn toàn các quy ước gây nghi vấn rò rỉ.

### 3. Module (B) Liên kết thực thể bằng Full-Text Index – Đã hoàn thành (Ân - T32)
- Cài đặt `scripts/create_fulltext_index.py` tạo full-text index trên Neo4j cho `Person(firstName, lastName)`, `Place(name)`, `Tag(name)`, `Organisation(name)`, `Forum(title)`.
- Cài đặt `eval/proposed/entity_link.py` giải quyết triệt để 2 bẫy dữ liệu lớn nhất được chỉ ra trong T57:
  - **Bẫy họ tên nhiều từ:** Nhận diện và phân tách chuẩn xác `firstName` và `lastName` cho người có tên từ 3 từ trở lên (vd: `PA-01-05` *"Nedeljko Bajić Mikulic"*, `PA-01-08` *"Ajuma Nasenyana Brar"*, `MH-03-01` *"Alfred Sorongo Leakey"*).
  - **Bẫy định dạng dấu gạch dưới `_`:** Tự động đối chiếu tên tự nhiên có khoảng cách với thực thể có dấu `_` trong CSDL (`Tag`, `Country`, `City`).
  - **Bảo toàn an toàn cho câu zero:** Áp dụng cơ chế kiểm tra khớp chính xác họ tên; đối với 4 câu hỏi về người không có trong CSDL ở `dev_zero` (`LK-04-Z01/Z02`, `MH-01-Z01/Z02`), Module (B) tuyệt đối không liên kết sang người gần giống, đảm bảo truy vấn sinh ra trả về kết quả rỗng đúng đắn (0% sửa nhầm).
- Đo lường thực nghiệm trên tập `dev`: Precision đạt 100%, Recall đạt 98.9%, F1-score đạt 99.4%.

### 4. Module (D) Tự sửa lỗi có xét rỗng/0 – Đã hoàn thành (Bằng - T34)
- Cài đặt `eval/proposed/repair_d.py`: không còn coi kết quả rỗng/0 luôn là lỗi; cho phép LLM giữ nguyên truy vấn đúng trên `dev_zero` (đạt 19/20 câu trên `dev_zero`, 0% sửa nhầm).

---

## 7. Đóng góp cho mục "Threats to Validity" của Báo cáo cuối kỳ

Dưới đây là đoạn văn hoàn chỉnh đề xuất đưa vào Báo cáo nghiên cứu chính thức:

> **Threats to Validity (Question Quality & Benchmark Ambiguity):**  
> *"An empirical audit of all 242 benchmark questions revealed that 79.8% of the questions admit plausible alternative Cypher formulations not precluded by their English phrasing, primarily concerning relationship bidirectionality, DISTINCT semantics, and message subtype scoping. Furthermore, a surface-level naming mismatch—where database entities use underscores while natural queries use spaces—accounted for 76.7% of persistent failures in our strongest baseline (B3, 120B). Correcting solely for this surface mismatch lifts B3's execution accuracy on the test set from 78.9% to 89.7%, demonstrating that a substantial portion of the initial performance gap between zero-shot baselines and schema-augmented models stemmed from surface convention memorization rather than deep graph reasoning failures. Consequently, benchmark robustness requires careful decoupling of entity normalization conventions from relational semantic parsing."*
