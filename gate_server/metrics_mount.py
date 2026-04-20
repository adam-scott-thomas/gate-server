"""Mount gate-metrics into gate-server — STUB.

Seeded by Creator 4. Improvers: import and mount in app.py.

Pattern:
    from gate_metrics.server import app as metrics_app
    from gate_metrics.collector import GateCollector
    from gate_metrics.server import set_collector

    collector = GateCollector()
    set_collector(collector)

    # In filter endpoint, wrap with:
    #   result = collector.observe_filter(gate, mode)

    # Mount metrics sub-app:
    #   app.mount("/metrics-app", metrics_app)
    # Or just add the /metrics route directly
"""
