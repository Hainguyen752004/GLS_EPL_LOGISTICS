from pathlib import Path


FRONTEND_JS = Path(__file__).resolve().parents[2] / "frontend" / "js"
APP_JS = FRONTEND_JS / "app.js"
# Endpoint hóa đơn đã chuyển từ main.py sang routes/accounting_routes.py.
ACCOUNTING_PY = Path(__file__).resolve().parents[1] / "app" / "routes" / "accounting_routes.py"


def test_giao_dien_khong_bao_gio_tu_khai_so_tien_hoa_don():
    """Số tiền hóa đơn do MÁY CHỦ tính, giao diện không được khai.

    BÀI NÀY TRƯỚC ĐÂY soi thân hàm `window.postInvoice` và đòi ba điều: không
    gửi `customer_id`, không gửi `total`, và không có con số cứng `2587500`.
    Ý nghĩa đó vẫn đúng và vẫn phải giữ — một máy khách khai được số tiền thì
    doanh thu là thứ người dùng gõ vào, không phải thứ hệ thống tính.

    Nhưng `window.postInvoice` ĐÃ BỎ. Nó là mã chết và là mã chết nguy hiểm: nó
    ghi một hóa đơn thật cùng bút toán sổ cái, cho lệnh giao hàng nó TỰ CHỌN
    bằng "lệnh đã giao đầu tiên tìm thấy". Chỗ gọi duy nhất là một nút trên thẻ
    minh họa ở Bảng điều khiển, và nút đó đã bỏ.

    Và không mất tính năng nào: hóa đơn được phát hành NGAY TRONG bước hoàn tất
    giao hàng — `delivery_completion_service` gọi `post_ar_invoice` trong cùng
    một giao dịch với POD và giá cuối.

    Nên bài kiểm nay chốt điều mạnh hơn: KHÔNG tệp giao diện nào được gửi số
    tiền tới đường lập hóa đơn. Quét toàn bộ thư mục `js`, không chỉ thân một
    hàm — đó cũng là chỗ bản trước yếu, vì nó chỉ canh đúng một hàm.
    """
    assert APP_JS.is_file()
    source = APP_JS.read_text(encoding="utf-8")

    # Hàm cũ không được sống lại. Phía giao diện có bài kiểm riêng
    # (`frontend/tests/dead-ui-cleanup.test.js`, mục 1b); đây là nửa phía máy
    # chủ, để một lần dọn ở một bên không lặng lẽ mở lại bên kia.
    # Soi PHÉP GÁN, không soi chữ. Trong `app.js` có một khối chú thích giải
    # thích vì sao hàm đó đã bỏ — bắt cả chữ thì buộc người sửa phải xóa đúng
    # phần giải thích khiến lần sau có người dựng lại hàm.
    import re
    assert not re.search(r"window\.postInvoice\s*=", source), (
        "window.postInvoice đã sống lại — hàm này ghi hóa đơn thật cho một lệnh "
        "giao hàng nó tự chọn, và bước hoàn tất giao hàng đã phát hành hóa đơn "
        "trong cùng giao dịch nên không màn nào cần nó"
    )

    # Và không tệp nào gửi số tiền tới đường lập hóa đơn.
    for tep in sorted(FRONTEND_JS.glob("*.js")):
        if tep.name.endswith(".min.js"):
            continue                      # thư viện ngoài, không phải mã của dự án
        ma = tep.read_text(encoding="utf-8", errors="replace")
        if "/api/invoices/post" not in ma:
            continue
        # Chỉ soi phần quanh chỗ gọi, để một chữ `total:` ở màn khác không
        # làm bài kiểm đỏ oan.
        i = ma.index("/api/invoices/post")
        quanh = ma[max(0, i - 1500):i + 1500]
        for cam in ("total:", "customer_id:", "2587500"):
            assert cam not in quanh, (
                "%s gửi %r tới /api/invoices/post — số tiền hóa đơn phải do máy "
                "chủ tính, không phải do máy khách khai" % (tep.name, cam)
            )


def test_invoice_endpoint_has_no_unreachable_legacy_posting_implementation():
    source = ACCOUNTING_PY.read_text(encoding="utf-8")
    start = source.index('@router.post("/api/invoices/post")')
    end = source.index("# 9. Dashboard API", start)
    endpoint = source[start:end]

    assert "Legacy implementation" not in endpoint
    assert 'data.get("total")' not in endpoint
    assert "GLTransaction(" not in endpoint
