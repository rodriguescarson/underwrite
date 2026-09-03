import os
from pathlib import Path

LEDGER = Path(__file__).parent / "_ledger"
os.environ["UNDERWRITE_LEDGER_DIR"] = str(LEDGER)
os.environ.setdefault("ALPACA_API_KEY", "PKTEST")
os.environ.setdefault("ALPACA_SECRET_KEY", "test")

import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def clean_ledger():
    LEDGER.mkdir(exist_ok=True)
    for f in LEDGER.glob("*.jsonl"):
        f.unlink()
    yield
