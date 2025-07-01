"""
symbolica.runtime.api
=====================

Optional REST micro-service that wraps the in-process Symbolica runtime.
Requires:

    pip install fastapi[all] uvicorn

Start a local server via the CLI wrapper:

    symbolica run --rpack rulepack.rpack --port 8080
"""

from __future__ import annotations

import pathlib
from typing import Any, Dict, Optional

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
    from starlette.responses import JSONResponse

    from .loader import load_pack, get_pack
    from .evaluator import infer

    app = FastAPI(title="Symbolica Runtime", version="0.1.0")

    # ─────────────────────────────  Pydantic models  ─────────────────────────

    class InferRequest(BaseModel):
        facts: Dict[str, Any]
        agent: str = Field(..., description="Agent / registry name")
        trace_level: str = Field(
            "compact", regex="^(compact|verbose|debug)$"
        )
        rulepack: Optional[pathlib.Path] = Field(
            None,
            description="Optional override .rpack path; "
            "if omitted, uses the pack already loaded in memory.",
        )

    class InferResponse(BaseModel):
        verdict: Dict[str, Any]
        trace: Dict[str, Any]

    # ─────────────────────────────  Endpoints  ───────────────────────────────

    @app.post("/infer", response_model=InferResponse)
    def infer_route(req: InferRequest):
        """
        Run Symbolica inference on the supplied fact dictionary.

        If *rulepack* path is provided, it is loaded (and hot-swapped) before
        evaluation.
        """
        if req.rulepack is not None:
            try:
                load_pack(str(req.rulepack))
            except FileNotFoundError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc

        try:
            verdict, trace = infer(
                facts=req.facts,
                agent=req.agent,
                trace_level=req.trace_level,
            )
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return JSONResponse(content={"verdict": verdict, "trace": trace})

    @app.get("/health")
    def health() -> Dict[str, str]:
        """Simple liveness/readiness probe."""
        try:
            get_pack()
            return {"status": "ok"}
        except RuntimeError:
            return {"status": "no_rulepack"}

except ImportError:
    # FastAPI not installed – the CLI will detect and warn.
    app = None
