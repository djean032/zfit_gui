import os
import sys
from importlib.util import find_spec
from pathlib import Path


def _sanitize_qt_env() -> None:
    ld_library_path = os.environ.get("LD_LIBRARY_PATH")
    if not ld_library_path:
        return

    parts = [p for p in ld_library_path.split(":") if p]
    filtered = [p for p in parts if p.rstrip("/") not in {"/usr/lib", "/usr/lib64"}]

    if filtered:
        os.environ["LD_LIBRARY_PATH"] = ":".join(filtered)
    else:
        os.environ.pop("LD_LIBRARY_PATH", None)


def _prepare_qt_library_path() -> bool:
    spec = find_spec("PySide6")
    if spec is None or spec.origin is None:
        return False

    qt_lib_dir = Path(spec.origin).resolve().parent / "Qt" / "lib"
    if not qt_lib_dir.exists():
        return False

    current = os.environ.get("LD_LIBRARY_PATH", "")
    parts = [p for p in current.split(":") if p]
    qt_lib_str = str(qt_lib_dir)
    if qt_lib_str in parts:
        return False

    os.environ["LD_LIBRARY_PATH"] = ":".join([qt_lib_str, *parts])
    return True


def main() -> None:
    _sanitize_qt_env()

    if os.environ.get("ZSCAN_STUDIO_QT_BOOTSTRAPPED") != "1":
        os.environ["ZSCAN_STUDIO_QT_BOOTSTRAPPED"] = "1"
        if _prepare_qt_library_path():
            os.execvpe(
                sys.executable,
                [sys.executable, "-m", "zscan_studio.launcher", *sys.argv[1:]],
                os.environ,
            )

    from zscan_studio.main import main as app_main

    app_main()


if __name__ == "__main__":
    main()
