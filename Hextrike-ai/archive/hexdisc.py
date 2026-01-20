import requests
import json
from pprint import pprint

Hexstrike = "http://192.168.56.101:8888"  # CHANGE IF NEEDED
TIMEOUT = 10


def try_get(endpoint):
    """Helper for GET requests"""
    try:
        r = requests.get(f"{Hexstrike}{endpoint}", timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json(), endpoint
    except Exception:
        pass
    return None, None


def try_options(endpoint):
    """OPTIONS probe"""
    try:
        r = requests.options(f"{Hexstrike}{endpoint}", timeout=TIMEOUT)
        return dict(r.headers)
    except Exception:
        return None


def try_command(cmd):
    """Attempt a non-invasive command like help"""
    try:
        r = requests.post(
            f"{Hexstrike}/api/command",
            json={"command": cmd},
            timeout=TIMEOUT
        )
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def discover_tools():
    print("\n[+] Hexstrike Tool Discovery\n")

    # 1️⃣ Known discovery endpoints
    discovery_endpoints = [
        "/api/tools",
        "/api/commands",
        "/api/capabilities",
        "/api/help"
    ]

    for ep in discovery_endpoints:
        data, found = try_get(ep)
        if data:
            print(f"[✓] Found tool listing at {found}")
            pprint(data)
            return

    print("[!] No dedicated tool endpoint found\n")

    # 2️⃣ OpenAPI / Swagger discovery
    openapi_endpoints = [
        "/openapi.json",
        "/swagger.json",
        "/v3/api-docs"
    ]

    for ep in openapi_endpoints:
        data, found = try_get(ep)
        if data:
            print(f"[✓] OpenAPI spec found at {found}")
            print("\nAvailable paths:\n")
            for path in data.get("paths", {}):
                print(f" - {path}")
            return

    print("[!] No OpenAPI spec found\n")

    # 3️⃣ OPTIONS probe
    print("[*] Probing OPTIONS /api/command")
    headers = try_options("/api/command")
    if headers:
        pprint(headers)
    else:
        print("No OPTIONS data returned")

    # 4️⃣ Help-style introspection commands
    print("\n[*] Trying help-style commands\n")

    for cmd in ["help", "?", "tools", "list", "commands"]:
        print(f"[>] Trying command: {cmd}")
        result = try_command(cmd)
        if result:
            print("[✓] Response:")
            pprint(result)
            return

    print("\n[✗] No tool discovery possible via API")
    print("    Hexstrike likely expects opaque commands or manual documentation.")


if __name__ == "__main__":
    discover_tools()
