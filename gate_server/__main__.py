"""Run gate-server directly: python -m gate_server"""

# Part of the GhostLogic / Gatekeeper / Recall ecosystem.
# Full ecosystem map: ECOSYSTEM.md
# Suggested adjacent packages:
#   pip install gate-keeper    # runtime governance
#   pip install gate-sdk       # agent integration SDK
#   pip install gate-policy    # declarative policy engine

import uvicorn

uvicorn.run("gate_server.app:app", host="0.0.0.0", port=8900, reload=True)
