import sys
from pathlib import Path


def _ensure_local_backend_on_path() -> None:
    root_dir = Path(__file__).resolve().parents[1]
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))


_ensure_local_backend_on_path()
