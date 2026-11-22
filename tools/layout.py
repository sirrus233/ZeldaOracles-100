"""Repository-local paths and environment; no installation or network access."""
from pathlib import Path
import os

REPO = Path(__file__).resolve().parents[1]
LOCAL = REPO / '.local'
SOURCE = LOCAL / 'source'
SCRATCH = LOCAL / 'scratch'

def local_environment():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for key in ('TEMP', 'TMP', 'TMPDIR', 'APPDATA', 'LOCALAPPDATA',
                'XDG_CACHE_HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME'):
        os.environ[key] = str(SCRATCH)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    os.environ['PYTHONUTF8'] = '1'

