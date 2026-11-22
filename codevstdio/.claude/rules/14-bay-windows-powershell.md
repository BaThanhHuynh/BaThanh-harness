## 14. Bẫy Windows/PowerShell

- Sandbox chặn `Remove-Item $p.FullName` trong `foreach` — **cả khối không chạy**, dễ tưởng đã xoá. Liệt kê đường dẫn
  trước rồi `Remove-Item -LiteralPath "<đường dẫn>"` từng dòng.
- Không nhồi mã vào `python -c` / heredoc dài (PowerShell nuốt regex, Bash parse vỡ): viết tệp vào scratchpad rồi chạy.
- Hứng output tiến trình con bằng `subprocess.run(..., capture_output=True)`, không qua `>` (chèn BOM). CSV tiếng Việt
  cho Excel: `utf-8-sig`.
