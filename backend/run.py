"""Convenience dev launcher: `python backend/run.py`.

Anchors the working directory to this file's folder so the local ``.env`` and
the SQLite ``demo.db`` resolve correctly regardless of where it is invoked from.
"""
from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
