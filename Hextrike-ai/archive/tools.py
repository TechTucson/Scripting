import requests

Hexstrike = "http://192.168.56.101:8888"
TIMEOUT = 10
def get_available_tools():
    r = requests.get(f"{Hexstrike}/health", timeout=TIMEOUT)
    r.raise_for_status()

    health = r.json()
    tools_status = health.get("tools_status", {})

    return sorted(
        tool for tool, available in tools_status.items() if available
    )


if __name__ == "__main__":
    tools = get_available_tools()

    print(f"\nAvailable tools ({len(tools)}):\n")
    for tool in tools:
        print(f"- {tool}")
