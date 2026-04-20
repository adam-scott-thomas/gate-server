"""Run gate-server directly: python -m gate_server"""

import uvicorn

uvicorn.run("gate_server.app:app", host="0.0.0.0", port=8900, reload=True)
