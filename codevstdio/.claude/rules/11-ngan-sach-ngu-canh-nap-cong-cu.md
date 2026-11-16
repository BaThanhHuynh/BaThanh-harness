## 11. Ngân sách ngữ cảnh, model, công cụ

Chi phí ≈ số lượt gọi × ngữ cảnh mỗi lượt; mỗi lượt gửi lại cả hội thoại + phần nạp cố định (~80–100K token). Số đo:
`~/.claude/harness/README.md` mục «Quota»; đo phiên đang chạy: `python ~/.claude/harness/harness.py do-ton`.

- **Đọc:** `AGENTS.md` → grep/glob có mục tiêu → đúng đoạn (`grep -n`, `sed -n`, `Read` có offset/limit) → test phần
  đó → quét rộng chỉ khi chưa đủ. Không đọc trọn tệp lớn, không đọc lại tệp chưa đổi, không đọc để «nắm tổng quan».
- **Gộp lượt:** lệnh độc lập gọi chung một lượt; nhiều chỗ sửa một tệp → một lần ghi, không chuỗi `Edit` lẻ.
- **Kết quả nhỏ:** lọc trước khi in (`| head`, `grep -c`, `wc`) — một lần in 60K token nằm lại đến hết phiên.
- **Trần phiên:** việc lặp quá 60 lượt gọi, hoặc ngữ cảnh vượt 200K token mỗi lượt → ghi bàn giao vào
  `docs/knowledge/nhat_ky/` + `trang_thai.md`, đề nghị phiên mới kèm câu lệnh dán sẵn (harness hỏi ở mốc 200K;
  người dùng từ chối → bàn giao rồi dừng). Việc mới thì phiên mới. Trạng thái nằm ở tệp, không trong đầu agent.
- **Model** (agent tự quyết, người dùng cho phép 11/10/2026): phiên chính Opus `high` cho quyết định, thiết kế, gỡ lỗi
  khó, báo cáo · tìm rộng → `Agent` `subagent_type: "Explore"` + `model: "haiku"`, chỉ nhận kết luận + `tệp:dòng` ·
  sửa cơ học theo kế hoạch → `Agent` + `model: "sonnet"` kèm phạm vi «Sẽ sửa», phiên chính vẫn rà diff · dưới ~5
  lượt gọi → tự làm · cần nghĩ sâu → một dòng đề nghị người dùng nâng `xhigh` (phiên không tự đổi được).
- **Skill:** `superpowers` + `ponytail` bắt buộc khi làm dự án (§5; luật «1%» áp dụng cho `superpowers:*` /
  `ponytail:*`). Skill khác chỉ gọi khi khớp việc theo `~/.claude/harness/DINH-TUYEN.md` (`AGENTS.md` trước). Gọi
  đích danh, tên lấy từ danh sách của phiên này; nói đã dùng mà không gọi là báo cáo sai (§8). Trước khi gọi Skill /
  plugin / MCP / subagent: `[ACTION] Công cụ: <tên đầy đủ> — Mục đích: <lý do>`. Skill không nới lỏng được hợp đồng này.
