"""Chốt bảo vệ đường upload và tải về chứng từ POD."""

import importlib

import pytest


@pytest.fixture
def workflow_routes():
    return importlib.import_module("routes.workflow_routes")


PNG = b"\x89PNG\r\n\x1a\n"
JPEG = b"\xff\xd8\xff\xe0"
PDF = b"%PDF-1.7"


def test_mime_type_comes_from_content_not_from_the_client(workflow_routes):
    """Kiểu tệp do client khai được lưu lại rồi dùng làm media_type khi phục
    vụ, nên tin theo nó cho phép người gửi tự chọn cách trình duyệt diễn giải
    nội dung mình tải lên."""
    assert workflow_routes._verified_mime_type(PNG + b"x", "image/jpeg") == "image/png"
    assert workflow_routes._verified_mime_type(JPEG + b"x", "application/pdf") == "image/jpeg"
    assert workflow_routes._verified_mime_type(PDF + b"x", "image/png") == "application/pdf"


def test_content_that_matches_no_known_signature_is_refused(workflow_routes):
    """Khai là PNG nhưng nội dung không phải PNG thì phải bị từ chối."""
    from services.errors import DomainError

    with pytest.raises(DomainError) as excinfo:
        workflow_routes._verified_mime_type(b"<script>alert(1)</script>", "image/png")
    assert excinfo.value.args[0] == "POD_FILE_TYPE_INVALID"

    with pytest.raises(DomainError):
        workflow_routes._verified_mime_type(b"MZ\x90\x00", "application/octet-stream")


def test_oversized_content_is_rejected_with_413(workflow_routes):
    """Phải chặn ngay trong vòng lặp đọc file, không đợi tới tận service.

    Schema cho phép 100 mục, mỗi mục một POD kèm một chữ ký, mỗi file 10 MB —
    đọc hết rồi mới kiểm nghĩa là ~2 GB đã nằm trong RAM trước lời từ chối đầu.
    """
    from services.errors import DomainError
    from services.delivery_completion_service import MAX_POD_BYTES

    workflow_routes._reject_oversized(b"x" * 10, "POD_FILE_TOO_LARGE", "quá lớn")

    with pytest.raises(DomainError) as excinfo:
        workflow_routes._reject_oversized(
            b"x" * (MAX_POD_BYTES + 1), "POD_FILE_TOO_LARGE", "quá lớn"
        )
    assert excinfo.value.args[0] == "POD_FILE_TOO_LARGE"
    assert excinfo.value.args[2] == 413


def _seed_pod_document(db, models, *, suffix, mime_type, content, file_name):
    """Dựng đủ chuỗi phụ thuộc cho một chứng từ POD.

    delivery_pod_records có khóa ngoại tới delivery_orders và vehicles, và
    vehicle_id là NOT NULL, nên không thể tạo bản ghi POD đứng một mình.
    """
    db.merge(models.Customer(id="CUS-POD", name="Khách POD"))
    db.merge(models.Vehicle(id="VEH-POD", status="Sẵn sàng"))
    db.commit()
    db.merge(models.SalesOrder(
        id=f"SO-POD-{suffix}", customer_id="CUS-POD",
        canonical_status="confirmed", status="Confirmed", total_amount=1000000,
    ))
    db.commit()
    db.merge(models.DeliveryOrder(
        id=f"DO-POD-{suffix}", so_id=f"SO-POD-{suffix}", customer_id="CUS-POD",
        canonical_status="delivered", status="Delivered",
    ))
    db.commit()
    record = models.DeliveryPODRecord(
        idempotency_key=f"harden-{suffix}", do_id=f"DO-POD-{suffix}",
        vehicle_id="VEH-POD", stop_no=1, status="completed", created_by="test",
    )
    db.add(record)
    db.commit()
    document_id = f"PODDOC-HARDEN-{suffix}"
    db.add(models.DeliveryPODDocument(
        id=document_id, pod_record_id=record.id, file_name=file_name,
        mime_type=mime_type, file_size=len(content),
        checksum="a" * 64, content=content, created_by="test",
    ))
    db.commit()
    return document_id


def test_pod_download_is_attachment_with_nosniff(app_client):
    """PDF dựng khéo phục vụ inline từ chính origin ứng dụng sẽ chạy được
    JavaScript trong ngữ cảnh đó."""
    client, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")

    with database.SessionLocal() as db:
        document_id = _seed_pod_document(
            db, models, suffix="1", mime_type="application/pdf",
            content=PDF, file_name="chung-tu.pdf",
        )

    response = client.get(f"/api/pod-documents/{document_id}")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-disposition"].startswith("attachment;")


def test_unknown_stored_mime_type_is_served_as_octet_stream(app_client):
    """Bản ghi cũ có mime_type lạ không được tự chọn cách trình duyệt đọc nó."""
    client, _, _ = app_client
    database = importlib.import_module("database")
    models = importlib.import_module("models")

    with database.SessionLocal() as db:
        document_id = _seed_pod_document(
            db, models, suffix="2", mime_type="text/html",
            content=b"<h1>", file_name="la.html",
        )

    response = client.get(f"/api/pod-documents/{document_id}")

    assert response.status_code == 200
    assert "text/html" not in response.headers["content-type"]
    assert response.headers["content-type"].startswith("application/octet-stream")
