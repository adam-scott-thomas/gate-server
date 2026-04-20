"""Guard middleware for gate-server — STUB.

Seeded by Creator 4. Wraps gate-server's tool execution endpoints
with gate-guard enforcement. Rejects API calls for suppressed tools.

Pattern:
    from gate_guard.enforcer import GuardedGate

    guard = GuardedGate(gate, mode="strict")

    @app.post("/v1/execute")
    async def execute_tool(body: ExecuteRequest):
        try:
            result = guard.execute(body.tool_name, mode=body.mode, **body.params)
            return {"status": "executed", "result": result.return_value}
        except ExecutionDenied as e:
            raise HTTPException(403, detail=str(e))
"""
