"""Proxy pool status routes."""

from __future__ import annotations

from fastapi import APIRouter

from api.schemas import ProxyPoolStatus
from src.config import CONFIG_DIR

router = APIRouter()


@router.get("/proxy/pool", response_model=ProxyPoolStatus)
def get_proxy_pool_status():
    config_path = CONFIG_DIR / "config.toml"
    proxies = []
    if config_path.exists():
        try:
            import toml
            cfg = toml.load(config_path)
            proxies = cfg.get("proxy", {}).get("proxy_list", [])
        except Exception:
            pass

    return ProxyPoolStatus(
        total=len(proxies),
        working=len(proxies),
        failed=0,
        last_refresh=None,
    )


@router.post("/proxy/refresh")
def refresh_proxies():
    import subprocess
    try:
        result = subprocess.run(
            ["python3", "-m", "src.proxy.refresh", "--check-working"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {"ok": True, "output": result.stdout[:500]}
    except Exception as e:
        return {"ok": False, "error": str(e)}
