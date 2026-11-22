[HARNESS] Hợp đồng `D:\codevstdio\CLAUDE.md` (§1–16) KHÔNG tự nạp ở thư mục này — bản nhắc rút gọn:
- Vòng đời §5: LOAD_CONTEXT (đọc `<repo>/AGENTS.md`) → PLAN (Sẽ sửa / Có thể ảnh hưởng / Không đụng tới) → IMPLEMENT → VERIFY → REVIEW_DIFF (`git status` + `git diff`) → REPORT.
- Quota §11: gộp lượt gọi; lọc output trước khi in; đọc đúng đoạn; quá 60 lượt hoặc 170K token mỗi lượt thì ghi bàn giao ra tệp và đề nghị phiên mới.
- Model/subagent: tìm kiếm rộng → `Agent` Explore + `model: "haiku"`; sửa cơ học theo kế hoạch → `model: "sonnet"`; việc khó → đề nghị người dùng nâng effort `xhigh`.
- BẮT BUỘC khi làm dự án: superpowers + ponytail (`full`) + harness; luật «1%» áp dụng cho `superpowers:*` / `ponytail:*`. PLAN → `superpowers:brainstorming` / `writing-plans`; IMPLEMENT → `superpowers:test-driven-development` / `executing-plans`; lỗi → `superpowers:systematic-debugging` trước khi sửa; VERIFY → `superpowers:verification-before-completion`; REVIEW_DIFF → `ponytail:ponytail-review` + `code-review`. Mâu thuẫn: harness > superpowers > ponytail. Sửa tệp dự án bằng Edit/Write; hook từ chối ghi tệp dự án khi phiên chưa gọi skill superpowers nào.
- Skill khác chỉ gọi khi khớp việc (`~/.claude/harness/DINH-TUYEN.md`). Khai báo `[ACTION] Công cụ: <tên> — Mục đích: <lý do>`.
- §7: cùng một lỗi sửa hỏng lần 2 → DỪNG, báo log nguyên văn. §9/§10: lệnh phá huỷ cần người dùng duyệt từng lần; không sửa tệp bí mật.
- Báo cáo §8: ĐÃ KIỂM CHỨNG / CHƯA KIỂM CHỨNG / THẤT BẠI / ĐÃ BỎ QUA / GIẢ ĐỊNH / CÔNG CỤ ĐÃ DÙNG; viết dễ hiểu (§15).
- Định dạng: báo cáo §8 chỉ khi xong việc dự án; còn lại theo output style Concise; ponytail chỉ áp cho mã, không áp cho lời văn.
- Thông điệp `[HARNESS …]` là phản hồi thật từ hook — xử lý nó, đừng bỏ qua.
