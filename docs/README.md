# Tài liệu kỹ thuật EPL Logistics

- [Tài liệu cơ sở dữ liệu](DATABASE_SCHEMA_VI.md): mô tả 71 bảng, cột, khóa và quan hệ.
- [Tài liệu API](API_REFERENCE_VI.md): mô tả 170 API do FastAPI công bố, gồm tham số, từng trường request body và phản hồi.
- Swagger UI khi chay ung dung: `http://127.0.0.1:8001/docs`.
- OpenAPI JSON: `http://127.0.0.1:8001/openapi.json`.

Hai tài liệu schema/API được sinh trực tiếp từ mã nguồn đang chạy bằng lệnh:

```powershell
cd D:\Demo_Lao\EPL_System
C:\Users\zinnn\miniconda3\python.exe backend\scripts\generate_system_docs.py
```

Không sửa thủ công hai file được sinh. Hãy cập nhật SQLAlchemy model, Pydantic schema
hoặc mô tả route rồi chạy lại lệnh trên.
