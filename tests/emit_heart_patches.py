"""Compatibility imports shared by the regression fixtures."""
import sys
from pathlib import Path
from repo_paths import PROJECT,WORK,SOURCE
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from bps import make_patch,apply_patch
