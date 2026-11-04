"""
Launcher for Trading Machine Cockpit v2.
Usage:
    python cockpit_dashboard_v2.py
or:
    python cockpit_dashboard_v2.py --live

The repo's .env is loaded HERE — inside the guard, and BEFORE the app import: several dashboard
callbacks read the Alpaca keys at module level, so the load must precede them (2026-11-04).
Importing this file loads nothing. Locked by tests/test_dashboard_entry_env_2026_11_04.py.
"""

if __name__ == "__main__":
    import argparse
    from core.env import load_local_env
    load_local_env()
    from cockpit.dashboard_v2.app import run_dashboard

    p = argparse.ArgumentParser()
    p.add_argument("--live", action="store_true", help="Enable auto-refresh updates (Paper Mode).")
    p.add_argument("--port", type=int, default=8050, help="Port number (default 8050).")
    args = p.parse_args()
    run_dashboard(live=args.live, port=args.port)
