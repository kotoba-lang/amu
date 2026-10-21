#!/usr/bin/env python3
"""Maintainer tool: (re)write SHA256SUMS for every file of this package (except SHA256SUMS and __pycache__)."""
import hashlib
from pathlib import Path
PKG = Path(__file__).resolve().parents[1]
files = sorted(p for p in PKG.rglob('*') if p.is_file() and p.name != 'SHA256SUMS' and '__pycache__' not in p.parts)
(PKG / 'SHA256SUMS').write_text(''.join('%s  %s\n' % (hashlib.sha256(p.read_bytes()).hexdigest(), p.relative_to(PKG)) for p in files))
print(len(files), 'files')
