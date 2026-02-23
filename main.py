#!/usr/bin/env python3
import os
import re
import subprocess
import traceback
from typing import Dict, List, Set

from dotenv import load_dotenv
from routeros_api import RouterOsApiPool

# Local development convenience: if .env is absent, load_dotenv is a no-op.
load_dotenv(dotenv_path=os.getenv("DOTENV_PATH", ".env"), override=False)


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


MT_HOST = os.getenv("MT_HOST")
MT_USER = os.getenv("MT_USER")
MT_PASS = os.getenv("MT_PASS")
MT_USE_SSL = env_bool("MT_USE_SSL", True)
MT_SSL_VERIFY = env_bool("MT_SSL_VERIFY", False)
MT_PORT = int(os.getenv("MT_PORT", "8729" if MT_USE_SSL else "8728"))

WG_GATEWAY = os.getenv("MT_WG_GW", "wg0")          # interface name or next-hop IP
DRY_RUN = os.getenv("MT_DRY_RUN", "false").strip().lower() in {"1", "true", "yes", "on"}
COMMENT_PREFIX = "openai:"                         # managed routes marker
DEFAULT_DOMAINS = [
    "api.openai.com",
    "chat.openai.com",
    "auth.openai.com",
    "platform.openai.com",
    "chatgpt.com",
    "ios.chat.openai.com",
]

IPV4_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")


def env_domains() -> List[str]:
    value = os.getenv("MT_DOMAINS", "")
    if not value.strip():
        return DEFAULT_DOMAINS
    domains = [item.strip() for item in value.split(",")]
    return [item for item in domains if item]


DOMAINS = env_domains()


def dig_a(domain: str) -> List[str]:
    print(f"[dns] resolve A for {domain}")
    out = subprocess.check_output(["dig", "+short", "A", domain], text=True, timeout=10)
    ips = []
    for line in out.splitlines():
        line = line.strip()
        if IPV4_RE.match(line):
            ips.append(line)
    uniq_ips = sorted(set(ips))
    print(f"[dns] {domain} -> {', '.join(uniq_ips) if uniq_ips else 'no A records'}")
    return uniq_ips


def desired() -> Dict[str, str]:
    # dst-address -> comment
    want: Dict[str, str] = {}
    for d in DOMAINS:
        for ip in dig_a(d):
            want[f"{ip}/32"] = f"{COMMENT_PREFIX}{d}"
    return want


def main():
    missing = [name for name, val in {"MT_HOST": MT_HOST, "MT_USER": MT_USER, "MT_PASS": MT_PASS}.items() if not val]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    print(
        "[startup] "
        f"mt_target={MT_HOST}:{MT_PORT} "
        f"mt_user={MT_USER} "
        f"wg_gateway={WG_GATEWAY} "
        f"dry_run={DRY_RUN} "
        f"use_ssl={MT_USE_SSL} "
        f"ssl_verify={MT_SSL_VERIFY}"
    )
    print(f"[startup] domains={', '.join(DOMAINS)}")
    want = desired()
    want_dst: Set[str] = set(want.keys())
    print(f"[plan] desired routes discovered: {len(want_dst)}")

    print(f"[routeros] connecting to {MT_HOST}:{MT_PORT} (ssl={MT_USE_SSL}, verify={MT_SSL_VERIFY})")
    try:
        pool = RouterOsApiPool(
            MT_HOST,
            username=MT_USER,
            password=MT_PASS,
            port=MT_PORT,
            use_ssl=MT_USE_SSL,
            ssl_verify=MT_SSL_VERIFY,
            plaintext_login=True,  # RouterOS >= 6.43 login method (works for v7 too)
        )
        api = pool.get_api()
        print("[routeros] connected")
    except Exception as exc:
        print(f"[routeros] connect failed to {MT_HOST}:{MT_PORT}: {exc}")
        print(traceback.format_exc())
        raise

    try:
        routes = api.get_resource("/ip/route")
        print("[routeros] fetching managed routes")

        # Read all routes and split managed/non-managed locally.
        all_routes = routes.get()
        existing = [r for r in all_routes if str(r.get("comment", "")).startswith(COMMENT_PREFIX)]
        print(f"[routeros] all_routes={len(all_routes)} managed_routes={len(existing)}")

        any_by_dst: Dict[str, List[dict]] = {}
        for r in all_routes:
            dst = r.get("dst-address")
            if dst:
                any_by_dst.setdefault(dst, []).append(r)

        exist_by_dst: Dict[str, List[dict]] = {}
        for r in existing:
            dst = r.get("dst-address")
            if dst:
                exist_by_dst.setdefault(dst, []).append(r)

        # 1) ADD missing first (no hole). Skip if dst exists at all (managed or manual).
        to_add = [dst for dst in sorted(want_dst) if dst not in any_by_dst]
        if not DRY_RUN:
            for dst in to_add:
                routes.add(
                    **{
                        "dst-address": dst,
                        "gateway": WG_GATEWAY,
                        "comment": want[dst],
                        "disabled": "no",
                    }
                )

        # Re-fetch routes after adds unless dry-run
        current_all = all_routes if DRY_RUN else routes.get()
        current = [r for r in current_all if str(r.get("comment", "")).startswith(COMMENT_PREFIX)]
        current_by_dst: Dict[str, List[dict]] = {}
        for r in current:
            dst = r.get("dst-address")
            if dst:
                current_by_dst.setdefault(dst, []).append(r)

        # 2) DELETE obsolete + duplicates
        to_delete_ids: List[str] = []
        for dst, items in current_by_dst.items():
            if dst not in want_dst:
                for it in items:
                    to_delete_ids.append(it["id"])
            else:
                # delete duplicates (keep first)
                if len(items) > 1:
                    for it in items[1:]:
                        to_delete_ids.append(it["id"])

        if not DRY_RUN:
            for rid in to_delete_ids:
                routes.remove(id=rid)

        mode = "DRY-RUN" if DRY_RUN else "APPLY"
        print(f"{mode} desired={len(want_dst)} add={len(to_add)} delete={len(to_delete_ids)}")
        if to_add:
            print("plan_add:", ", ".join(to_add))
        if to_delete_ids:
            print("plan_delete_ids:", ", ".join(to_delete_ids))

    finally:
        try:
            pool.disconnect()
            print("[routeros] disconnected")
        except Exception:
            pass


if __name__ == "__main__":
    main()
