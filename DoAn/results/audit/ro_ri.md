# T56 – Kiểm tra rò rỉ dữ liệu (Khôi) – bản sơ bộ

> Mọi số liệu dưới đây lấy từ script chạy thật, kết quả nằm trong `results/audit/*.json`. Với test, tôi chỉ chạy script in số liệu tổng hợp (theo loại câu, theo `template_id`). Tôi không mở câu hỏi, gold hay Cypher dự đoán của test, và không mở `results/midterm/errors_B1.md` hay `RESULTS.md`.
>
> Môi trường: Neo4j 5 community (Docker, `docker-compose.yml`), LDBC SF0.1 với 327.588 node và 1.477.965 cạnh. Oracle trên dev đạt 92/92.
> Nhánh `khoi/audit-ro-ri` tạo từ `main` (khi chạy script lấy `run_eval.py`, `proposed_v0.py` và `results/runs/` từ `origin/bang/midterm` vì `main` chưa có các file này).

## 0. Mốc thời gian

| Sự kiện | Thời điểm (+07) | Nguồn |
|---|---|---|
| QA_GUIDELINE, README, graph_stats.md, load_ldbc.py, stats.py | 11/10 11:57 | commit `908f683` |
| B1 chạy **dev** xong | 20/10 16:23 (commit 16:25:35) | `9aa3d0a`, meta `llm_last_call_at` |
| **Lần gọi LLM đầu tiên trên test** (B1, B3) | **20/10 16:25:45** | meta `llm_first_call_at` của `results/runs/test/*` |
| B3 run 1 trên test xong (đã có lỗi test trên máy) | 20/10 16:37 | meta |
| Commit `errors_B1.md`, RESULTS.md | 20/10 20:34 | `a677088` |
| Commit `proposed_v0.py` (7 quy ước) | 21/10 09:45 | `e7ec2d2` |

Lưu ý: mốc đúng để xét rò rỉ là **16:25:45**, sớm hơn mốc 20:34 ghi trong file giao việc. Kết quả lỗi trên test đã có trên máy người chạy từ khoảng 16:37, trước khi commit.

## 1. Rò rỉ giá trị – `eval/audit/leak_values.py`

Các đoạn văn bản cố định được quét: `prompt`, `fix_prompt`, `conventions`, `schema` của mọi run dev, cùng `build_schema` của B1 lấy trực tiếp từ DB. Ba đoạn schema giống hệt nhau. Mỗi giá trị trong `params`, literal trong gold và `answer_preview` của dev/test được so ở cả dạng có `_` và dạng có dấu cách, không phân biệt hoa thường, khớp theo ranh giới từ.

| Trùng | Dev | Test | Đánh giá |
|---|---|---|---|
| Năm `2011` (ví dụ `m.creationDate.year = 2011` trong quy ước) | 8 câu (TM-02: 3, TM-04: 5) | 7 câu (TM-01: 5, TM-05: 2) | **Nhẹ.** Năm vốn có sẵn trong câu hỏi. Ví dụ này chỉ dạy cú pháp, không lộ đáp án, và đã có nguyên văn trong QA_GUIDELINE từ 11/10 |
| `'the'`, `'person'`, `'may'` | 2 câu + 1 câu | 3 câu | Trùng ngẫu nhiên: đáp án là họ "The", đáp án "Person", tháng "May". Không phải rò rỉ |
| Tên riêng hoặc tên thực thể (tag, nước, công ty…) | 0 | 0 | `sample_names()` loại đúng các tham số |
| Giá trị đáp án | 0 | 0 | – |

Module (A) chính thức (`detailed_schema`) chưa có. Khi có, script sẽ tự quét thêm, nếu module nằm ở `baselines/module_a.py` hoặc có hàm `detailed_schema`.

## 2. Nguồn gốc 7 quy ước trong `CONVENTIONS` (rò rỉ quy trình)

| # | Quy ước | Có trước test (16:25:45)? | Nguồn | Kết luận |
|---|---|---|---|---|
| 1 | KNOWS không chiều | **Có** | `eval/QA_GUIDELINE.md` mục 2, dòng 23 và 34, cùng README dòng 147 (`908f683`). Dev B1: 10 câu sai do viết `-[:KNOWS]->` (MH-03-01, -05, -06, -08…) | Hợp lệ |
| 2 | Chiều các quan hệ khác | **Có** | `results/graph_stats.md` bảng "Cạnh theo kiểu" (`908f683`), QA_GUIDELINE dòng 28 (`Person→City→Country`) | Hợp lệ |
| 3 | Tên dùng dấu `_` | **Có** | QA_GUIDELINE dòng 36: "Cypher gold dùng giá trị thật trong DB (`United_States`, `Muammar_Gaddafi`)" (`908f683`) | Có nguồn trước. Tuy vậy dev hầu như không lộ lỗi này (xem mục 3), trong khi test có nguyên một template AG-05 phụ thuộc vào nó |
| 4 | firstName có nhiều từ, so họ tên đầy đủ | **Có** (gián tiếp) | graph_stats dòng 72–76 ("Emperor of Brazil Dom Pedro II", "K. Bose"), `scripts/stats.py` có ghép `firstName + ' ' + lastName` (`908f683`). Dev B1 sai ở MH-03-01 ("Alfred Sorongo Leakey") và MH-03-06 ("Ernest B Karat") | Hợp lệ, có bằng chứng từ dev |
| 5 | `.year/.month/.quarter`; **"Cypher has no year() function"** | Một phần | Phần `.year` có trong QA_GUIDELINE dòng 30 (`908f683`), `.quarter` có trong `templates/temporal.json` (`067c7a3`). Cụm "year()" chỉ xuất hiện lần đầu ở `RESULTS.md`/`manual.json` của `a677088` (gói lỗi **test**). Dev B1 có **0** câu dùng `year()` | **Nghi rò rỉ** (mệnh đề `year()`) |
| 6 | Person.creationDate khác HAS_MEMBER.joinDate | **Có** (từ dev) | Dev B1 TM-02-01, -04, -07, -10 sai do hiểu "joined the network" là `joinDate`; run dev được commit lúc 16:25:35. Thuộc tính có trong `load_ldbc.py` | Hợp lệ, có bằng chứng từ dev |
| 7 | Trả về thuộc tính, không trả nguyên node | **Có** (từ dev) | Dev B1 có 6 câu sai do `RETURN u`/`RETURN f` (LK-03-02, -06, -09, MH-03-09…). Ghi chú bằng chữ "trả về nguyên node" thì chỉ có từ `a677088` (sau test) | Hợp lệ theo dev, nhưng văn bản ghi chú được viết sau khi xem test |

Kết luận mục 2:
- 6/7 quy ước có nguồn hợp lệ: tài liệu ngày 11/10 hoặc lỗi trên **dev**.
- Chỉ mệnh đề "Cypher has no year() function" không có nguồn trước test, nên **nghi rò rỉ**.
- Không chứng minh được động cơ. Quy ước được viết trong khoảng 20/10 16:37 – 21/10 09:44, lúc lỗi test đã có sẵn.

## 3. Mẹo bề mặt – `eval/audit/rescore_fix.py` (không gọi LLM)

Cách làm: lấy Cypher đã có trong file run, sửa máy móc, chạy lại ở chế độ chỉ đọc (timeout 30 s) rồi chấm bằng `judge`. Khi chạy lại bản chưa sửa, tất cả các run đều cho nhãn đúng/sai **trùng 100%** với file gốc.

EX trung bình (từng lượt ghi trong ngoặc):

| Run | Gốc | Sửa 1 (`_`) | Sửa 2 (KNOWS) | Sửa 3 (cả hai) |
|---|---|---|---|---|
| Dev B1 (20b) | 57,6% | 67,4% | 63,0% | **72,8%** |
| Dev proposed v0 | 98,9% | (32,6%)* | 98,9% | (32,6%)* |
| Test B1 (20b, run 1–2) | 48,3% (48,7 / 48,0) | 57,7% (58,0 / 57,3) | 63,7% (64,0 / 63,3) | **73,7%** (74,7 / 72,7) |
| Test B3 (120b, run 1–3) | 78,9% (77,3 / 80,7 / 78,7) | 86,0% (84,0 / 88,0 / 86,0) | 79,1% | **86,2%** (84,0 / 88,0 / 86,7) |

\*Sửa 1 làm hỏng proposed: proposed so khớp `firstName + ' ' + lastName = 'John Ahmad'`, nên khi thay dấu cách thành `_` thì tên người không còn khớp. Đây là giới hạn của cách sửa máy móc. Trên B1, Sửa 1 làm 1–2 câu đúng thành sai, trên B3 là 7–8 câu (LK-01/02, MH, PA, TM). Vì vậy các con số ở cột Sửa 1 là **cận dưới** của tác dụng thật.

Bảng rescore theo loại câu (số câu đúng / tổng số câu của loại; với test ghi từng lượt cách nhau bởi `/`):

| Split / Model | Loại câu (`n`) | Gốc | Sửa 1 (`_`) | Sửa 2 (KNOWS) | Sửa 3 (cả hai) |
|---|---|---|---|---|---|
| **Dev B1 (20b)** | `lookup` (17) | 14 (82,4%) | 14 (82,4%) | 14 (82,4%) | 14 (82,4%) |
| | `aggregation` (20) | 9 (45,0%) | **19 (95,0%)** | 9 (45,0%) | **19 (95,0%)** |
| | `multi_hop` (20) | 12 (60,0%) | 11 (55,0%) | **15 (75,0%)** | 14 (70,0%) |
| | `path` (16) | 5 (31,3%) | 5 (31,3%) | **7 (43,8%)** | **7 (43,8%)** |
| | `temporal` (19) | 13 (68,4%) | 13 (68,4%) | 13 (68,4%) | 13 (68,4%) |
| **Test B1 (20b, run 1/2)** | `lookup` (30) | 27 / 28 (91,7%) | 25 / 26 (85,0%) | 27 / 28 (91,7%) | 25 / 26 (85,0%) |
| | `aggregation` (30) | 13 / 14 (45,0%) | **29 / 30 (98,3%)** | 13 / 14 (45,0%) | **29 / 30 (98,3%)** |
| | `multi_hop` (30) | 20 / 18 (63,3%) | 20 / 18 (63,3%) | **22 / 24 (76,7%)** | 22 / 23 (75,0%) |
| | `path` (30) | 3 / 4 (11,7%) | 3 / 4 (11,7%) | **24 / 20 (73,3%)** | **26 / 21 (78,3%)** |
| | `temporal` (30) | 10 / 8 (30,0%) | 10 / 8 (30,0%) | 10 / 9 (31,7%) | 10 / 9 (31,7%) |
| **Test B3 (120b, run 1/2/3)** | `lookup` (30) | 30 / 29 / 29 (97,8%) | 27 / 26 / 26 (87,8%) | 30 / 29 / 29 (97,8%) | 27 / 26 / 26 (87,8%) |
| | `aggregation` (30) | 14 / 14 / 14 (46,7%) | **30 / 30 / 30 (100%)** | 14 / 14 / 14 (46,7%) | **30 / 30 / 30 (100%)** |
| | `multi_hop` (30) | 29 / 29 / 28 (95,6%) | 27 / 27 / 26 (88,9%) | 29 / 29 / 28 (95,6%) | 27 / 27 / 26 (88,9%) |
| | `path` (30) | 25 / 26 / 25 (84,4%) | 26 / 26 / 25 (85,6%) | 25 / 26 / 25 (84,4%) | 26 / 26 / 25 (85,6%) |
| | `temporal` (30) | 18 / 23 / 22 (70,0%) | 16 / 23 / 22 (67,8%) | 18 / 23 / 23 (71,1%) | 16 / 23 / 23 (68,9%) |

Chi tiết nổi bật theo loại câu và `template_id` (test, sai → đúng):
- **AG-05: 0/10 → 10/10 ở mọi lượt của cả B1 và B3, chỉ nhờ Sửa 1.** Template "0% ở cả hai model" hỏng hoàn toàn vì dấu `_`. Thông tin này liên quan trực tiếp đến T57 của Ân.
- AG-02, AG-04: +3/10 mỗi template, nhờ Sửa 1.
- Path (B1): 3 → 26/30 (run 1) và 4 → 21/30 (run 2), chủ yếu nhờ Sửa 2. Đóng góp lớn nhất là PA-04 và PA-05 (+8 đến +10 câu).
- Aggregation: 13–14 → 29–30/30 ở mọi model.
- Temporal và lookup: gần như không đổi.

Diễn giải:
- **Chỉ sửa dấu `_` thì B1 trên test tăng từ 48,3% lên 57,7%. Sửa cả hai bẫy thì lên 73,7%**, sát B3 (78,9%).
- Trên dev, hai bẫy giải thích **15,2 / 41,3 điểm** (≈ 37%) chênh lệch giữa B1 (57,6%) và proposed v0 (98,9%). Phần còn lại (≈ 26 điểm) đến từ các quy ước khác và vòng tự sửa (D).
- B3 thì gần như không mắc lỗi chiều KNOWS. Phần tăng của B3 chỉ đến từ dấu `_`, khoảng +7 điểm, và gần hết nằm ở AG-05.

## 4. Thiết kế thí nghiệm sạch (để Bằng đưa vào E2, **không chạy trên test bây giờ**)

- **Cấu hình:** proposed (A+D) với `CONVENTIONS` v0, so với proposed (A+D) với (A) sạch của Khôi. Hai bản dùng cùng model gpt-oss-20b, cùng (D), cùng prompt khung, chỉ khác khối (A).
- **(A) sạch:** chỉ viết từ dev và tài liệu có trước 20/10 16:25:45. Mỗi dòng trong (A) phải kèm nguồn (file + commit). Không có mệnh đề `year()`, trừ khi tìm được bằng chứng từ dev.
- **Chạy:** test, 3 lượt mỗi cấu hình, ở tuần 9–10, cùng batch runner.
- **Đo:** ΔEX = EX(v0) − EX(sạch), kèm khoảng tin cậy theo lượt và McNemar theo từng câu (gộp các lượt). ΔEX là **mức lợi tối đa** mà rò rỉ quy trình có thể mang lại. Báo cáo thêm theo loại câu và riêng template AG-05.
- **Đối chứng thêm:** B1 + Sửa 3 máy móc (đã có ở mục 3: 73,7%) làm mốc "chỉ chữa bẫy dữ liệu".

## 5. Kiểm tra nhanh – `eval/audit/leak_misc.py`

| Kiểm tra | Kết quả |
|---|---|
| Dev/test gần trùng (Jaccard trên từ ≥ 0,8, đã che tên riêng) | **Không**: 0/150. Phân bố Jaccard lớn nhất: phần lớn trong khoảng 0,3–0,5; chỉ 3 câu trong khoảng [0,7; 0,8) |
| Baseline đọc `gold`/`gold_answer`/`answer_preview` | **Không**. `b1_zeroshot.py` và `proposed_v0.py` sạch; chỉ `oracle.py` dòng 9 đọc gold (được phép) |
| Model đã thuộc LDBC chưa (tùy chọn) | **Chưa làm.** Cần `GROQ_API_KEY` trong `.env` |

## 6. Kết luận (sơ bộ)

- **Rò rỉ giá trị:** không có rò rỉ đáng kể. Chỉ có ví dụ năm 2011, trùng với 7 câu test; ví dụ này vô hại và đã có trong guideline từ trước.
- **Rò rỉ quy trình:** 6/7 quy ước có nguồn hợp lệ từ tài liệu 11/10 hoặc lỗi dev. Chỉ mệnh đề "no year() function" là nghi rò rỉ. Dù vậy, quy ước được soạn lúc lỗi test đã có sẵn, nên vẫn cần thí nghiệm sạch ở mục 4 để chặn trên tác động.
- **Mẹo bề mặt:** đây là vấn đề lớn nhất. Hai bẫy dữ liệu (dấu `_` và chiều KNOWS) là các quy ước đã có tài liệu từ trước, nên không phải rò rỉ. Tuy vậy, chúng một mình đưa B1 trên test từ 48,3% lên 73,7% và B3 từ 78,9% lên 86,2%. Riêng template AG-05 hỏng 100% chỉ vì dấu `_`. Vì vậy phần lớn "cải thiện" của (A) nên được báo cáo là **chữa bẫy dữ liệu**, không phải năng lực chung. Đề nghị Bảo và Ân xem lại AG-05: câu hỏi có cho người đọc cách nào biết tên tag dùng `_` không.

## Tái lập

```powershell
cd DoAn; docker compose up -d; python scripts/load_ldbc.py   # LDBC_DIR nếu data nằm chỗ khác
python eval/audit/leak_values.py     # -> results/audit/leak_values.json
python eval/audit/rescore_fix.py     # -> results/audit/rescore_fix.json (~3 phút)
python eval/audit/leak_misc.py       # -> results/audit/leak_misc.json
```
