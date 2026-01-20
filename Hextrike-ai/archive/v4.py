import requests
import sys
from collections import defaultdict

# ---------------- Configuration ----------------

OLLAMA_URL = "http://localhost:11434"
Hexstrike = "http://192.168.56.101:8888"  # CHANGE IF NEEDED
TIMEOUT = 10

# ---------------- Hexstrike Discovery ----------------

def get_hexstrike_health():
    r = requests.get(f"{Hexstrike}/health", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def discover_hexstrike_tools():
    health = get_hexstrike_health()

    tools_status = health.get("tools_status", {})
    category_stats = health.get("category_stats", {})

    available_tools = sorted(
        tool for tool, available in tools_status.items() if available
    )

    return available_tools, category_stats


def display_tools(available_tools, category_stats):
    print("\n================ Hexstrike Status ================\n")

    print("Category availability:")
    for category, stats in category_stats.items():
        print(f"- {category}: {stats['available']}/{stats['total']}")

    print("\nAvailable tools:\n")
    for tool in available_tools:
        print(f"- {tool}")

    print("\n=================================================\n")


# ---------------- Hexstrike Execution ----------------

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
            return True, result.get("output", "No output")
        else:
            return False, f"HTTP Error {response.status_code}"
    except Exception as e:
        return False, f"Error: {e}"


# ---------------- Ollama ----------------

def get_models():
    r = requests.get(f"{OLLAMA_URL}/api/tags")
    r.raise_for_status()
    return r.json().get("models", [])


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


def build_system_prompt(available_tools):
    return f"""
You are a cybersecurity assistant with access to external tools via Hexstrike.

Rules:
- You do NOT execute tools yourself.
- When a tool is required, respond ONLY with a command in this format:
  !hex <tool> <arguments>
- Use ONLY tools from the available tools list.
- Do NOT hallucinate tools.
- If no tool is needed, answer normally.

Available tools:
{", ".join(available_tools)}
"""


# ---------------- Chat Loop ----------------

def chat(model, system_prompt, available_tools, category_stats):
    print(f"\nChatting with model: {model}")
    print("Type 'exit' to quit.")
    print("Commands:")
    print("  !hex <command>   Execute Hexstrike command")
    print("  !tools           Show available tools\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            break

        if user_input == "!tools":
            display_tools(available_tools, category_stats)
            continue

        if user_input.startswith("!hex"):
            cmd = user_input[4:].strip()
            if not cmd:
                print("Usage: !hex <command>\n")
                continue

            tool_name = cmd.split()[0]
            if tool_name not in available_tools:
                print(f"[!] Tool '{tool_name}' is not available\n")
                continue

            confirm = input("Execute this command? [y/N]: ")
            if confirm.lower() != "y":
                print("Cancelled.\n")
                continue

            success, output = execute_Hexstrike_command(
                cmd, "Executing Hexstrike command"
            )

            print("\n[Hexstrike Output]\n")
            print(output)
            print()
            continue

        payload = {
            "model": model,
            "prompt": user_input,
            "system": system_prompt,
            "stream": False
        }

        try:
            r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload)
            r.raise_for_status()
            data = r.json()
            print(f"\n{model}: {data.get('response', '').strip()}\n")
        except Exception as e:
            print(f"Error talking to Ollama: {e}")
            break


# ---------------- Main ----------------

def main():
    print("[*] Discovering Hexstrike tools...")
    available_tools, category_stats = discover_hexstrike_tools()

    if not available_tools:
        print("[!] No tools available — exiting")
        sys.exit(1)

    print(f"[✓] {len(available_tools)} tools available")
    display_tools(available_tools, category_stats)

    models = get_models()
    model = select_model(models)

    system_prompt = build_system_prompt(available_tools)
    chat(model, system_prompt, available_tools, category_stats)


if __name__ == "__main__":
    main()
