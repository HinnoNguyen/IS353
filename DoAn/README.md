# Đồ án A.22 – Building a Simple Graph-Based Question Answering Tool

Nhóm 13 · IS353.R11 · GVHD: ThS. Trần Hưng Nghiệp

Công cụ hỏi đáp trên đồ thị mạng xã hội **LDBC SNB (SF0.1)** lưu trong **Neo4j**: câu hỏi tiếng Anh được LLM mã nguồn mở chuyển thành truy vấn **Cypher**, chạy trên đồ thị và trả lời bằng văn bản. Bài toán được đánh giá như Text-to-Cypher (execution accuracy) với baseline từ đơn giản đến mạnh.

Chi tiết: [proposal v2](docs/SNA-Group13-A.22-GraphQA-Proposal-v2.docx) · phân công & timeline: [Phan_cong_Nhom13_GraphQA.xlsx](docs/Phan_cong_Nhom13_GraphQA.xlsx)

## Cấu trúc thư mục

```
DoAn/
├── scripts/
│   ├── load_ldbc.py        # nạp LDBC SNB SF0.1 (CSV) vào Neo4j
│   └── stats.py            # thống kê đồ thị -> results/graph_stats.md
├── eval/
│   ├── QA_GUIDELINE.md     # quy ước xây bộ câu hỏi QA (bắt buộc đọc trước khi viết câu hỏi)
│   ├── pilot_questions.json# 10 câu hỏi thử nghiệm kèm Cypher gold
│   └── pilot_text2cypher.py# baseline B1 (LLM zero-shot) + chấm execution accuracy
├── results/
│   └── graph_stats.md      # thống kê đồ thị đã đếm trong Neo4j
├── docs/                   # proposal, file phân công
├── requirements.txt
└── .env.example            # mẫu biến môi trường (copy thành .env)
```

`data/` (dữ liệu LDBC, ~89 MB) và `.env` (API key) **không** được đưa lên git.

## Chạy lại từ đầu

**1. Cài thư viện**

```bash
cd DoAn
python -m pip install -r requirements.txt
```

**2. Tải dữ liệu.** Vào <https://ldbcouncil.org/benchmarks/snb/datasets/>, mục *SNB Interactive v1 → Initial datasets*, tải ô **hàng `CsvComposite & LongDateFormatter`, cột `0.1`**. Giải nén vào `DoAn/data/` để có thư mục:

```
DoAn/data/social_network-sf0.1-CsvComposite-LongDateFormatter/{static,dynamic}/*.csv
```

File là `.tar.zst`; có thể giải nén bằng Python (`pip install zstandard`):

```python
import tarfile, zstandard
with open("social_network-sf0.1-CsvComposite-LongDateFormatter.tar.zst", "rb") as f, \
     zstandard.ZstdDecompressor().stream_reader(f) as r, tarfile.open(fileobj=r, mode="r|") as t:
    t.extractall("data", filter="data")
```

**3. Chạy Neo4j bằng Docker**

```bash
docker run -d --name graphqa-neo4j -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/graphqa123 -v graphqa-neo4j-data:/data neo4j:5-community
```

Mật khẩu `graphqa123` chỉ là mặc định cho máy cá nhân; đổi được qua `NEO4J_PASSWORD` trong `.env`.

**4. Nạp dữ liệu và kiểm tra** (khoảng 1 phút)

```bash
python scripts/load_ldbc.py
python scripts/stats.py      # phải ra 327.588 node và 1.477.965 cạnh
```

Xem đồ thị: <http://localhost:7474> (user `neo4j`).

**5. Sinh bộ câu hỏi từ template**

```bash
python eval/generate_questions.py                 # mọi loại trong eval/templates/
python eval/generate_questions.py --type lookup   # chỉ một loại
```

Template của từng loại nằm trong `eval/templates/<loại>.json` (khuôn mẫu: `lookup.json`). Kết quả ghi vào `eval/questions/<loại>.json`, 10 câu mỗi template, seed cố định nên chạy lại ra đúng bộ câu cũ. Câu bị loại tự động: đáp án rỗng/0, quá 20 dòng, chạy quá 10 s, người trùng họ tên, câu trùng, thực thể đã dùng trong `pilot_questions.json`.

**6. Chạy thử baseline B1**

```bash
cp .env.example .env         # rồi điền key của bạn vào .env
python eval/pilot_text2cypher.py
```

Kết quả lưu trong `results/pilot_<thời gian>.md|json`. Chọn LLM bằng `LLM_BACKEND` trong `.env` (`ollama` hoặc `gemini`; backend Groq đang được bổ sung).

## Số liệu đồ thị (LDBC SNB SF0.1)

| | Số lượng |
|---|---|
| Node / cạnh | 327.588 / 1.477.965 |
| Person / KNOWS | 1.528 / 14.073 |
| Post / Comment | 135.701 / 151.043 |
| Loại node / kiểu quan hệ | 8 / 15 |

Lưu ý khi viết Cypher: mỗi cặp bạn bè chỉ lưu **một cạnh KNOWS theo một chiều** → luôn viết `-[:KNOWS]-` (không chiều). Xem thêm [eval/QA_GUIDELINE.md](eval/QA_GUIDELINE.md).
