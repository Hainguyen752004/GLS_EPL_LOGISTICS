from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "app"
FILES = [
    ROOT / "main.py",
    ROOT / "models.py",
    ROOT / "routes" / "workflow_routes.py",
    ROOT / "routes" / "health_routes.py",
    ROOT / "routes" / "tms_planning_routes.py",
    ROOT / "routes" / "tms_finance_routes.py",
    ROOT / "services" / "workflow_service.py",
    ROOT / "services" / "tms_ap_service.py",
    ROOT / "services" / "tms_cost_service.py",
    ROOT / "services" / "errors.py",
]

BAD_TOKENS = [
    "Ãƒ", "Ã„", "Ã¡Âº", "Ã¡Â»", "Ã¢Å“", "Ã¢Å¡", "Ã°Å¸", "VNÃ„",
    "Kh?", "B?", "H?a", "D?ch", "ch?a", "s?n", "Vui l?ng", "??", "?ang",
]


def test_backend_source_has_no_mojibake_in_user_facing_flow_files():
    failures = []
    for file_path in FILES:
        lines = file_path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            if any(token in line for token in BAD_TOKENS):
                failures.append(f"{file_path.relative_to(ROOT)}:{line_number}: {line[:180]}")

    assert not failures, "Phát hiện lỗi tiếng Việt trong backend:\n" + "\n".join(failures[:40])
