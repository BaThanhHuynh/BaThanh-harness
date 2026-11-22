# Rút gọn luật chung (đợt 1) — kế hoạch

> Thực thi: tự làm trong phiên (người dùng chọn «sửa ở đây», 22/11/2026). Thiết kế duyệt trong hội thoại.

**Mục tiêu:** phần nạp sẵn `D:\codevstdio\CLAUDE.md` + rule import từ 14,5 KB xuống ≤ 11 KB, không bỏ ý an toàn/kiểm chứng.

**Ràng buộc:** giữ nguyên số §1–16 và tên tệp (`harness.py` nhắc theo số) · không viết sang tiếng Anh · không đụng
`harness.py`, `AGENTS.md` các repo (đợt 2) · sao lưu ở `sao-luu/2026-11-22/truoc-rut-gon-luat/`.

**Điểm cần soát:** ý bị cắt mà không có nguồn khác thay (ponytail, system prompt, hook, `DINH-TUYEN.md`) · mốc trần
ngữ cảnh khớp harness (170K) · nhãn báo cáo §8 và dòng `[ACTION]` giữ nguyên dạng.

- [ ] **1. Kiểm trước (phải fail ngân sách):** `python -I kiem_luat.py` → `vượt ngân sách`.
- [ ] **2. Sửa:** §2 còn 1 dòng (ponytail lo) · §5 bỏ câu mô tả hook, gộp câu trùng §11 · §11 model → trỏ
  `DINH-TUYEN.md`, 200K → 170K · §14 bỏ BOM/`Set-Content`/here-string (system prompt + cảm biến BOM của harness) ·
  §15 còn phần output style không lo · §1, 7–10 gọt chữ thừa.
- [ ] **3. Kiểm sau:** `python -I kiem_luat.py` → `OK`; đọc lại từng tệp đối chiếu bảng giữ/bỏ.
- [ ] **4. Ghi** một mục `VAN-HANH.md` (ngày, số đo trước/sau, đường dẫn sao lưu).
