## 14. Bẫy Windows/PowerShell (vấp ngay lúc chạy lệnh)

- `>` của PowerShell chèn BOM → `JSONDecodeError: Unexpected UTF-8 BOM`. Hứng output bằng
  `subprocess.run([...], capture_output=True)`; ghi tệp bằng `Out-File -Encoding utf8` (`Set-Content` mặc định ANSI).
  CSV tiếng Việt cho Excel: `utf-8-sig`.
- Sandbox chặn `Remove-Item $p.FullName` trong `foreach` — **cả khối lệnh không chạy**, dễ tưởng đã xoá. Liệt kê đường
  dẫn bằng lệnh riêng rồi `Remove-Item -LiteralPath "<đường dẫn>"` từng dòng.
- PowerShell nuốt regex / chuỗi nhiều dòng (`Missing closing ')'`); heredoc dài trong Bash cũng có thể vỡ khi parse.
  Đừng nhồi mã vào `python -c` hay heredoc: viết tệp vào scratchpad rồi chạy. Here-string `@'...'@`, `'@` ở **cột 0**.
