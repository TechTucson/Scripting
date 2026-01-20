import requests
import sys
from collections import defaultdict

OLLAMA_URL = "http://localhost:11434"
Hexstrike = "http://192.168.56.101:8888"  # <-- CHANGE IF NEEDED
TIMEOUT = 10


# ---------------- Hexstrike Tool Discovery ----------------

def get_hexstrike_health():
    r = requests.get(f"{Hexstrike}/health", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def get_available_tools_grouped():
    """
    Returns:
      - available_tools: set of tool names
      - grouped_tools: { category: [tools] }
    """
    health = get_hexstrike_health()

    tools_status = health.get("tools_status", {})
    category_stats = health.get("category_stats", {})

    available_tools = {
        tool for tool, available in tools_status.items() if available
    }

    # NOTE:
    # The health endpoint does not map tools -> categories explicitly.
    # We infer grouping using known tool sets per category if available.
    # For now, we present categories with counts + flat tool list under 'available'.
    grouped_tools = defaultdict(list)

    # Fallback: single "Available Tools" group
    for tool in sorted(available_tools):
        grouped_tools["available"].append(tool)

    return available_tools, grouped_tools, category_stats


def display_tools(grouped_tools, category_stats):
    print("\n================ Hexstrike Available Tools ================\n")

    for category, tools in category_stats.items():
        available = tools.get("available", 0)
        total = tools.get("total", 0)
        print(f"[{category.upper()}]  ({available}/{total} available)")

    print("\n[AVAILABLE TOOLS]\n")
    for tool in grouped_tools["available"]:
        print(f"- {tool}")

    print("\n===========================================================\n")


# ---------------- Hexstrike Command Execution ----------------

def execute_Hexstrike_command(cmd, description=""):
    print(f"[+] {description}")
    print(f"    Command: {cmd}")

    try:
        response = requests.post(
            f"{Hexstrike}/api/command",
            json={"command": cmd},
            timeout=300
        )

        if response.status_code == 200:
            result = response.json()
            output = result.get("output", "No output")
            return True, output
        else:
            return False, f"HTTP Error {response.status_code}"
    except Exception as e:
        return False, f"Error: {e}"


# ---------------- Ollama ----------------

def get_models():
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags")
        response.raise_for_status()
        return response.json().get("models", [])
    except requests.RequestException as e:
        print(f"Error connecting to Ollama: {e}")
        sys.exit(1)


def select_model(models):
    print("\nAvailable Ollama models:\n")
    for i, model in enumerate(models, start=1):
        print(f"{i}. {model['name']}")

    while True:
        try:
            choice = int(input("\nSelect a model number: "))
            if 1 <= choice <= len(models):
                return models[choice - 1]["name"]
        except ValueError:
            pass
        print("Invalid selection.")


# ---------------- Chat Loop ----------------

def chat(model, available_tools, grouped_tools, category_stats):
    print(f"\nChatting with model: {model}")
    print("Type 'exit' to quit.")
    print("Commands:")
    print("  !hex <command>   Run Hexstrike command")
    print("  !tools           Show available tools\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            break

        if user_input == "!tools":
            display_tools(grouped_tools, category_stats)
            continue

        if user_input.startswith("!hex"):
            cmd = user_input[4:].strip()
            if not cmd:
                print("Usage: !hex <command>\n")
                continue

            tool_name = cmd.split()[0]

            if tool_name not in available_tools:
                print(f"[!] Tool '{tool_name}' is NOT available in Hexstrike\n")
                continue

            success, output = execute_Hexstrike_command(
                cmd,
                description="Executing Hexstrike command"
            )

            print("\n[Hexstrike Output]")
            print(output)
            print()
            continue

        payload = {
            "model": model,
            "prompt": user_input,
            "stream": False
        }

        try:
            response = requests.post(
                f"{OLLAMA_URL}/api/generate",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            print(f"\n{model}: {data.get('response', '').strip()}\n")
        except requests.RequestException as e:
            print(f"Error during generation: {e}")
            break


# ---------------- Main ----------------

def main():
    print("[*] Discovering Hexstrike tools...")

    available_tools, grouped_tools, category_stats = get_available_tools_grouped()

    if not available_tools:
        print("[!] No Hexstrike tools available — execution disabled\n")
    else:
        print(f"[✓] {len(available_tools)} Hexstrike tools discovered")

    display_tools(grouped_tools, category_stats)

    models = get_models()
    model = select_model(models)
    chat(model, available_tools, grouped_tools, category_stats)


if __name__ == "__main__":
    main()
