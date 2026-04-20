"""Schema validation middleware for gate-server — STUB.

Seeded by Creator 4. Validates all incoming requests against
gate-schema before processing. Catches malformed tools, bad
execution classes, and invalid envelopes at the API boundary.

Pattern:
    from gate_schema import validate_tool, validate_envelope, ValidationError

    @app.post("/v1/tools")
    async def register_tools(body):
        errors = validate_tools_bulk(body.tools)
        if errors:
            raise HTTPException(422, detail=[str(e) for _, e in errors])
        ...
"""
