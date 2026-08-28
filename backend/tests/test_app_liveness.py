import builtins
import concurrent.futures
import importlib
import sys
import threading
import time
import types
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine


APP_DIR = Path(__file__).resolve().parents[1] / "app"
AI_UNAVAILABLE_MESSAGE = (
    "D\u1ecbch v\u1ee5 AI t\u1ea1m th\u1eddi kh\u00f4ng kh\u1ea3 d\u1ee5ng. "
    "Vui l\u00f2ng th\u1eed l\u1ea1i sau."
)


def _clear_app_modules():
    for name, module in list(sys.modules.items()):
        module_file = getattr(module, "__file__", None)
        if not module_file:
            continue
        try:
            Path(module_file).resolve().relative_to(APP_DIR.resolve())
        except (OSError, ValueError):
            continue
        sys.modules.pop(name, None)


def _reject_import(monkeypatch, rejected_name, error):
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == rejected_name or name.startswith(f"{rejected_name}."):
            raise error
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)


def test_main_import_does_not_connect_database_or_import_cv2(monkeypatch):
    _clear_app_modules()
    monkeypatch.setattr(
        Engine,
        "connect",
        lambda _self: (_ for _ in ()).throw(AssertionError("database connected")),
    )
    _reject_import(monkeypatch, "cv2", AssertionError("cv2 imported"))

    main = importlib.import_module("main")

    with TestClient(main.app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_frontend_html_is_served_with_utf8_charset_and_no_store_cache(monkeypatch):
    _clear_app_modules()
    main = importlib.import_module("main")

    client = TestClient(main.app)
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "charset=utf-8" in response.headers["content-type"].lower()
    assert response.headers["cache-control"] == "no-store"
    assert "T\u00f3m t\u1eaft &amp; Ph\u00e2n t\u00edch" in response.text
    assert "Danh M\u1ee5c \u0110\u1ed9i Xe" in response.text
    assert "\ufffd" not in response.text


def test_checkpoint_returns_503_vietnamese_error_when_cv2_is_unavailable(monkeypatch):
    _clear_app_modules()
    main = importlib.import_module("main")
    _reject_import(
        monkeypatch,
        "cv2",
        ImportError("C:/private/build/cv2_secret_extension.pyd is missing"),
    )

    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai/checkpoint/scan",
            files={"file": ("tiny.jpg", b"not-an-image", "image/jpeg")},
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "AI_DEPENDENCY_UNAVAILABLE",
            "message": AI_UNAVAILABLE_MESSAGE,
        },
        "error": {
            "code": "AI_DEPENDENCY_UNAVAILABLE",
            "message": AI_UNAVAILABLE_MESSAGE,
            "fields": [],
            "links": [],
        },
    }
    assert "private" not in response.text
    assert "cv2_secret_extension" not in response.text


def test_startup_database_error_is_sanitized(monkeypatch, caplog):
    _clear_app_modules()
    main = importlib.import_module("main")
    secret = "postgresql://secret-user:secret-pass@private-host/epl?token=hidden"
    monkeypatch.setattr(
        main, "auto_migrate_db", lambda: (_ for _ in ()).throw(RuntimeError(secret))
    )

    main.on_startup()

    output = caplog.text
    assert "DATABASE_STARTUP_UNAVAILABLE" in output
    for value in ("secret-user", "secret-pass", "private-host", "token", "hidden"):
        assert value not in output


def _install_fake_ai_modules(monkeypatch, *, decoded_frame=object(), engine_type=None):
    cv2 = types.ModuleType("cv2")
    cv2.error = type("CV2DecodeError", (Exception,), {})
    cv2.IMREAD_COLOR = 1
    cv2.imdecode = lambda _array, _mode: decoded_frame
    cv2.imencode = lambda _extension, _image: (True, b"encoded-image")
    numpy = types.ModuleType("numpy")
    numpy.uint8 = object()
    numpy.frombuffer = lambda contents, _dtype: contents

    if engine_type is None:
        class FakeEngine:
            def process_frame(self, _frame):
                return {"cropped_plate_img": None, "status": "processed"}

        engine_type = FakeEngine

    cv_engine = types.ModuleType("cv_engine")
    cv_engine.AICheckpointEngine = engine_type
    monkeypatch.setitem(sys.modules, "cv2", cv2)
    monkeypatch.setitem(sys.modules, "numpy", numpy)
    monkeypatch.setitem(sys.modules, "cv_engine", cv_engine)


def test_checkpoint_rejects_oversized_upload_before_ai_loading(monkeypatch):
    _clear_app_modules()
    main = importlib.import_module("main")
    _reject_import(monkeypatch, "cv2", AssertionError("AI loaded for oversized upload"))

    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai/checkpoint/scan",
            files={"file": ("large.jpg", b"x" * (main.MAX_CHECKPOINT_UPLOAD_BYTES + 1))},
        )

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "UPLOAD_TOO_LARGE"


def test_checkpoint_returns_400_for_malformed_image(monkeypatch):
    _clear_app_modules()
    main = importlib.import_module("main")
    _install_fake_ai_modules(monkeypatch, decoded_frame=None)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai/checkpoint/scan", files={"file": ("bad.jpg", b"bad")}
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_IMAGE"


def test_checkpoint_returns_400_for_empty_upload_without_decoding(monkeypatch):
    _clear_app_modules()
    main = importlib.import_module("main")
    _install_fake_ai_modules(monkeypatch)
    sys.modules["cv2"].imdecode = lambda *_args: (_ for _ in ()).throw(
        AssertionError("empty upload reached decoder")
    )

    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai/checkpoint/scan", files={"file": ("empty.jpg", b"")}
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_IMAGE"


def test_checkpoint_returns_sanitized_400_when_decoder_raises(monkeypatch):
    _clear_app_modules()
    main = importlib.import_module("main")
    _install_fake_ai_modules(monkeypatch)
    decode_error = sys.modules["cv2"].error
    sys.modules["cv2"].imdecode = lambda *_args: (_ for _ in ()).throw(
        decode_error("C:/private/decode-secret.dll")
    )

    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai/checkpoint/scan", files={"file": ("broken.jpg", b"image")}
        )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_IMAGE"
    assert "private" not in response.text
    assert "decode-secret" not in response.text


def test_checkpoint_preserves_valid_small_upload_behavior(monkeypatch):
    _clear_app_modules()
    main = importlib.import_module("main")
    _install_fake_ai_modules(monkeypatch)

    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai/checkpoint/scan", files={"file": ("small.jpg", b"image")}
        )

    assert response.status_code == 200
    assert response.json() == {"cropped_plate_img": None, "status": "processed"}


def test_checkpoint_returns_sanitized_503_when_numpy_is_unavailable(monkeypatch):
    _clear_app_modules()
    main = importlib.import_module("main")
    _reject_import(monkeypatch, "numpy", ImportError("C:/private/numpy_secret.pyd"))

    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai/checkpoint/scan", files={"file": ("small.jpg", b"image")}
        )

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "code": "AI_DEPENDENCY_UNAVAILABLE",
        "message": AI_UNAVAILABLE_MESSAGE,
    }
    assert "numpy_secret" not in response.text


def test_checkpoint_returns_sanitized_503_when_engine_constructor_fails(monkeypatch):
    _clear_app_modules()
    main = importlib.import_module("main")

    class BrokenEngine:
        def __init__(self):
            raise RuntimeError("C:/private/model?token=secret")

    _install_fake_ai_modules(monkeypatch, engine_type=BrokenEngine)
    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai/checkpoint/scan", files={"file": ("small.jpg", b"image")}
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "AI_DEPENDENCY_UNAVAILABLE"
    assert "private" not in response.text
    assert "secret" not in response.text


def test_checkpoint_initializes_once_and_serializes_processing(monkeypatch):
    _clear_app_modules()
    main = importlib.import_module("main")
    state = {"constructed": 0, "active": 0, "max_active": 0}
    state_lock = threading.Lock()

    class CountingEngine:
        def __init__(self):
            with state_lock:
                state["constructed"] += 1

        def process_frame(self, _frame):
            with state_lock:
                state["active"] += 1
                state["max_active"] = max(state["max_active"], state["active"])
            time.sleep(0.02)
            with state_lock:
                state["active"] -= 1
            return {"cropped_plate_img": None}

    _install_fake_ai_modules(monkeypatch, engine_type=CountingEngine)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(main._process_checkpoint, [b"image"] * 4))

    assert len(results) == 4
    assert state == {"constructed": 1, "active": 0, "max_active": 1}


def test_checkpoint_runs_blocking_work_in_threadpool(monkeypatch):
    _clear_app_modules()
    main = importlib.import_module("main")
    _install_fake_ai_modules(monkeypatch)
    calls = []

    async def fake_run_in_threadpool(function, *args):
        calls.append(function)
        return function(*args)

    monkeypatch.setattr(main, "run_in_threadpool", fake_run_in_threadpool)
    with TestClient(main.app) as client:
        response = client.post(
            "/api/ai/checkpoint/scan", files={"file": ("small.jpg", b"image")}
        )

    assert response.status_code == 200
    assert calls == [main._process_checkpoint]
