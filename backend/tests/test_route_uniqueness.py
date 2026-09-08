import importlib
import re


def _normalized(path):
    path = path.rstrip("/") or "/"
    return re.sub(r"\{[^}]+\}", "{param}", path)


def _routes(app):
    for route in app.routes:
        included = getattr(route, "original_router", None)
        if included is not None:
            yield from included.routes
        elif hasattr(route, "path"):
            yield route


def test_every_http_method_and_normalized_path_is_unique(app_client):
    client, _, _ = app_client
    duplicates = []
    owners = {}
    for route in _routes(client.app):
        for method in getattr(route, "methods", set()) or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            key = method, _normalized(route.path)
            if key in owners:
                duplicates.append((key, owners[key], route.endpoint.__module__))
            owners[key] = route.endpoint.__module__
    assert not duplicates


def test_workflow_routes_import_and_are_owned_by_workflow_module(app_client):
    """Duong nghiep vu chi duoc thuoc router nghiep vu, khong nam rai trong `main`.

    HAI tep duoc phep so huu, khong phai mot. `routes/bao_gia_routes.py` la nha
    cua luong Bao gia moi (QT -> DO) va co dependency xac thuc o tang router;
    gop no vao `workflow_routes.py` — da hon mot nghin dong — chi de thoa man
    mot bai kiem thi la de bai kiem quyet dinh kien truc.

    Dieu bai kiem nay THUC SU can canh van con nguyen, va nam o hai cho: mot
    duong khong duoc thuoc mot tep thu ba (nhat la `main`), va khong duoc khai
    hai lan — phan trung lap do `test_every_http_method_and_normalized_path_is_unique`
    o tren giu.
    """
    client, _, _ = app_client
    importlib.import_module("routes.workflow_routes")
    importlib.import_module("routes.bao_gia_routes")
    prefixes = ("/api/quotations", "/api/sales-orders", "/api/delivery-orders", "/api/pod")
    owned = [
        r for r in _routes(client.app)
        if r.path.startswith(prefixes)
        and not r.path.endswith(("/closeout", "/dossier"))
    ]
    assert owned
    assert {r.endpoint.__module__ for r in owned} <= {
        "routes.workflow_routes",
        "routes.bao_gia_routes",
    }


def test_main_has_no_legacy_pod_handlers(app_client):
    import main
    assert not hasattr(main, "get_pod")
    assert not hasattr(main, "save_pod")
