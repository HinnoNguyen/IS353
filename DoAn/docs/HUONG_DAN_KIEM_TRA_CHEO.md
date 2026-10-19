# Hướng dẫn kiểm tra chéo bộ câu hỏi

Mục đích: kiểm tra **đáp án gold** của bộ câu hỏi có đúng không. Gold sai thì model trả lời đúng vẫn bị chấm sai, và mọi con số trong báo cáo đều sai theo.
Cách làm: **một người không viết template** đọc câu hỏi, **tự viết Cypher mà không xem gold**, rồi so kết quả của mình với gold.

- Người kiểm tra làm **cả 5 loại**: mỗi loại 10 câu, tổng cộng **50 câu**. Câu được chọn ngẫu nhiên với seed cố định.
- Thời gian dự kiến khoảng 3–4 giờ (3–5 phút mỗi câu).
- Quy định đầy đủ nằm ở [QA_GUIDELINE.md](../eval/QA_GUIDELINE.md), mục 2 và mục 6.

---

## Bước 0 – Chuẩn bị

1. Có Neo4j chạy trên máy và đã nạp dữ liệu (xem `HUONG_DAN_CAI_DAT.md`). Kiểm tra:
   ```powershell
   docker start graphqa-neo4j
   ```
2. Lấy code mới nhất:
   ```powershell
   cd <repo>
   git fetch
   git checkout bao/lookup-templates
   git pull
   ```
3. Đọc kỹ **mục 2 (quy ước ngữ nghĩa)** trong `eval/QA_GUIDELINE.md`. Gold được viết theo đúng các quy ước này.

## Bước 1 – Lấy câu hỏi

Chạy lệnh dưới, thay `Tên` bằng tên của bạn (ví dụ `Ân`):

```powershell
cd <repo>\DoAn
python eval/cross_check.py export --reviewer Tên
```

Lệnh tạo ra file `eval/cross_check/Tên.json` gồm 50 câu. Mỗi câu có dạng:

```json
{ "id": "AG-02-03", "type": "aggregation",
  "question": "Which city in Afghanistan has the most residents?",
  "my_cypher": "" }
```

> ⚠️ **Không mở** các file `eval/questions/*.json` và `eval/templates/*.json`, vì trong đó có gold. Xem gold trước thì kết quả kiểm tra chéo không còn giá trị.

## Bước 2 – Tự viết Cypher

Với từng câu:
1. Viết và chạy thử truy vấn trong Neo4j Browser (<http://localhost:7474>).
2. Khi thấy đúng, dán truy vấn **trên một dòng** vào trường `my_cypher`.
3. Câu nào không biết cách viết thì để trống và ghi chú lại để hỏi.

### Quy ước phải theo (tóm tắt mục 2 của guideline)

| Trong câu hỏi | Viết Cypher |
|---|---|
| friend(s), knows | `-[:KNOWS]-` **không có mũi tên** (mỗi cặp bạn chỉ lưu một chiều) |
| post(s) / comment(s) / message(s) | `:Post` / `:Comment` / `:Message` (cả hai) |
| lives in \<country\> | `(:Person)-[:IS_LOCATED_IN]->(:City)-[:IS_PART_OF]->(:Country)` |
| in \<year\>, quarter, month | Theo UTC: `x.creationDate.year = 2011`, `.quarter`, `.month` |
| how many … | `count(DISTINCT x)` |
| the most / the largest | `ORDER BY n DESC LIMIT 1` |
| category (của chủ đề/tag) | `TagClass` qua `HAS_TYPE` |

### Mẹo

- **Tên trong câu hỏi là tên tự nhiên, trong DB dùng dấu gạch dưới.** Ví dụ câu hỏi ghi "United Kingdom" thì DB lưu `United_Kingdom`. Tra giá trị đúng trước khi viết:
  ```cypher
  MATCH (t:Tag) WHERE t.name CONTAINS 'Aung' RETURN t.name
  ```
- Tên tag được đặt trong ngoặc kép trong câu hỏi, vì nhiều tag là tên bài hát hoặc tác phẩm.
- Person dùng `firstName` và `lastName`, không có `name`. Một số firstName có dấu cách, ví dụ "Emperor of Brazil".
- **Đặt cột đáp án lên đầu** trong `RETURN`. Được thêm cột phụ, ví dụ cột đếm `n`.
- Trong JSON, viết chuỗi trong Cypher bằng **dấu nháy đơn** (`'Afghanistan'`) để không phải escape dấu nháy kép.

## Bước 3 – Chấm

```powershell
python eval/cross_check.py compare --reviewer Tên
```

Script chạy Cypher của bạn và gold, chấm bằng cùng hàm dùng để chấm model, rồi in ra:

```
Loại         Đã làm  Khớp  Đồng thuận
lookup           10    ...
...
Cần thảo luận (n):
  AG-03-01 [không khớp] How many posts are tagged with "..."?
```

Kết quả chi tiết được lưu ở `eval/cross_check/Tên_result.json`. Mỗi câu có Cypher của bạn, gold, vài dòng kết quả của mỗi bên và nhãn khớp / không khớp / lỗi. **Chỉ từ bước này mới được xem gold.**

> ⚠️ **Sau khi chấm, không sửa lại `my_cypher`.** Kể cả khi nhận ra mình viết sai, hãy giữ nguyên và ghi nguyên nhân ở bước 4. Sửa lại để "cho khớp" sẽ làm tỉ lệ đồng thuận bị phóng đại.

## Bước 4 – Thảo luận các câu không khớp

Mở `Tên_result.json`. Với mỗi câu **không khớp** hoặc **lỗi**, cùng Bảo (tác giả template) xem lại rồi điền 2 trường:

| `cause` (nguyên nhân) | Nghĩa |
|---|---|
| `gold_sai` | Gold viết sai |
| `cau_mo_ho` | Câu hỏi hiểu được theo hai cách và cách nào cũng hợp lý |
| `nguoi_kiem_tra_sai` | Cypher của người kiểm tra sai |

| `action` (xử lý) | Nghĩa |
|---|---|
| `sua_gold` | Bảo sửa gold trong template |
| `sua_cau` | Sửa câu hỏi, hoặc bổ sung quy ước vào guideline mục 2 |
| `giu` | Gold đúng, giữ nguyên |
| `loai` | Không thống nhất được, loại câu |

Chạy lại `compare` vẫn giữ nguyên các trường `cause` và `action` đã điền.

## Bước 5 – Nộp

Commit 2 file `eval/cross_check/Tên.json` và `eval/cross_check/Tên_result.json`, hoặc gửi trực tiếp cho Bảo. Đây là bằng chứng cho phần kiểm tra chéo trong báo cáo.

---

## Output cuối cùng

| Sản phẩm | Ai làm | Dùng cho |
|---|---|---|
| `Tên.json`: 50 câu Cypher tự viết | Người kiểm tra | Bằng chứng |
| `Tên_result.json`: khớp/không khớp, nguyên nhân, xử lý | Người kiểm tra + Bảo | Danh sách câu cần sửa/loại |
| Bảng tỉ lệ đồng thuận theo 5 loại (in ra ở bước 3) | Hương tổng hợp | Đưa vào báo cáo |
| Template đã sửa → sinh lại câu → chia lại dev/test → **đóng băng test** | Bảo | Bộ câu hỏi chính thức |

**Ngưỡng:** loại nào có tỉ lệ đồng thuận **dưới 90%** thì phải rà lại toàn bộ câu của loại đó (script tự đánh dấu).

Sau khi sửa xong, Bảo chạy lại theo thứ tự:
```powershell
python eval/generate_questions.py
python eval/split_dev_test.py      # tự điền checked_by từ kết quả kiểm tra chéo + tính mã băm test mới
python eval/cross_check.py compare --reviewer Tên   # xác nhận các câu đã sửa giờ khớp
```

Khi sinh lại, câu của một template đã sửa có thể bị đổi. Những câu như vậy được đánh dấu **"câu đã đổi"** và không tính vào tỉ lệ đồng thuận. Nếu cần, người kiểm tra viết lại Cypher cho các câu này.
