from pathlib import Path


APP_JS = Path(__file__).resolve().parents[2] / "frontend" / "js" / "app.js"
MAIN_PY = Path(__file__).resolve().parents[1] / "app" / "main.py"


def test_frontend_invoice_requests_only_identify_delivered_do_and_posting_time():
    source = APP_JS.read_text(encoding="utf-8")
    start = source.index("window.postInvoice = async function")
    end = source.index("window.submitIncident", start)
    post_invoice = source[start:end]

    assert "customer_id:" not in post_invoice
    assert "total:" not in post_invoice
    assert "2587500" not in post_invoice
    assert "do_id: doId" in post_invoice
    assert "posted_at: new Date().toISOString()" in post_invoice
    assert "if (!res.ok)" in post_invoice


def test_invoice_endpoint_has_no_unreachable_legacy_posting_implementation():
    source = MAIN_PY.read_text(encoding="utf-8")
    start = source.index('@app.post("/api/invoices/post")')
    end = source.index("# 9. Dashboard API", start)
    endpoint = source[start:end]

    assert "Legacy implementation" not in endpoint
    assert 'data.get("total")' not in endpoint
    assert "GLTransaction(" not in endpoint
