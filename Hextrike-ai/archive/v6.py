import requests
import sys
import time
import re

# ---------------- Configuration ----------------

OLLAMA_URL = "http://localhost:11434"
Hexstrike = "http://192.168.56.101:8888"
TIMEOUT = 10

MAX_CYCLES = 6            # Total PLAN→EXECUTE→ANALYZE loops
SLEEP_BETWEEN_STEPS = 1.5

# ---------------- Hexstrike Discovery ----------------

def discover_hexstrike_tools():
    r = requests.get(f"{Hexstrike}/health", timeout=TIMEOUT)
    r.raise_for_status()
    health = r.json()

    tools_status = health.get("tools_status", {})
    category_stats = health.get("category_stats", {})

    available_tools = sorted(
        tool for tool, ok in tools_status.items() if ok
    )

    return available_tools, category_stats


def execute_hexstrike(cmd):
    print(f"\n⚙️ EXECUTING TOOL:\n{cmd}\n")
    r = requests.post(
        f"{Hexstrike}/api/command",
        json={"command": cmd},
        timeout=300
    )
    if r.status_code == 200:
        return r.json().get("output", "")
    return f"Execution error: HTTP {r.status_code}"


# ---------------- Ollama Helpers ----------------

HEX_CMD = re.compile(r"^!hex\s+(.+)$", re.IGNORECASE)

def ollama_generate(model, system, prompt):
    payload = {
        "model": model,
        "system": system,
        "prompt": prompt,
        "stream": False
    }
    r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload)
    r.raise_for_status()
    return r.json()["response"].strip()


def build_system_prompt(available_tools):
    return f"""
You are an autonomous cybersecurity agent.

You operate in THREE PHASES:
1. PLAN     – Decide the next action. NO TOOLS.
2. EXECUTE  – If needed, run EXACTLY ONE tool.
3. ANALYZE  – Interpret the result and decide next steps.

RULES:
- Tools may ONLY be used in EXECUTE phase.
- Tool execution format:
  !hex <tool> <arguments>
- Use ONLY tools from the available list.
- NEVER run more than one tool per EXECUTE step.
- If the objective is complete, clearly say: DONE

Available tools:
{", ".join(available_tools)}
"""


# ---------------- Agent Loop ----------------

def agent_loop(model, system_prompt, available_tools):
    print(f"\n🤖 Autonomous PLAN→EXECUTE→ANALYZE agent running ({model})")
    print("Type 'exit' to stop.\n")

    objective = input("🎯 Objective: ").strip()
    if not objective:
        print("No objective provided.")
        return

    context = f"Objective: {objective}\n"
    cycles = 0

    while cycles < MAX_CYCLES:
        cycles += 1
        print(f"\n===== CYCLE {cycles} =====\n")

        # -------- PLAN --------
        plan_prompt = context + "\n[PHASE: PLAN]\nWhat is the next step?"
        plan = ollama_generate(model, system_prompt, plan_prompt)

        print("🧠 PLAN:\n", plan, "\n")
        if "DONE" in plan.upper():
            print("✅ Objective complete.")
            return

        # -------- EXECUTE --------
        exec_prompt = (
            context +
            f"\nPLAN:\n{plan}\n\n"
            "[PHASE: EXECUTE]\n"
            "If a tool is needed, output the command.\n"
            "Otherwise say: NO TOOL"
        )

        execute = ollama_generate(model, system_prompt, exec_prompt)
        print("⚙️ EXECUTE:\n", execute, "\n")

        tool_output = "NO TOOL EXECUTED"

        match = HEX_CMD.match(execute)
        if match:
            cmd = match.group(1)
            tool_name = cmd.split()[0]

            if tool_name not in available_tools:
                print(f"[!] Tool '{tool_name}' not allowed.")
                return

            tool_output = execute_hexstrike(cmd)

        # -------- ANALYZE --------
        analyze_prompt = (
            context +
            f"\nPLAN:\n{plan}\n\n"
            f"EXECUTE:\n{execute}\n\n"
            f"TOOL OUTPUT:\n{tool_output}\n\n"
            "[PHASE: ANALYZE]\n"
            "Analyze results and decide next step."
        )

        analysis = ollama_generate(model, system_prompt, analyze_prompt)
        print("📊 ANALYSIS:\n", analysis, "\n")

        context += (
            f"\nPLAN:\n{plan}\n"
            f"EXECUTE:\n{execute}\n"
            f"OUTPUT:\n{tool_output}\n"
            f"ANALYSIS:\n{analysis}\n"
        )

        if "DONE" in analysis.upper():
            print("✅ Objective complete.")
            return

        time.sleep(SLEEP_BETWEEN_STEPS)

    print("⚠️ Max cycles reached — stopping agent.")


# ---------------- Main ----------------

def main():
    available_tools, _ = discover_hexstrike_tools()
    if not available_tools:
        print("No tools available.")
        sys.exit(1)

    models = requests.get(f"{OLLAMA_URL}/api/tags").json()["models"]
    print("\nAvailable models:")
    for i, m in enumerate(models, 1):
        print(f"{i}. {m['name']}")

    model = models[int(input("\nSelect model: ")) - 1]["name"]

    system_prompt = build_system_prompt(available_tools)
    agent_loop(model, system_prompt, available_tools)


if __name__ == "__main__":
    main()

