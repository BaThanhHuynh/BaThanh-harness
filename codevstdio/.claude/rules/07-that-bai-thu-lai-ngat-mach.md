## 7. Thất bại, thử lại, ngắt mạch

`FAILED` ≠ `DONE`, `UNVERIFIED` ≠ `DONE`. Kiểm hỏng: chẩn đoán trước — do mình thì sửa nguyên nhân gốc, chạy lại đúng
phần kiểm; không do mình thì không sửa mã không liên quan, báo rồi làm tiếp phần còn lại; không sửa an toàn được thì
dừng, đưa log nguyên văn, nói đã kiểm đến đâu, không tuyên bố xong.

**Ngắt mạch** (cùng một lỗi — cùng bản chất, cùng thông báo): sửa hỏng lần 1 → chẩn đoán lại, đổi giả thuyết; **lần 2
→ DỪNG**: log, giả thuyết đã loại, hướng đề xuất, chờ người dùng. Dừng sớm hơn nếu: bản sửa không dựa trên hiểu biết
mới; số tệp phải sửa tăng mà gốc chưa rõ; muốn sửa test cho khớp mã. Không đoán thêm, không đổi kiến trúc để né lỗi.
