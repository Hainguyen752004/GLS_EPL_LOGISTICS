# Tài liệu kỹ thuật EPL Logistics

- [Tài liệu cơ sở dữ liệu](DATABASE_SCHEMA_VI.md): 60 bảng còn lại sau hai đợt dọn 10/09 (bỏ Đơn hàng SO; bỏ kế toán AR/AP, thuế, kỳ kế toán, Shipment 360), kèm cột, kiểu, khoá.
- [Tài liệu API](API_REFERENCE_VI.md): bảng 184 điểm cuối do FastAPI công bố (phương thức, đường dẫn, tóm tắt).
- Swagger UI khi chạy ứng dụng: `http://127.0.0.1:8001/docs` — bản đầy đủ tham số, request body và phản hồi.
- OpenAPI JSON: `http://127.0.0.1:8001/openapi.json`.
- Luồng nghiệp vụ và nhật ký rà soát: [ra-soat-hardcode-va-luong-20260910.md](ra-soat-hardcode-va-luong-20260910.md) (mục A1–A25).

Hai tài liệu schema/API là ảnh chụp sinh từ mã nguồn đang chạy (`app.openapi()` và `models.Base.metadata`)
ngày 10/09/2026; script sinh cũ (`generate_system_docs.py`) đã xoá cùng đợt dọn script demo. Cần bản
mới nhất thì mở Swagger ở trên — đó mới là nguồn sống.
