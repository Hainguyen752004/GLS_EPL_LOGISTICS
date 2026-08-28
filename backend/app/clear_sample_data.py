"""Deprecated destructive entry point; use ``python -m data_cleanup``."""


def clear_orders():
    raise RuntimeError(
        "Unsafe blanket deletion is disabled; use the manifest-driven data_cleanup CLI"
    )


if __name__ == "__main__":
    clear_orders()
