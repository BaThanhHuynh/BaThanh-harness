## 8. Điều kiện hoàn thành và báo cáo

`DONE` chỉ khi đủ bảy: triển khai xong · đã chạy kiểm chứng liên quan · pass, hoặc hỏng đã báo kèm log · đã đọc diff
cuối (§6) · không tệp nào sửa ngoài ý định · không sót mã thử / dữ liệu giả (§9) · báo cáo đã phân loại. «Đã viết mã»
≠ «xong».

Báo cáo phân loại, bỏ dòng không có:

```
ĐÃ KIỂM CHỨNG    <việc + cách kiểm chứng + kết quả>
CHƯA KIỂM CHỨNG  <việc + lý do chưa kiểm được>
THẤT BẠI         <việc + log nguyên văn>
ĐÃ BỎ QUA        <việc + lý do>
GIẢ ĐỊNH         <giả định đã dùng khi tự quyết (§1)>
CÔNG CỤ ĐÃ DÙNG  <skill / plugin / MCP / subagent + dùng để làm gì>
```

Lời nước đôi («chắc là chạy được», «về cơ bản xong») thuộc CHƯA KIỂM CHỨNG. Đã kiểm thì nói thẳng, không rào đón.
