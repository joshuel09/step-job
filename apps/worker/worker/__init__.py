"""Step Job background worker.

The worker shares the API's models rather than duplicating them, as the
constitution requires. That dependency is declared in pyproject.toml, but the
editable-install .pth files uv and hatchling generate carry no trailing newline,
so Python's site module silently skips them and the API package never reaches
sys.path. The failure is a bare ModuleNotFoundError at import time, with nothing
to indicate the cause.

Rather than requiring every invocation — compose, CI, a developer's shell — to
set PYTHONPATH correctly, the path is repaired here, once, and only when the
package is genuinely missing. Remove this when the editable install works.
"""

import sys
from importlib.util import find_spec
from pathlib import Path

if find_spec("app") is None:  # pragma: no cover - environment repair
    _api = Path(__file__).resolve().parents[2] / "api"
    if (_api / "app").is_dir():
        sys.path.insert(0, str(_api))
