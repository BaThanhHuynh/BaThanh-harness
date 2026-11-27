# Mẫu và checklist cho `<repo>/AGENTS.md`

Không bắt buộc, chỉ để tham khảo khi viết tay. Ràng buộc nằm ở §12: phải có mục `INHERITANCE` trỏ về
`D:\codevstdio\CLAUDE.md`, chỉ được làm chặt thêm, dưới 12 KB. Repo chưa có `AGENTS.md` thì đừng tự tạo — tệp chỉ
có khung làm agent tưởng đã có tri thức dự án.

Khung sáu mục (đã dùng tốt ở `repo/MedicalGraph`, `repo/CredX`) — bỏ, thêm, đổi thứ tự đều được, miễn giữ mục 1:

```markdown
# REPOSITORY AGENTS RULES — <Tên dự án>

## 1. INHERITANCE
- Quy tắc chính: D:\codevstdio\CLAUDE.md. File này là quy tắc phụ, chỉ làm chặt thêm.

## 2. PROJECT CONTEXT & STACK
- Tên dự án, mục tiêu một câu, tech stack, lệnh chạy test chính thức.
- Bẫy lớn nhất của dự án (nếu có) — đặt ngay đây, đừng giấu ở cuối file.
- Bản đồ dữ liệu of-record nằm ngoài repo (nếu có).

## 3. LOCAL SKILLS & WORKFLOWS
- Các quy trình lặp lại được, mỗi quy trình vài gạch đầu dòng.

## 4. RESTRICTIONS
- Lệnh cấm, đánh dấu mức độ. Nêu hậu quả, không chỉ nêu cấm.

## 5. KNOWLEDGE
- Lỗi đã gặp và cách xử lý — ghi gì, khi nào, thăng cấp ra sao theo §13.

## 6. CÁCH LÀM VIỆC ĐÃ ĐƯỢC CHỐT
- Thói quen chủ dự án đã xác nhận: ngôn ngữ viết tài liệu, cách đóng gói, cách báo cáo.
```

Checklist rà lại (hai dấu đầu bắt buộc):

- [ ] Mục 1 trỏ đúng về `D:\codevstdio\CLAUDE.md` và nói rõ «chỉ làm chặt thêm».
- [ ] Không câu nào nới lỏng §1–§11 (tự ý refactor, mở rộng phạm vi, bỏ bước hỏi lại, bỏ kiểm chứng).
- [ ] Mọi đường dẫn, tên tệp, lệnh chạy trong file **đã kiểm là còn tồn tại**.
- [ ] Có ít nhất một mục `RESTRICTIONS` nêu hậu quả cụ thể, không chỉ nói «không nên».
- [ ] `KNOWLEDGE` ghi lỗi thật đã gặp, không phải lời khuyên chung chung.
- [ ] Dưới 12 KB (nạp lại mỗi lượt). Dài hơn thì tách phần tra cứu sang `docs/knowledge/`, để lại một dòng trỏ.
