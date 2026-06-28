#!/usr/bin/env python3
"""Standalone proxy refresh script — can be run via cron or directly.

Usage:
    python3 -m src.proxy.refresh              # refresh if stale
    python3 -m src.proxy.refresh --force       # force refresh
    python3 -m src.proxy.refresh --status      # show pool status
    python3 -m src.proxy.refresh --cron        # cron mode (quiet, exit codes)

Cron example (every 30 minutes):
    */30 * * * * cd /root/projects/open-work && python3 -m src.proxy.refresh --cron >> /var/log/open-work-proxy.log 2>&1
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("proxy.refresh")


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh proxy pool")
    parser.add_argument("--force", action="store_true", help="Force refresh even if pool is fresh")
    parser.add_argument("--status", action="store_true", help="Show pool status and exit")
    parser.add_argument("--cron", action="store_true", help="Cron mode: quiet, use exit codes")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.cron:
        logging.getLogger().setLevel(logging.WARNING)

    from src.proxy.manager import ProxyManager

    manager = ProxyManager(auto_refresh=False)

    if args.status:
        stats = manager.get_stats()
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"Proxy Pool Status:")
            print(f"  Total proxies:  {stats['total']}")
            print(f"  Healthy:        {stats['healthy']}")
            print(f"  Failed:         {stats['failed']}")
            print(f"  Avg latency:    {stats['avg_latency']:.0f}ms")
            if stats['last_refresh']:
                age = int(time.time() - stats['last_refresh'])
                print(f"  Last refresh:   {age}s ago")
            else:
                print(f"  Last refresh:   never")
        return 0

    # Refresh
    try:
        count = manager.refresh(force=args.force)
        if args.json:
            print(json.dumps({"working_proxies": count, "status": "ok"}))
        elif not args.cron:
            print(f"\nRefreshed: {count} working proxies")

        return 0 if count > 0 else 1
    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e), "status": "failed"}))
        elif not args.cron:
            print(f"Refresh failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
