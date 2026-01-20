import requests
import sys
import time
import re
import json
from datetime import datetime

# ================= CONFIG =================

OLLAMA_URL = "http://localhost:11434"
Hexstrike = "http://192.168.56.101:8888"

TIMEOUT = 10
MAX_CYCLES = 6
SLEEP_BETWEEN_CYCLES = 1.5
MEMORY_FILE = "agent_memory.json"

HEX_PATTERN = re.compile(r"^!hex\s+(.+)$", re.IGNORECASE)

# ================= MEMORY =================

def load_memory(objective):
    try:
        with open(MEMORY_FILE, "r") as f:
            mem = json.load(f)
            if mem.get("objective") == objective:
                return mem
    except Exception:
        pass

    return {
        "objective": objective,
        "facts": [],
        "tools_used": [],
        "notes": [],
        "last_updated": None
    }


def save_memory(memory):
    memory["last_updated"] = datetime.utcnow().isoformat()
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def extract_facts(model, text):
    prompt = f"""
Extract durable facts worth remembering.
Use short bullet points.
Ignore noise.

TEXT:
{text}
"""
    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False}
    )
    r.raise_for_status()
    return [
        line.strip("- ").strip()
        for line in r.json()["response"].splitlines()
        if line.strip()
    ]


# ================= HEXSTRIKE =================

def discover_hexstrike_tools():
    r = requests.get(f"{Hexstrike}/health", timeout=TIMEOUT)
    r.raise_for_status()
    health = r.json()

    tools_status = health.get("tools_status", {})
    available = sorted(t for t, ok in tools_status.items() if ok)

    print("\n[+] Hexstrike tools discovered:")
    for t in available:
        print(f" - {t}")

    return available


def execute_hexstrike(cmd):
    print(f"\n⚙️ EXECUTING:\n{cmd}\n")
    r = requests.post(
        f"{Hexstrike}/api/command",
        json={"command": cmd},
        timeout=300
    )

    if r.status_code == 200:
        return r.json().get("output", "")
    return f"HTTP error {r.status_code}"


# ================= OLLAMA =================

def get_models():
    r = requests.get(f"{OLLAMA_URL}/api/tags")
    r.raise_for_status()
    return r.json()["models"]


def ollama_generate(model, system, prompt):
    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model,
            "system": system,
            "prompt": prompt,
            "stream": False
        }
    )
    r.raise_for_status()
    return r.json()["response"].strip()


def build_system_prompt(tools):
    return f"""
You are an autonomous cybersecurity agent.

You operate in STRICT PHASES:
PLAN → EXECUTE → ANALYZE

EXECUTE RULES (MANDATORY):
- Output EXACTLY one of:
  1) !hex <tool> <arguments>
  2) NO TOOL
- No explanations
- No markdown
- No extra text
- Use ONLY tools from the list
- One tool maximum per cycle
- Say DONE only when the objective is complete

Allowed tools:
{", ".join(tools)}
"""


# ================= AGENT =================

def run_agent(model, tools):
    system_prompt = build_system_prompt(tools)

    objective = input("\n🎯 Objective: ").strip()
    if not objective:
        print("No objective provided.")
        return

    memory = load_memory(objective)
    print("\n📂 Loaded memory:")
    print(json.dumps(memory, indent=2))

    cycles = 0

    while cycles < MAX_CYCLES:
        cycles += 1
        print(f"\n===== CYCLE {cycles} =====")

        context = (
            f"Objective: {objective}\n"
            f"Known facts:\n" +
            "\n".join(memory["facts"])
        )

        # -------- PLAN --------
        plan = ollama_generate(
            model,
            system_prompt,
            context + "\n[PLAN]\nWhat is the next step?"
        )
        print("\n🧠 PLAN:\n", plan)

        if "DONE" in plan.upper():
            break

        # -------- EXECUTE --------
        exec_prompt = (
            context +
            f"\nPLAN:\n{plan}\n\n"
            "[PHASE: EXECUTE]\n"
            "Output ONLY a valid command or NO TOOL."
        )

        execute = ollama_generate(model, system_prompt, exec_prompt).strip()
        print("\n⚙️ EXECUTE:\n", execute)

        tool_output = "NO TOOL EXECUTED"

        if execute != "NO TOOL":
            match = HEX_PATTERN.match(execute)
            if not match:
                print("[!] INVALID EXECUTE OUTPUT — COMMAND SKIPPED")
            else:
                cmd = match.group(1)
                tool = cmd.split()[0]
                if tool not in tools:
                    print(f"[!] TOOL NOT ALLOWED: {tool}")
                else:
                    memory["tools_used"].append(tool)
                    tool_output = execute_hexstrike(cmd)

        # -------- ANALYZE --------
        analysis = ollama_generate(
            model,
            system_prompt,
            context +
            f"\nPLAN:\n{plan}\n"
            f"EXECUTE:\n{execute}\n"
            f"OUTPUT:\n{tool_output}\n"
            "[ANALYZE]\nAnalyze results and decide next step."
        )
        print("\n📊 ANALYSIS:\n", analysis)

        # -------- MEMORY UPDATE --------
        facts = extract_facts(
            model,
            plan + "\n" + tool_output + "\n" + analysis
        )
        for f in facts:
            if f not in memory["facts"]:
                memory["facts"].append(f)

        memory["notes"].append(analysis[:200])
        save_memory(memory)

        if "DONE" in analysis.upper():
            break

        time.sleep(SLEEP_BETWEEN_CYCLES)

    print("\n✅ Agent finished.")
    save_memory(memory)


# ================= MAIN =================

def main():
    tools = discover_hexstrike_tools()
    if not tools:
        print("No tools available.")
        sys.exit(1)

    models = get_models()
    print("\nAvailable Ollama models:")
    for i, m in enumerate(models, 1):
        print(f"{i}. {m['name']}")

    model = models[int(input("\nSelect model: ")) - 1]["name"]
    run_agent(model, tools)


if __name__ == "__main__":
    main()
