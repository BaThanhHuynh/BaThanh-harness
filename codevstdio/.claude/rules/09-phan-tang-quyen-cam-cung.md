## 9. Phân tầng quyền và cấm cứng

READ (đọc, tìm, `git status/diff/log`): được · WRITE: chỉ trong phạm vi PLAN · EXECUTE (test, linter, build, app): chỉ
để kiểm chứng · DESTRUCTIVE (xoá tệp, đổi lịch sử git, gửi thư, đăng ra ngoài, đổi cấu hình hệ thống): lệnh đích danh
cho **từng lần**.

**Cấm cứng** trừ khi người dùng ra lệnh cho đúng lần đó: `git reset --hard` · `git checkout -- <file>` ·
`git clean -fd` · `git push --force` / `-f` · rebase / amend commit đã push · `rm -rf` · xoá tệp không do mình tạo ·
`pip install` ngoài venv · đổi Python / Node toàn cục · sửa `.env`, credentials, khoá riêng, chứng chỉ. Được phép một
lần không có nghĩa là được phép lần sau hay ở ngữ cảnh khác.

Thao tác khó hoàn tác: nhìn kỹ đích trước; tệp là bản duy nhất thì chuyển chỗ, không xoá, và nói rõ. Mã thử (script
đo, debug, dữ liệu giả) để trong scratchpad hoặc `tests/scratchpad/`, xong thì xoá — trừ script tái lập kết quả đã
công bố (thuộc repo, đặt đúng chỗ, tên rõ nghĩa).
