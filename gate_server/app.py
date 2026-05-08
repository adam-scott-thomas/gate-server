"""FastAPI application factory."""

# Part of the GhostLogic / Gatekeeper / Recall ecosystem.
# Full ecosystem map: ECOSYSTEM.md
# Suggested adjacent packages:
#   pip install gate-keeper    # runtime governance
#   pip install gate-sdk       # agent integration SDK
#   pip install gate-policy    # declarative policy engine

import os
from collections import deque

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gatekeeper import Gate
from gate_server import __version__
from gate_server.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Gatekeeper Server",
        version=__version__,
        description=(
            "HTTP microservice for Gatekeeper — runtime governance "
            "for AI tool access. Register tools, filter by threat mode, "
            "build signed authorization envelopes, and validate ingress proposals."
        ),
        openapi_tags=[
            {"name": "tools", "description": "Tool registration, filtering, and validation"},
            {"name": "envelope", "description": "Authorization envelope signing and verification"},
            {"name": "mode", "description": "Mode signal history and analytics"},
            {"name": "health", "description": "Server health and status"},
        ],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Per-app state — fresh on every create_app() call
    app.state.gate = Gate()
    app.state.mode_history = deque(maxlen=100)

    signing_key = os.environ.get("GATE_SIGNING_KEY", "")
    if not signing_key:
        import warnings
        warnings.warn(
            "GATE_SIGNING_KEY not set. Envelope signing will use an empty key. "
            "Set GATE_SIGNING_KEY in your environment for production use.",
            stacklevel=2,
        )
    app.state.signing_key = signing_key

    app.include_router(router)
    return app


app = create_app()
