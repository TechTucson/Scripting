#!/usr/bin/env python3

import requests
import sys
import time
import json
import os
import re
import hashlib
from datetime import datetime

# ===================== DEFAULTS =====================

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_HEXSTRIKE_URL = "http://192.168.56.101:8888"

TIMEOUT = 10
MAX_CYCLES = 6
SLEEP_BETWEEN_CYCLES = 1.5

VERBOSE_LLM = True
MEMORY_FILE = "agent_memory.json"
EVIDENCE_DIR = "evidence"

HEX_PATTERN = re.compile(r"^!hex\s+(.+)$", re.IGNORECASE)

os.makedirs(EVIDENCE_DIR, exist_ok=True)

OLLAMA_URL = None
HEXSTRIKE_URL = None

# ===================== UTILS =====================

def prompt_url(name, default):
    val = input(f"{name} [{default}]: ").strip()
    return val if val else default


def print_prompt_diff(prev, curr, label):
    if not prev:
        return
    print("\n" + "═" * 90)
    print(f"🔍 PROMPT DIFF ({label})")
    print("─" * 90)
    left = prev.splitlines()
    right = curr.splitlines()
    width = 45
    for i in range(max(len(left), len(right))):
        l = left[i] if i < len(left) else ""
        r = right[i] if i < len(right) else ""
        print(f"{l[:width]:<{width}} | {r[:width]}")
    print("═" * 90)


def extract_confidence(text):
    for line in text.splitlines():
        if line.upper().startswith("CONFIDENCE"):
            try:
                return float(line.split(":")[1].strip())
            except Exception:
                pass
    return 0.0


def hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

# ===================== MEMORY =====================

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


def save_memory(memory):
    memory["last_updated"] = datetime.utcnow().isoformat()
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

# ===================== OLLAMA =====================

def get_models():
    r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["models"]


def ollama_generate(model, system, prompt, label=""):
    if VERBOSE_LLM:
        print("\n" + "=" * 90)
        print(f"📤 LLM REQUEST [{label}]")
        print("-" * 90)
        print(prompt)
        print("=" * 90)

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
        print("\n" + "=" * 90)
        print(f"📥 LLM RESPONSE [{label}]")
        print("-" * 90)
        print(response)
        print("=" * 90)

    return response


def ollama_generate_stream(model, system, prompt, label=""):
    print("\n" + "=" * 90)
    print(f"📤 LLM STREAM [{label}]")
    print("=" * 90)

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

    full = ""
    for line in r.iter_lines():
        if not line:
            continue
        data = json.loads(line.decode())
        chunk = data.get("response", "")
        print(chunk, end="", flush=True)
        full += chunk

    print("\n" + "=" * 90)
    return full

# ===================== HEXSTRIKE =====================

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
    print(f"\n⚙️ EXECUTING:\n{cmd}\n")
    r = requests.post(
        f"{HEXSTRIKE_URL}/api/command",
        json={"command": cmd},
        timeout=300
    )
    if r.status_code == 200:
        return r.json().get("output", "")
    return f"HTTP error {r.status_code}"

# ===================== PROMPTS =====================

def build_system_prompt(tools):
    return f"""
You are an autonomous cybersecurity agent operating in a STRICT PHASE LOOP.

PHASES:
PLAN → EXECUTE → ANALYZE

PLAN:
- Decide next single step
- NO commands

EXECUTE:
- Output ONE line only
- !hex <tool> <args> OR NO TOOL

ANALYZE:
- Interpret results
- Extract facts
- Include CONFIDENCE: <0.0–1.0>
- Say DONE only if confidence ≥ 0.9

RULES:
- Never mix phases
- Never explain EXECUTE
- If unsure, choose NO TOOL

TOOLS:
{", ".join(tools)}
"""

# ===================== AGENT =====================

def run_agent(model, tools):
    system = build_system_prompt(tools)
    objective = input("\n🎯 Objective: ").strip()
    memory = load_memory(objective)

    last_prompt = None

    for cycle in range(1, MAX_CYCLES + 1):
        print(f"\n===== CYCLE {cycle} =====")

        plan_prompt = f"""
=== PHASE: PLAN ===

Objective:
{objective}

Known Facts:
{chr(10).join(memory['facts'])}

Notes:
{chr(10).join(memory['notes'][-3:])}

Describe the NEXT step.
"""
        print_prompt_diff(last_prompt, plan_prompt, "PLAN")
        plan = ollama_generate(model, system, plan_prompt, "PLAN")

        execute_prompt = f"""
=== PHASE: EXECUTE ===

PLAN:
{plan}

Output ONLY:
!hex <tool> <args>
OR
NO TOOL
"""
        print_prompt_diff(plan_prompt, execute_prompt, "EXECUTE")
        execute = ollama_generate(model, system, execute_prompt, "EXECUTE").strip()

        tool_output = "NO TOOL"
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
                        "excerpt": tool_output[:1000],
                        "timestamp": datetime.utcnow().isoformat()
                    })

        analyze_prompt = f"""
=== PHASE: ANALYZE ===

PLAN:
{plan}

EXECUTE:
{execute}

OUTPUT:
{tool_output}

Include:
CONFIDENCE: <0.0–1.0>
"""
        print_prompt_diff(execute_prompt, analyze_prompt, "ANALYZE")
        analysis = ollama_generate(model, system, analyze_prompt, "ANALYZE")

        confidence = extract_confidence(analysis)
        print(f"🔐 Confidence: {confidence}")

        memory["notes"].append(analysis[:300])
        save_memory(memory)

        if "DONE" in analysis.upper() and confidence >= 0.9:
            print("✅ Objective completed with high confidence")
            break

        last_prompt = plan_prompt
        time.sleep(SLEEP_BETWEEN_CYCLES)

    return memory

# ===================== REPORT =====================

def generate_report(model, memory):
    prompt = f"""
Generate a professional cybersecurity report.

Objective:
{memory['objective']}

Tools Used:
{', '.join(set(memory['tools_used']))}

Evidence:
{json.dumps(memory['evidence'], indent=2)}

Notes:
{chr(10).join(memory['notes'])}

Sections:
- Executive Summary
- Methodology
- Findings
- Evidence
- Risk Assessment
- Recommendations
"""
    return ollama_generate_stream(model, "", prompt, "REPORT")

# ===================== MAIN =====================

def main():
    global OLLAMA_URL, HEXSTRIKE_URL

    print("\n🔧 Configure Endpoints (Enter = default)\n")
    HEXSTRIKE_URL = prompt_url("Hexstrike URL", DEFAULT_HEXSTRIKE_URL)
    OLLAMA_URL = prompt_url("Ollama URL", DEFAULT_OLLAMA_URL)

    tools = discover_hexstrike_tools()
    models = get_models()

    print("\nAvailable Ollama models:")
    for i, m in enumerate(models, 1):
        print(f"{i}. {m['name']}")

    model = models[int(input("\nSelect model: ")) - 1]["name"]

    memory = run_agent(model, tools)

    print("\n📝 GENERATING FINAL REPORT\n")
    report = generate_report(model, memory)

    with open("final_report.md", "w") as f:
        f.write(report)

    print("\n📄 Report saved to final_report.md")

if __name__ == "__main__":
    main()
