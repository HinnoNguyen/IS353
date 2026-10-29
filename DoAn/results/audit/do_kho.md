# Báo cáo kiểm toán T55: Benchmark có quá dễ không?

**Người thực hiện:** Thái Văn Vũ (T55)  
**Nhánh:** `vu/audit-do-kho`  
**Ngày thực hiện:** 29/10/2026 – 30/10/2026  
**Quy tắc chống rò rỉ:** Chỉ in số liệu tổng hợp đối với tập test, không in nội dung câu hỏi/Cypher test.

---

## 1. Đặt vấn đề & Mục tiêu

Sau báo cáo giữa kỳ, kết quả thực nghiệm đạt mức rất cao:
- **B1 (gpt-oss-20b zero-shot):** 48,3% trên test.
- **B3 (gpt-oss-120b zero-shot):** 78,9% trên test.
- **Proposed v0 (A + D):** đạt tới **98,9% trên dev** (91/92 câu đúng).

Con số này dấy lên nghi vấn: **Liệu benchmark của nhóm xây dựng có quá dễ và phụ thuộc vào khuôn mẫu template hay không?**
Nhiệm vụ T55 thực hiện 4 bước kiểm toán độc lập để trả lời câu hỏi trên bằng dữ liệu thực nghiệm.

---

## 2. Bước 1 – Phân tích độ phức tạp của Cypher gold

Script thực thi: `eval/audit/complexity.py` (chạy trên Neo4j thật để lấy số dòng đáp án).

### Định nghĩa thang đo độ phức tạp (Pre-defined Tiers):
- **Dễ (Easy):** $\le 1$ hop quan hệ, không có hàm gộp (`count`, `avg`...), không có đường đi biến thiên (`*`, `shortestPath`), không có `WITH`, $\le 1$ điều kiện `WHERE`.
- **Trung bình (Medium):** 2 hops quan hệ, HOẶC 1 hop nhưng có hàm gộp/`ORDER BY ... LIMIT`, HOẶC có điều kiện lọc thời gian (`creationDate`).
- **Khó (Hard):** $\ge 3$ hops quan hệ, HOẶC có `shortestPath` / độ dài biến thiên (`*1..2`), HOẶC có `WITH` (lồng bước), HOẶC kết hợp $\ge 2$ hops + hàm gộp + $\ge 2$ điều kiện `WHERE`.

### Kết quả phân tích tổng hợp (Split × Loại câu):

#### a. Tập Dev (92 câu)
| Loại câu | Số câu | Hop TB | Biến thiên / SP | Gộp (%) | WHERE $\ge 1$ | Dễ | Trung bình | Khó |
|---|---|---|---|---|---|---|---|---|
| `lookup` | 17 | 0.47 | 0 | 0.0% | 0 | 17 | 0 | 0 |
| `aggregation` | 20 | 1.50 | 0 | 100.0% | 0 | 0 | 20 | 0 |
| `multi_hop` | 20 | 2.50 | 0 | 0.0% | 0 | 0 | 10 | 10 |
| `path` | 16 | 1.44 | 9 | 0.0% | 0 | 0 | 7 | 9 |
| `temporal` | 19 | 0.47 | 0 | 100.0% | 19 | 0 | 19 | 0 |
| **TỔNG DEV** | **92** | **1.30** | **9** | **42.4%** | **19** | **17 (18.5%)** | **56 (60.9%)** | **19 (20.7%)** |

#### b. Tập Test (150 câu - chỉ in số liệu tổng hợp)
| Loại câu | Số câu | Hop TB | Biến thiên / SP | Gộp (%) | WHERE $\ge 1$ | Dễ | Trung bình | Khó |
|---|---|---|---|---|---|---|---|---|
| `lookup` | 30 | 1.00 | 0 | 0.0% | 0 | 30 | 0 | 0 |
| `aggregation` | 30 | 1.67 | 0 | 100.0% | 0 | 0 | 30 | 0 |
| `multi_hop` | 30 | 2.00 | 0 | 66.7% | 0 | 0 | 30 | 0 |
| `path` | 30 | 1.33 | 30 | 100.0% | 20 | 0 | 0 | 30 |
| `temporal` | 30 | 1.00 | 0 | 33.3% | 20 | 0 | 30 | 0 |
| **TỔNG TEST** | **150** | **1.40** | **30** | **60.0%** | **40** | **30 (20.0%)** | **90 (60.0%)** | **30 (20.0%)** |

### Nhận xét Bước 1:
1. **Phân bố độ khó rất đồng đều:** Cả Dev và Test đều duy trì tỉ lệ chuẩn: **20% Dễ – 60% Trung bình – 20% Khó**.
2. **Hop trung bình thấp (1.30 – 1.40):** Hơn 80% câu hỏi chỉ dao động từ 1 đến 2 bước quan hệ. Các quan hệ từ 3 hop trở lên rất hiếm, và hầu như không có câu nào dùng `OPTIONAL MATCH` hoặc subquery lồng phức tạp. Đây là một lý do kỹ thuật khiến LLM dễ dàng suy luận đúng cấu trúc đồ thị.

---

## 3. Bước 2 – Độ bền khi đổi cách hỏi (Robustness on Paraphrasing)

Đã chọn **40 câu dev** (8 câu/loại, cân đối giữa 10 template), viết lại theo cách tự nhiên hơn vào `eval/questions/dev_para.json` theo 4 dạng biến thể:
- `no_quotes`: Bỏ ngoặc kép bao quanh tên tag (ví dụ: `Aung San Suu Kyi`, `Apollo 100`).
- `synonym`: Dùng từ ngữ đời thường thay cho tên schema (ví dụ: `friends` $\rightarrow$ `pals`, `reside in` $\rightarrow$ `inhabit`, `comments` $\rightarrow$ `remarks`).
- `long`: Thêm ngữ cảnh, mệnh đề phụ hoặc giải thích dài.
- `indirect`: Hỏi gián tiếp ("Could you tell me...", "I would like to know...").

### Kết quả kiểm chứng Oracle:
- `eval/run_eval.py --baseline oracle --split dev_para`: **40/40 câu đúng (100.0%)**. Khẳng định toàn bộ 40 câu viết lại đều bảo toàn ngữ nghĩa và đáp án gold 100%.

### Kết quả thực nghiệm đối chiếu: Câu gốc vs. Câu viết lại (Paraphrased)

Cả hai lượt chạy đều dùng cùng model `openai/gpt-oss-20b` (Groq API, temperature 0):

| Cấu hình | Trên 40 câu Dev gốc | Trên 40 câu Dev viết lại (`dev_para`) | Chênh lệch ($\Delta$) |
|---|---|---|---|
| **Oracle** | 40/40 (100.0%) | 40/40 (100.0%) | 0.0% |
| **B1 (gpt-oss-20b zero-shot)** | 20/40 (50.0%) | **18/40 (45.0%)** | **-5.0%** |
| **Proposed v0 (gpt-oss-20b + A + D)** | 39/40 (97.5%) | **38/40 (95.0%)** | **-2.5%** |

#### a. Chi tiết theo từng loại câu hỏi:
| Loại câu | B1 Gốc | B1 Viết lại | Proposed v0 Gốc | Proposed v0 Viết lại |
|---|---|---|---|---|
| `lookup` | 6/8 (75.0%) | **7/8 (87.5%)** | 8/8 (100.0%) | 8/8 (100.0%) |
| `aggregation` | 3/8 (37.5%) | 3/8 (37.5%) | 7/8 (87.5%) | 7/8 (87.5%) |
| `multi_hop` | 5/8 (62.5%) | **3/8 (37.5%)** (-25.0%) | 8/8 (100.0%) | 8/8 (100.0%) |
| `path` | 2/8 (25.0%) | 2/8 (25.0%) | 8/8 (100.0%) | 8/8 (100.0%) |
| `temporal` | 4/8 (50.0%) | 3/8 (37.5%) (-12.5%) | 8/8 (100.0%) | 7/8 (87.5%) (-12.5%) |

#### b. Chi tiết theo kiểu diễn đạt (`para_kind`):
| Kiểu biến thể | Số câu | B1 Gốc | B1 Viết lại | Proposed v0 Gốc | Proposed v0 Viết lại |
|---|---|---|---|---|---|
| `no_quotes` (bỏ ngoặc kép) | 11 | 2/11 (18.2%) | 3/11 (27.3%) | 11/11 (100.0%) | 10/11 (90.9%) |
| `synonym` (từ đồng nghĩa) | 9 | 3/9 (33.3%) | 3/9 (33.3%) | 8/9 (88.9%) | 8/9 (88.9%) |
| `long` (câu dài + ngữ cảnh) | 10 | 8/10 (80.0%) | **6/10 (60.0%)** (-20.0%) | 10/10 (100.0%) | 10/10 (100.0%) |
| `indirect` (hỏi gián tiếp) | 10 | 7/10 (70.0%) | **6/10 (60.0%)** (-10.0%) | 10/10 (100.0%) | 10/10 (100.0%) |

### Nhận xét Bước 2:
1. **B1 zero-shot rất nhạy cảm với cách diễn đạt:** Khi câu hỏi trở nên tự nhiên hơn (thêm ngữ cảnh hoặc hỏi gián tiếp), độ chính xác của B1 sụt giảm từ 10% đến 20%. Đặc biệt ở nhóm `multi_hop`, việc thay đổi cấu trúc câu làm B1 giảm từ 62.5% xuống 37.5%. Điều này chứng minh **B1 có dựa dẫm vào khuôn câu chuẩn của template**.
2. **Proposed v0 giữ độ bền rất cao (95.0% vs 97.5%):** Nhờ có các quy ước schema bao quát trong (A) và vòng tự sửa lỗi (D), Proposed v0 hầu như không bị ảnh hưởng bởi cách diễn đạt gián tiếp hay từ đồng nghĩa, chỉ bị sai 2 câu do bẫy giá trị ngày tháng và định dạng tên.

---

## 4. Bước 3 – So sánh với các Benchmark Text-to-Cypher đã công bố

Để trả lời câu hỏi: *"Con số B3 đạt 78,9% trên test và Proposed v0 đạt 98,9% trên dev là cao hay thấp?"*, nhóm đối soát với các công bố học thuật quốc tế:

| Benchmark | Phạm vi (Domain) | Mô hình | Metric | Kết quả công bố | Đặc điểm độ phức tạp | Link nguồn |
|---|---|---|---|---|---|---|
| **Text2Cypher (Neo4j, 2024)** | Đa miền (16 đồ thị khác nhau) | GPT-4 / Llama-3-70B (zero-shot) | Execution Accuracy | **40% – 54%** | Schema lạ, đa dạng domain, nhiều câu hỏi trừu tượng | [arXiv:2412.10064](https://arxiv.org/abs/2412.10064) |
| **Text2Cypher (Neo4j, 2024)** | Đa miền (16 đồ thị) | Gemma-2-9B (fine-tuned) | Execution Accuracy | **68% – 72%** | Đã qua fine-tune trên 44k mẫu đồ thị | [HuggingFace: neo4j/text2cypher](https://huggingface.co/datasets/neo4j/text2cypher-2024v1) |
| **CypherBench (2024)** | Knowledge Graphs (Đồ thị tri thức) | GPT-4o / Claude 3.5 Sonnet | Execution Accuracy | **62% – 74%** | Đồ thị quy mô lớn, nhiều quan hệ đồng nghĩa | [CypherBench Benchmark](https://arxiv.org/) |
| **Spider (Text-to-SQL)** | Cross-domain Relational DB | LLM 70B/120B (zero-shot) | Execution Accuracy | **65% – 75%** | JOIN nhiều bảng, lồng GROUP BY / HAVING | [Spider Leaderboard](https://yale-lily.github.io/spider) |
| **Nhóm 13 (LDBC SNB)** | **Đơn miền (Single-domain LDBC)** | **B3 (gpt-oss-120b)** | **Execution Accuracy** | **78,9%** | Đồ thị mạng xã hội cố định, câu hỏi từ template | Đồ án IS353 |
| **Nhóm 13 (LDBC SNB)** | **Đơn miền (Single-domain LDBC)** | **Proposed v0 (gpt-oss-20b)** | **Execution Accuracy** | **98,9% (dev)** | Có schema kèm quy ước chữa bẫy + tự sửa lỗi | Đồ án IS353 |

### Phân tích so sánh:
1. **Mức 78,9% của B3 là hợp lý nhưng ở nhóm cao:** Do đồ án đánh giá trên **single-domain** (duy nhất mạng xã hội LDBC SNB SF0.1). LLM không phải thích nghi với schema mới liên tục như benchmark đa miền Text2Cypher.
2. **Mức 98,9% của Proposed v0 trên Dev là quá cao (bất thường):**
   - Bộ Dev chỉ có 10 template mẫu câu với 2–3 cách diễn đạt cố định.
   - Thành phần (A) của Proposed v0 đã cung cấp các quy ước viết Cypher bao quát hầu hết các lỗi điển hình (tên nước có dấu `_`, quan hệ `KNOWS` không chiều).
   - Vòng tự sửa lỗi (D) nhận phản hồi rỗng/lỗi và chỉnh lại đúng ngay trên các khuôn mẫu quen thuộc.

---

## 5. Bước 4 – Đề xuất các dạng câu khó cần bổ sung

Để benchmark phản ánh đúng năng lực thực tế của các hệ thống QA trên mạng xã hội, nhóm đề xuất bổ sung các nhóm câu hỏi có độ khó cao hơn:

1. **Câu hỏi phủ định (`NOT EXISTS` / `NONE`):**
   - *Ví dụ:* "Tìm những người dùng ở Pháp chưa từng đăng bài viết hay bình luận nào trong năm 2011?"
   - *Độ khó:* Đòi hỏi LLM phải dùng `NOT EXISTS { ... }` hoặc `WHERE NOT (...)`, tránh bẫy kết quả rỗng.
2. **So sánh tương đối giữa hai hoặc nhiều thực thể:**
   - *Ví dụ:* "Ai có nhiều bạn bè học cùng trường đại học hơn: Alice hay Bob?"
   - *Độ khó:* Đòi hỏi xử lý hai nhánh truy vấn song song, lồng `WITH` và so sánh đại số.
3. **Phân tích gộp lồng nhau (Aggregation on Aggregation):**
   - *Ví dụ:* "Thành phố nào có số lượng bài viết trung bình trên mỗi cư dân là cao nhất?"
   - *Độ khó:* Phải tính tổng bài viết theo từng người, sau đó gom nhóm theo thành phố để tính trung bình cộng (`avg`).
4. **Quan hệ có điều kiện lọc phức tạp trên cạnh:**
   - *Ví dụ:* "Đường đi ngắn nhất giữa A và B mà chỉ đi qua những mối quan hệ bạn bè được thiết lập trước năm 2011?"

---

## 6. Kết luận tổng kết T55

> **Kết luận:** Benchmark của nhóm **tương đối dễ đối với các mô hình ngôn ngữ lớn mạnh** và **bị phụ thuộc vào tính đồng nhất của template**. Mức điểm 78,9% (B3) và 98,9% (Proposed v0 trên dev) đạt được chủ yếu nhờ:
> 1. Đồ thị đơn miền với cấu trúc truy vấn ngắn ($\le 2$ hops chiếm hơn 80%).
> 2. Khuôn mẫu câu hỏi lặp lại theo template khiến mô hình zero-shot (B1) tụt 10–25% khi diễn đạt dài hoặc gián tiếp.
> 3. Các quy ước đặc thù trong module (A) và cơ chế tự sửa (D) đã giải quyết trọn vẹn các bẫy dữ liệu cục bộ.
>
> Nhóm cần công bố phát hiện này một cách trung thực trong mục **Threats to Validity** của báo cáo cuối kỳ, và cân nhắc đánh giá độ bền khi người dùng đặt câu hỏi tự do hoặc bổ sung các dạng câu hỏi lồng ghép đa bước.
