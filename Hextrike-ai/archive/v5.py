import requests
import sys
import re
import time

# ---------------- Configuration ----------------

OLLAMA_URL = "http://localhost:11434"
Hexstrike = "http://192.168.56.101:8888"  # CHANGE IF NEEDED
TIMEOUT = 10

AUTO_EXECUTE = True        # <- Agent runs tools automatically
MAX_TOOL_RUNS = 5          # <- Prevent infinite loops
SLEEP_BETWEEN_RUNS = 1.5   # <- Rate limit agent actions

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
    for cat, stats in category_stats.items():
        print(f"- {cat}: {stats['available']}/{stats['total']}")
    print("\nAvailable tools:\n")
    for tool in available_tools:
        print(f"- {tool}")
    print("\n=================================================\n")


# ---------------- Hexstrike Execution ----------------

def execute_Hexstrike_command(cmd):
    print(f"\n[⚙️  Hexstrike EXECUTING]")
    print(f"Command: {cmd}\n")

    try:
        r = requests.post(
            f"{Hexstrike}/api/command",
            json={"command": cmd},
            timeout=300
        )

        if r.status_code == 200:
            return r.json().get("output", "No output")
        return f"HTTP Error {r.status_code}"
    except Exception as e:
        return f"Execution error: {e}"


# ---------------- Ollama ----------------

def get_models():
    r = requests.get(f"{OLLAMA_URL}/api/tags")
    r.raise_for_status()
    return r.json().get("models", [])


def select_model(models):
    print("\nAvailable Ollama models:\n")
    for i, m in enumerate(models, start=1):
        print(f"{i}. {m['name']}")
    while True:
        try:
            choice = int(input("\nSelect model: "))
            return models[choice - 1]["name"]
        except Exception:
            print("Invalid selection")


def build_system_prompt(available_tools):
    return f"""
You are an autonomous cybersecurity agent with access to execution tools.

RULES (STRICT):
- You may run tools when appropriate.
- When you decide to run a tool, output ONLY:
  !hex <tool> <arguments>
- Use ONLY tools from the available tools list.
- Never invent tools.
- Never explain the command before running it.
- After execution, analyze the output and decide next steps.
- Stop when the objective is complete.

Available tools:
{", ".join(available_tools)}
"""


HEX_PATTERN = re.compile(r"^!hex\s+(.+)$", re.IGNORECASE)


# ---------------- Autonomous Agent Loop ----------------

def chat(model, system_prompt, available_tools):
    print(f"\n🤖 Autonomous agent running with model: {model}")
    print("Type 'exit' to stop the agent.\n")

    tool_runs = 0
    conversation = []

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break

        conversation.append(f"User: {user_input}")

        while True:
            payload = {
                "model": model,
                "prompt": "\n".join(conversation),
                "system": system_prompt,
                "stream": False
            }

            r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload)
            r.raise_for_status()
            response = r.json()["response"].strip()

            print(f"\n{model}: {response}\n")
            conversation.append(f"Assistant: {response}")

            match = HEX_PATTERN.match(response)
            if not match:
                break

            if not AUTO_EXECUTE:
                print("[!] AUTO_EXECUTE disabled\n")
                break

            if tool_runs >= MAX_TOOL_RUNS:
                print("[!] Tool execution limit reached\n")
                break

            cmd = match.group(1)
            tool_name = cmd.split()[0]

            if tool_name not in available_tools:
                print(f"[!] Tool '{tool_name}' not available\n")
                break

            output = execute_Hexstrike_command(cmd)
            tool_runs += 1

            conversation.append(f"Tool output:\n{output}")
            time.sleep(SLEEP_BETWEEN_RUNS)


# ---------------- Main ----------------

def main():
    print("[*] Discovering Hexstrike tools...")
    available_tools, category_stats = discover_hexstrike_tools()

    if not available_tools:
        print("[!] No tools available — exiting")
        sys.exit(1)

    display_tools(available_tools, category_stats)

    models = get_models()
    model = select_model(models)

    system_prompt = build_system_prompt(available_tools)
    chat(model, system_prompt, available_tools)


if __name__ == "__main__":
    main()
