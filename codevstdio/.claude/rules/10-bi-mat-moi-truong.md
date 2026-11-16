## 10. Bí mật và môi trường

Không bao giờ: in khoá API / token / mật khẩu / chuỗi kết nối; commit bí mật (kể cả tệp ví dụ, chú thích); sửa tệp bí
mật — cần đổi thì báo người dùng tự đổi; đổi xác thực / phân quyền khi không được yêu cầu đích danh; gửi nội dung repo
ra dịch vụ ngoài khi chưa được phép. Bí mật đã bị commit: **báo, không tự xử lý** — việc đầu tiên là thu hồi khoá; xoá
khỏi lịch sử là DESTRUCTIVE. Kiểm `venv` / `.venv` / `conda` **trước** khi cài thư viện; không cài toàn cục; không có
môi trường ảo thì hỏi, đừng tự tạo.
