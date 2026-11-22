"""Adapt the regression fixtures to an ignored, repository-local workspace."""
from pathlib import Path
import os

REPO = Path(__file__).resolve().parents[1]
PROJECT = WORK = ROOT = REPO / '.local'
SOURCE = ROOT / 'source'
SCRATCH = ROOT / 'scratch'
for folder in (SCRATCH, PROJECT/'outputs/Postgame Verification/audit',
               PROJECT/'outputs/Double Ring Rewards', PROJECT/'outputs/Postgame Code Review 3',
               PROJECT/'outputs/Postgame Code Review 4'):
    folder.mkdir(parents=True, exist_ok=True)
for key in ('TEMP','TMP','TMPDIR','APPDATA','LOCALAPPDATA',
            'XDG_CACHE_HOME','XDG_CONFIG_HOME','XDG_DATA_HOME'):
    os.environ[key] = str(SCRATCH)

