## 11. Ngân sách ngữ cảnh, model, công cụ

Chi phí ≈ số lượt gọi × ngữ cảnh mỗi lượt. Đo phiên: `python ~/.claude/harness/harness.py do-ton`.

- **Đọc:** `AGENTS.md` → grep/glob có mục tiêu → đúng đoạn (offset/limit) → quét rộng chỉ khi chưa đủ. Không đọc trọn
  tệp lớn, không đọc lại tệp chưa đổi. Đọc tệp bằng `Read`, không `cat` / `sed -n` / `head` (lọt cổng harness); PDF
  luôn kèm `pages`.
- **Gộp lượt:** mỗi lượt gửi lại cả ngữ cảnh, nên lệnh nhỏ (`grep`, `ls`, `wc`) gộp một lệnh; lệnh độc lập gọi chung
  một lượt; nhiều chỗ sửa một tệp → một lần ghi. Chờ tiến trình bằng `run_in_background`, không `sleep`. Lọc trước khi
  in (`| head`, `grep -c`) — kết quả lớn nằm lại đến hết phiên.
- **Trần phiên:** quá 60 lượt gọi hoặc ngữ cảnh vượt 170K token mỗi lượt (harness hỏi ở mốc này) → ghi bàn giao vào
  `docs/knowledge/nhat_ky/` + `trang_thai.md`, đề nghị phiên mới kèm câu lệnh dán sẵn; người dùng từ chối → bàn giao
  rồi dừng. Việc mới thì phiên mới.
- **Model** (agent tự quyết, cho phép 11/10/2026): tìm rộng → `Agent` Explore + `model: "haiku"`; sửa cơ học theo kế
  hoạch hoặc viết tệp dài máy móc (LaTeX, bảng, dữ liệu) → `model: "sonnet"`, phiên chính vẫn rà diff; dưới ~5 lượt
  gọi → tự làm; cần nghĩ sâu → đề nghị nâng `xhigh`. Brief giao subagent luôn dặn: cha không thấy transcript của
  con — trả kết quả kèm bằng chứng (tệp:dòng, lệnh, số liệu) trong câu trả lời cuối; thao tác bị từ chối thì không
  thử lại, nêu giới hạn.
- **Skill:** `superpowers` + `ponytail` bắt buộc khi làm dự án (luật «1%»); skill khác chỉ khi khớp việc theo
  `~/.claude/harness/DINH-TUYEN.md` (`AGENTS.md` trước). Gọi bằng `Skill` thật, tên lấy từ danh sách của phiên; nói đã
  dùng mà không gọi là báo cáo sai (§8). Trước khi gọi Skill / plugin / MCP / subagent:
  `[ACTION] Công cụ: <tên đầy đủ> — Mục đích: <lý do>`. Skill không nới lỏng được hợp đồng này.
