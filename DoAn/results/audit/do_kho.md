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
| **B0 (Rule-based Regex)** | 40/40 (100.0%) | **1/40 (2.5%)** | **-97.5%** |
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
1. **B0 (Rule-based Regex) sụp đổ hoàn toàn khi câu hỏi bị biến đổi (100.0% -> 2.5%):**
   - Trên 40 câu dev gốc: B0 đạt **100.0% (40/40)** (và 92/92 trên toàn bộ tập `dev.json`) vì regex khớp chính xác 10 khuôn câu dev.
   - Nhưng khi câu hỏi được viết lại theo cách tự nhiên (`dev_para`): B0 rơi xuống còn đúng duy nhất **1/40 câu (2.5%)** (chỉ còn đúng 1 câu `AG-03-01` do còn giữ từ khóa "posts are tagged with"). Toàn bộ 39 câu còn lại trả về rỗng (`no_cypher`).
   - Trên tập kiểm thử độc lập (`test.json` gồm 15 templates mới): B0 đạt **0/150 (0.0%)** vì tuân thủ nghiêm ngặt nguyên tắc chống rò rỉ dữ liệu (không viết luật cho template chưa thấy trên dev).
   - Đây là bằng chứng thực nghiệm rõ nhất cho thấy hệ thống rule-based truyền thống hoàn toàn thất bại trước sự phong phú của ngôn ngữ tự nhiên, khẳng định sự cần thiết của các phương pháp LLM.
2. **B1 zero-shot có mức giảm nhẹ khi viết lại câu hỏi:** Khi câu hỏi trở nên tự nhiên hơn (thêm ngữ cảnh hoặc hỏi gián tiếp), EX của B1 giảm từ 20/40 (50.0%) xuống 18/40 (45.0%) (-5.0%, tức chỉ chênh lệch **2/40 câu**). Mức chênh 2 câu này chưa đủ lớn để khẳng định chắc chắn về sự phụ thuộc khuôn mẫu đối với B1, dù vẫn ghi nhận một số sai sót cục bộ ở nhóm `multi_hop` (-25.0%) và câu dài (`long`, -20.0%).
3. **Proposed v0 giữ độ bền rất cao (95.0% vs 97.5%):** Nhờ có các quy ước schema bao quát trong (A) và vòng tự sửa lỗi (D), Proposed v0 hầu như không bị ảnh hưởng bởi cách diễn đạt gián tiếp hay từ đồng nghĩa, chỉ bị sai 2 câu (chênh 1/40 câu giữa 2 lượt).

---

## 4. Bước 3 – So sánh với các Benchmark Text-to-Cypher đã công bố

Để trả lời câu hỏi: *"Con số B3 đạt 78,9% trên test và Proposed v0 đạt 98,9% trên dev là cao hay thấp?"*, nhóm đối soát trực tiếp với các số liệu có trong bài báo gốc (không nội suy hay quy đổi chéo giữa các metric khác nhau):

| Benchmark | Phạm vi (Domain) | Mô hình | Metric (theo bài gốc) | Kết quả công bố trong bài gốc | Đặc điểm độ phức tạp | Link nguồn |
|---|---|---|---|---|---|---|
| **CypherBench (2024)** *(Bảng 3, tập test 2.488 câu)* | Đa miền (7 đồ thị Wikidata quy mô lớn) | **Claude 3.5 Sonnet** (`20240620`, zero-shot) | **Execution Accuracy (EX)** | **61.58%** *(Exec: 96.34%)* | Đa đồ thị tri thức thật, schema lớn và phức tạp | [arXiv:2412.18702](https://arxiv.org/abs/2412.18702) |
| **CypherBench (2024)** *(Bảng 3, tập test 2.488 câu)* | Đa miền (7 đồ thị Wikidata) | **GPT-4o** (`20240806`, zero-shot) | **Execution Accuracy (EX)** | **60.18%** *(Exec: 94.93%)* | Như trên | [arXiv:2412.18702](https://arxiv.org/abs/2412.18702) |
| **CypherBench (2024)** *(Bảng 3, tập test 2.488 câu)* | Đa miền (7 đồ thị Wikidata) | **Qwen2.5-72B** / **Llama-3.1-70B** / `<10B` (zero-shot) | **Execution Accuracy (EX)** | **41.87%** / **38.84%** / **11.20%–18.82%** | Cho thấy chênh lệch lớn giữa mô hình mã nguồn mở và mô hình đóng trên đa đồ thị | [arXiv:2412.18702](https://arxiv.org/abs/2412.18702) |
| **Text2Cypher (Neo4j, 2024)** *(Bảng 5, 4.833 câu test)* | Đa miền (nhiều nguồn đồ thị gộp từ 44.387 mẫu) | `Llama-3.1-8B-it`, `Gemma-2-9B-it`, `GPT-4o-mini`, `GPT-4o` | **Google-BLEU** & **Exact Match** *(chỉ công bố $\Delta$ sau fine-tune ở Bảng 5; điểm gốc vẽ ở Hình 4)* | Cải thiện sau fine-tune ($\Delta$ Exact Match): **+0.11** (`Llama-3.1-8B`), **+0.07** (`Gemma-2-9B`), **+0.06** (`GPT-4o-mini`), **+0.01** (`GPT-4o`) | Chấm Exact Match chuỗi đầu ra và Google-BLEU, **không** dùng cùng thang EX để so trực tiếp tỉ lệ % | [arXiv:2412.10064](https://arxiv.org/abs/2412.10064) |
| **Nhóm 13 (LDBC SNB)** | **Đơn miền (Single-domain LDBC)** | **B3 (`gpt-oss-120b`, zero-shot)** | **Execution Accuracy (EX)** | **78.9%** *(tập test cũ)* | Đồ thị mạng xã hội cố định, câu hỏi sinh từ 25 template | Đồ án IS353 |
| **Nhóm 13 (LDBC SNB)** | **Đơn miền (Single-domain LDBC)** | **Proposed v0 (`gpt-oss-20b` + A + D)** | **Execution Accuracy (EX)** | **98.9%** *(tập dev)* | Có schema kèm quy ước chữa bẫy + tự sửa lỗi | Đồ án IS353 |

### Phân tích so sánh:
1. **Mức 78.9% của B3 cao hơn các mô hình mạnh trên CypherBench (~60–62%):** Trên benchmark đa miền CypherBench (7 đồ thị Wikidata lạ chưa từng gặp khi huấn luyện), ngay cả hai mô hình đóng hàng đầu là **Claude 3.5 Sonnet (61.58%)** và **GPT-4o (60.18%)** cũng chỉ đạt quanh ngưỡng ~60%, còn mô hình mở 70B (`Llama-3.1-70B`, `Qwen2.5-72B`) đạt **38.84%–41.87%**. Lý do chính khiến B3 (`gpt-oss-120b`) đạt tới **78.9%** ở đồ án là vì bài toán của nhóm mang tính **đơn miền (single-domain LDBC SNB)** với cấu trúc schema gọn cố định và độ dài bước quan hệ ngắn.
2. **Không đối chiếu số % trực tiếp với Text2Cypher (`arXiv:2412.10064`):** Bài báo Text2Cypher của Neo4j đánh giá bằng **Google-BLEU** và **Exact Match** (so sánh chuỗi đại diện kết quả/cú pháp, và phần bảng chỉ ghi chênh lệch $\Delta$ sau fine-tune ở Bảng 5), do đó chỉ tham khảo về mặt phương pháp luận chứ không dùng để so trực tiếp con số EX.
3. **Mức 98.9% của Proposed v0 trên Dev là quá cao (không đại diện cho hiệu năng thật):**
   - Bộ Dev chỉ có 10 template mẫu câu với 2–3 cách diễn đạt cố định.
   - Thành phần (A) của Proposed v0 đã cung cấp các quy ước viết Cypher giải quyết hầu hết các lỗi điển hình trên dev.
   - Cần đánh giá lại toàn bộ trên tập kiểm thử độc lập mới (`test2`) có độ khó cao hơn để kết luận khách quan.

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

> **Kết luận:** Benchmark của nhóm **tương đối dễ đối với các mô hình ngôn ngữ lớn mạnh** khi chạy trên phạm vi đơn miền, và có **tính đồng nhất cao theo khuôn mẫu template**. Cụ thể:
> 1. Đồ thị đơn miền với cấu trúc truy vấn ngắn ($\le 2$ hops chiếm hơn 80%), khiến B3 (`gpt-oss-120b`) đạt 78.9% — cao hơn đáng kể mức ~60% của GPT-4o / Claude 3.5 Sonnet trên benchmark đa miền phức tạp như CypherBench.
> 2. Tính đồng nhất theo template thể hiện rõ nhất ở hệ thống luật cứng B0 (tụt từ 40/40 xuống 1/40 trên `dev_para`), trong khi B1 (`gpt-oss-20b`) chỉ giảm nhẹ 2/40 câu (-5.0%) nên chưa đủ cơ sở để kết luận B1 phụ thuộc hoàn toàn vào khuôn chữ.
> 3. Các quy ước đặc thù trong module (A) và cơ chế tự sửa (D) đã giải quyết trọn vẹn các bẫy dữ liệu cục bộ trên dev (98.9%).
>
> Nhóm cần công bố phát hiện này một cách trung thực trong mục **Threats to Validity** của báo cáo cuối kỳ, và cân nhắc đánh giá độ bền khi người dùng đặt câu hỏi tự do hoặc bổ sung các dạng câu hỏi lồng ghép đa bước.
