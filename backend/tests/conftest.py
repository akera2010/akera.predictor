import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="akeraten-test-")
os.environ["DEMO_MODE"] = "true"
os.environ["AKERATEN_DISABLE_SCHEDULER"] = "1"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "REDIS_URL"):
    os.environ.pop(k, None)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
