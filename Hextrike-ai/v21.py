#!/usr/bin/env python3

import requests
import sys
import time
import re
import json
import os
import hashlib
from datetime import datetime

# ================= CONFIG =================

# Defaults (used if user accepts prompt default)
OLLAMA_URL_DEFAULT = "http://localhost:11434"
HEXSTRIKE_URL_DEFAULT = "http://192.168.56.101:8888"

# These will be overridden at runtime based on user input (or remain defaults)
OLLAMA_URL = OLLAMA_URL_DEFAULT
HEXSTRIKE_URL = HEXSTRIKE_URL_DEFAULT

TIMEOUT = 10
MAX_CYCLES = 6
SLEEP_BETWEEN_CYCLES = 1.5

VERBOSE_LLM = True

MEMORY_FILE = "agent_memory.json"
EVIDENCE_DIR = "evidence"

HEX_PATTERN = re.compile(r"^!hex\s+(.+)$", re.IGNORECASE)

os.makedirs(EVIDENCE_DIR, exist_ok=True)

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
        "evidence": [],
        "notes": [],
        "last_updated": None
    }


def normalize_memory(memory):
    defaults = {
        "facts": [],
        "tools_used": [],
        "evidence": [],
        "notes": [],
        "last_updated": None
    }
    for k, v in defaults.items():
        memory.setdefault(k, v)
    return memory


def save_memory(memory):
    memory["last_updated"] = datetime.utcnow().isoformat()
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


# ================= EVIDENCE =================

def hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def take_screenshot(label):
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{EVIDENCE_DIR}/screenshot_{label}_{ts}.png"

    for cmd in [
        f"gnome-screenshot -f {filename}",
        f"scrot {filename}"
    ]:
        if os.system(cmd) == 0 and os.path.exists(filename):
            return filename

    return None


# ================= OLLAMA =================

def ollama_generate(model, system, prompt, label=""):
    if VERBOSE_LLM:
        print("\n" + "=" * 80)
        print(f"📤 LLM REQUEST [{label}]")
        print("-" * 80)
        print(prompt)
        print("=" * 80)

    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model,
            "system": system,
            "prompt": prompt,
            "stream": False
        },
        timeout=300
    )
    r.raise_for_status()
    response = r.json()["response"].strip()

    if VERBOSE_LLM:
        print("\n" + "=" * 80)
        print(f"📥 LLM RESPONSE [{label}]")
        print("-" * 80)
        print(response)
        print("=" * 80)

    return response


def ollama_generate_stream(model, system, prompt, label=""):
    print("\n" + "=" * 80)
    print(f"📤 LLM STREAM [{label}]")
    print("=" * 80)

    r = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model,
            "system": system,
            "prompt": prompt,
            "stream": True
        },
        stream=True
    )
    r.raise_for_status()

    full_text = ""
    for line in r.iter_lines():
        if not line:
            continue
        data = json.loads(line.decode("utf-8"))
        chunk = data.get("response", "")
        print(chunk, end="", flush=True)
        full_text += chunk

    print("\n" + "=" * 80)
    return full_text


def get_models():
    r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["models"]


def build_system_prompt(tools):
    return f"""
You are an autonomous cybersecurity agent.

PHASES:
PLAN → EXECUTE → ANALYZE

EXECUTE RULES:
- Output EXACTLY one of:
  !hex <tool> <arguments>
  NO TOOL
- No explanations
- One tool max per cycle
- Use ONLY allowed tools
- Say DONE only when the objective is complete

If a GUI-based tool is used or significant findings occur,
request evidence by including:
EVIDENCE: SCREENSHOT

Allowed tools:
{", ".join(tools)}
"""


# ================= HEXSTRIKE =================

def discover_hexstrike_tools():
    r = requests.get(f"{HEXSTRIKE_URL}/health", timeout=TIMEOUT)
    r.raise_for_status()

    tools_status = r.json().get("tools_status", {})
    tools = sorted(t for t, ok in tools_status.items() if ok)

    print("\n[+] Available Hexstrike tools:")
    for t in tools:
        print(f" - {t}")

    return tools


def execute_hexstrike(cmd):
    print(f"\n⚙️ EXECUTING TOOL:\n{cmd}\n")
    r = requests.post(
        f"{HEXSTRIKE_URL}/api/command",
        json={"command": cmd},
        timeout=300
    )
    if r.status_code == 200:
        return r.json().get("output", "")
    return f"HTTP error {r.status_code}"


# ================= AGENT =================

def run_agent(model, tools):
    system_prompt = build_system_prompt(tools)

    objective = input("\n🎯 Objective: ").strip()
    memory = normalize_memory(load_memory(objective))

    for cycle in range(1, MAX_CYCLES + 1):
        print(f"\n===== CYCLE {cycle} =====")

        context = (
            f"Objective: {objective}\n"
            f"Known facts:\n" + "\n".join(memory["facts"])
        )

        plan = ollama_generate(
            model, system_prompt,
            context + "\n[PLAN]\nWhat is the next step?",
            "PLAN"
        )

        if "DONE" in plan.upper():
            break

        execute = ollama_generate(
            model, system_prompt,
            context + f"\nPLAN:\n{plan}\n\n[EXECUTE]\nCommand or NO TOOL.",
            "EXECUTE"
        ).strip()

        tool_output = "NO TOOL EXECUTED"
        tool_used = None

        if execute != "NO TOOL":
            m = HEX_PATTERN.match(execute)
            if m:
                cmd = m.group(1)
                tool = cmd.split()[0]
                if tool in tools:
                    tool_used = tool
                    memory["tools_used"].append(tool)
                    tool_output = execute_hexstrike(cmd)

                    memory["evidence"].append({
                        "type": "command_output",
                        "tool": tool,
                        "timestamp": datetime.utcnow().isoformat(),
                        "excerpt": tool_output[:1000]
                    })

        analysis = ollama_generate(
            model, system_prompt,
            context +
            f"\nPLAN:\n{plan}\nEXECUTE:\n{execute}\nOUTPUT:\n{tool_output}\n[ANALYZE]",
            "ANALYZE"
        )

        if "EVIDENCE: SCREENSHOT" in analysis.upper():
            path = take_screenshot(tool_used or "generic")
            if path:
                memory["evidence"].append({
                    "type": "screenshot",
                    "tool": tool_used,
                    "file": path,
                    "hash": hash_file(path),
                    "timestamp": datetime.utcnow().isoformat()
                })

        memory["notes"].append(analysis[:300])
        save_memory(memory)

        if "DONE" in analysis.upper():
            break

        time.sleep(SLEEP_BETWEEN_CYCLES)

    return memory


# ================= REPORT =================

def generate_report(model, memory):
    prompt = f"""
Generate a professional cybersecurity report.

Objective:
{memory['objective']}

Tools Used:
{', '.join(set(memory['tools_used']))}

Evidence (JSON):
{json.dumps(memory['evidence'], indent=2)}

Analyst Notes:
{chr(10).join(memory['notes'])}

Structure:
- Executive Summary
- Methodology
- Findings
- Evidence
- Risk Assessment
- Recommendations
"""
    return ollama_generate_stream(model, "", prompt, "REPORT")


# ================= MAIN =================

def prompt_with_default(prompt_text, default):
    try:
        val = input(f"{prompt_text} [{default}]: ").strip()
    except EOFError:
        # Non-interactive environment: fall back to default
        val = ""
    return val if val else default


def main():
    global OLLAMA_URL, HEXSTRIKE_URL

    # Ask user for endpoints, showing defaults
    print("Configure endpoints (press Enter to accept the default shown in brackets).")
    OLLAMA_URL = prompt_with_default("Ollama URL", OLLAMA_URL_DEFAULT)
    HEXSTRIKE_URL = prompt_with_default("Hexstrike URL", HEXSTRIKE_URL_DEFAULT)

    print(f"\nUsing Ollama URL: {OLLAMA_URL}")
    print(f"Using Hexstrike URL: {HEXSTRIKE_URL}")

    tools = discover_hexstrike_tools()
    if not tools:
        print("No tools available.")
        sys.exit(1)

    models = get_models()
    print("\nAvailable Ollama models:")
    for i, m in enumerate(models, 1):
        print(f"{i}. {m['name']}")

    try:
        model = models[int(input("\nSelect model: ")) - 1]["name"]
    except Exception:
        print("Invalid model selection.")
        sys.exit(1)

    memory = run_agent(model, tools)

    print("\n📝 GENERATING FINAL REPORT (STREAMING)\n")
    report = generate_report(model, memory)

    with open("final_report.md", "w") as f:
        f.write(report)

    print("\n📄 Report saved as final_report.md")


if __name__ == "__main__":
    main()
