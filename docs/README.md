# Tài liệu kỹ thuật EPL Logistics

**Hướng dẫn thao tác cho người dùng** — từng module, từng nút bấm, kèm bảng tra các lời từ chối
thường gặp. Ba bản cùng một nội dung, khác ngôn ngữ:

- Tiếng Việt: [bản Word](HUONG_DAN_SU_DUNG_VI.docx) · [bản Markdown](HUONG_DAN_SU_DUNG_VI.md)
- English: [Word](USER_GUIDE_EN.docx) · [Markdown](USER_GUIDE_EN.md)
- ພາສາລາວ: [Word](HUONG_DAN_SU_DUNG_LO.docx) · [Markdown](HUONG_DAN_SU_DUNG_LO.md)

Bản Word là bản để gửi đi và in. Sửa nội dung thì sửa tệp `.md` rồi sinh lại bản Word
bằng `backend/scripts/sinh_tai_lieu_word.py` (cần `pip install python-docx`).

Bản Lào dùng phông `Leelawadee UI` vì đó là phông duy nhất trên máy có glyph chữ Lào;
các ký hiệu mũi tên và biểu tượng dùng `Segoe UI Symbol`. Word KHÔNG tự thay phông khi
phông đã chỉ định thiếu glyph — nó vẽ ô vuông — nên bộ sinh chọn phông theo từng ký tự.

Các tài liệu bên dưới là tài liệu **kỹ thuật**, dành cho người viết mã và người nối hệ thống:

- [Hướng dẫn luồng và cấu hình dữ liệu gốc](HUONG_DAN_LUONG_VA_CAU_HINH_VI.md): đọc ĐẦU TIÊN nếu chưa biết gì về hệ — dữ liệu gốc cấu hình theo thứ tự nào, luồng Báo giá → Lệnh giao hàng → Chuyến → Hoàn tất → Bàn giao đi qua những màn nào, ai bấm gì, con số ở đâu ra.
- [Tài liệu API](API_REFERENCE_VI.md): toàn bộ điểm cuối theo nhóm nghiệp vụ, tham số, thân request, ghi chú cách dùng. Phần **★ dành cho bên công nợ (anh Khang)** nằm ngay đầu: hai API bàn giao (danh sách DO; header + chi tiết DO).
- [Tài liệu cơ sở dữ liệu](DATABASE_SCHEMA_VI.md): 57 bảng còn lại sau hai đợt dọn 10/09 (bỏ Đơn hàng SO; bỏ kế toán AR/AP, thuế, kỳ kế toán, Shipment 360, bảng di sản), kèm cột, kiểu, khoá, ràng buộc; có mục "bảng đã xoá".
- Swagger UI khi chạy ứng dụng: `http://127.0.0.1:8001/docs` — mẫu request/response sống. OpenAPI JSON: `http://127.0.0.1:8001/openapi.json`.
- Nhật ký rà soát và quyết định thiết kế: [ra-soat-hardcode-va-luong-20260910.md](ra-soat-hardcode-va-luong-20260910.md) (mục A1–A26).

Hai tài liệu API và schema là **sinh tự động** từ mã đang chạy (`main.app.openapi()` và `models.Base.metadata`)
bằng `backend/scripts/sinh_tai_lieu.py`. Khi đổi route hoặc model, chạy lại để tài liệu không lệch mã:

```
cd backend\app
C:\Users\zinnn\miniconda3\python.exe ..\scripts\sinh_tai_lieu.py
```

Mô tả từng API và từng bảng viết tay trong hai bảng `MO_TA_API` và `MO_TA_BANG` của script đó; điểm cuối
hoặc bảng mới chưa có mô tả sẽ hiện "(chưa có mô tả)" trong tài liệu — thêm vào script rồi sinh lại.
