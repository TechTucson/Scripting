#!/usr/bin/env python3
import curses
import requests
import json
import time
import threading
import re
from datetime import datetime

# ===================== DEFAULTS =====================

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_HEXSTRIKE_URL = "http://192.168.56.101:8888"
TIMEOUT = 10
HEX_PATTERN = re.compile(r"^!hex\s+(.+)$", re.IGNORECASE)

# ===================== GLOBAL STATE =====================

STATE = {
    "hex_url": DEFAULT_HEXSTRIKE_URL,
    "ollama_url": DEFAULT_OLLAMA_URL,
    "model": "",
    "objective": "",
    "phase": "IDLE",
    "confidence": 0.0,
    "llm_prompt": "",
    "llm_response": "",
    "tool_output": [],
    "running": False,
    "quit": False,
    "tools": [],
    "scroll_offset": 0,
}

LAST_DRAW = {
    "left": [],
    "right": [],
    "bottom": []
}

# ===================== LLM =====================

def ollama_generate(prompt, system=""):
    r = requests.post(
        f"{STATE['ollama_url']}/api/generate",
        json={
            "model": STATE["model"],
            "system": system,
            "prompt": prompt,
            "stream": False
        },
        timeout=300
    )
    r.raise_for_status()
    return r.json()["response"].strip()


def extract_confidence(text):
    for line in text.splitlines():
        if line.upper().startswith("CONFIDENCE"):
            try:
                return float(line.split(":")[1].strip())
            except Exception:
                pass
    return 0.0

# ===================== HEXSTRIKE =====================

def discover_tools():
    r = requests.get(f"{STATE['hex_url']}/health", timeout=TIMEOUT)
    r.raise_for_status()
    tools_status = r.json().get("tools_status", {})
    return sorted(t for t, ok in tools_status.items() if ok)


def execute_hexstrike(cmd):
    r = requests.post(
        f"{STATE['hex_url']}/api/command",
        json={"command": cmd},
        timeout=300
    )
    if r.status_code == 200:
        return r.json().get("output", "")
    return f"HTTP {r.status_code}"

# ===================== PROMPTS =====================

def system_prompt():
    return f"""
You are a STRICT phase-based cybersecurity agent.

PLAN:
- Decide next step
- NO commands

EXECUTE:
- Output ONLY:
  !hex <tool> <args>
  OR
  NO TOOL

ANALYZE:
- Interpret output
- Include CONFIDENCE: <0.0–1.0>
- Say DONE only if confidence ≥ 0.9

TOOLS:
{", ".join(STATE["tools"])}
"""

# ===================== AGENT LOOP =====================

def agent_loop():
    while not STATE["quit"]:
        if not STATE["running"]:
            time.sleep(0.2)
            continue

        # -------- PLAN --------
        STATE["phase"] = "PLAN"
        plan_prompt = f"""
=== PHASE: PLAN ===
Objective:
{STATE['objective']}

Describe the NEXT step.
"""
        STATE["llm_prompt"] = plan_prompt
        plan = ollama_generate(plan_prompt, system_prompt())
        STATE["llm_response"] = plan

        # -------- EXECUTE --------
        STATE["phase"] = "EXECUTE"
        exec_prompt = f"""
=== PHASE: EXECUTE ===
PLAN:
{plan}

Output ONLY:
!hex <tool> <args>
OR
NO TOOL
"""
        STATE["llm_prompt"] = exec_prompt
        execute = ollama_generate(exec_prompt, system_prompt()).strip()
        STATE["llm_response"] = execute

        tool_output = "NO TOOL"
        if execute != "NO TOOL":
            m = HEX_PATTERN.match(execute)
            if m:
                cmd = m.group(1)
                tool = cmd.split()[0]
                if tool in STATE["tools"]:
                    STATE["tool_output"].append(f"[{datetime.utcnow()}] {cmd}")
                    tool_output = execute_hexstrike(cmd)
                    STATE["tool_output"].extend(tool_output.splitlines()[-50:])  # last 50 lines max

        # -------- ANALYZE --------
        STATE["phase"] = "ANALYZE"
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
        STATE["llm_prompt"] = analyze_prompt
        analysis = ollama_generate(analyze_prompt, system_prompt())
        STATE["llm_response"] = analysis
        STATE["confidence"] = extract_confidence(analysis)

        if "DONE" in analysis.upper() and STATE["confidence"] >= 0.9:
            STATE["tool_output"].append("✅ Objective completed")
            STATE["running"] = False
            STATE["phase"] = "IDLE"

        time.sleep(1)

# ===================== UI =====================

def draw_box(win, title):
    win.box()
    win.addstr(0, 2, f" {title} ")

def draw_lines(win, lines, last_lines):
    maxy, maxx = win.getmaxyx()
    for i, l in enumerate(lines, 2):
        if i >= maxy - 1:
            break
        if i >= len(last_lines) or last_lines[i] != l[:maxx-4]:
            win.addstr(i, 2, l[:maxx-4])
    # fill remaining lines with spaces if shrinking
    for i in range(len(lines)+2, maxy-1):
        win.addstr(i, 2, " " * (maxx-4))
    return lines[:]

def draw_left(win):
    win.clear()
    draw_box(win, "CONFIG / STATUS")
    lines = [
        f"Hexstrike: {STATE['hex_url']}",
        f"Ollama:    {STATE['ollama_url']}",
        f"Model:     {STATE['model']}",
        "",
        f"Objective: {STATE['objective']}",
        "",
        f"Phase:     {STATE['phase']}",
        f"Confidence:{STATE['confidence']:.2f}",
        "",
        "[s] Start",
        "[p] Pause",
        "[q] Quit"
    ]
    LAST_DRAW["left"][:] = draw_lines(win, lines, LAST_DRAW["left"])
    win.refresh()

def draw_right(win):
    win.clear()
    draw_box(win, "LLM PROMPT / RESPONSE")
    lines = ["PROMPT:"] + STATE["llm_prompt"].splitlines() + ["", "RESPONSE:"] + STATE["llm_response"].splitlines()
    LAST_DRAW["right"][:] = draw_lines(win, lines, LAST_DRAW["right"])
    win.refresh()

def draw_bottom(win):
    win.clear()
    draw_box(win, "TOOL OUTPUT (scrollable with ↑/↓)")
    maxy, maxx = win.getmaxyx()
    output = STATE["tool_output"]
    scroll = STATE["scroll_offset"]
    visible = output[scroll:scroll + maxy-3]
    LAST_DRAW["bottom"][:] = draw_lines(win, visible, LAST_DRAW["bottom"])
    win.refresh()

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)

    h, w = stdscr.getmaxyx()
    bottom_height = max(15, h // 3)
    top_height = h - bottom_height

    left = curses.newwin(top_height, w//2, 0, 0)
    right = curses.newwin(top_height, w - w//2, 0, w//2)
    bottom = curses.newwin(bottom_height, w, top_height, 0)

    threading.Thread(target=agent_loop, daemon=True).start()

    while not STATE["quit"]:
        draw_left(left)
        draw_right(right)
        draw_bottom(bottom)

        try:
            key = stdscr.getch()
        except:
            key = -1

        if key == ord('q'):
            STATE["quit"] = True
        elif key == ord('s'):
            STATE["running"] = True
        elif key == ord('p'):
            STATE["running"] = False
        elif key == curses.KEY_UP:
            STATE["scroll_offset"] = max(0, STATE["scroll_offset"] - 1)
        elif key == curses.KEY_DOWN:
            STATE["scroll_offset"] = min(max(0, len(STATE["tool_output"]) - (bottom_height-3)), STATE["scroll_offset"])

        time.sleep(0.1)

# ===================== SETUP =====================

def setup():
    print("\n🔧 Initial Configuration (press Enter for defaults)\n")

    STATE["hex_url"] = input(f"Hexstrike URL [{DEFAULT_HEXSTRIKE_URL}]: ").strip() or DEFAULT_HEXSTRIKE_URL
    STATE["ollama_url"] = input(f"Ollama URL [{DEFAULT_OLLAMA_URL}]: ").strip() or DEFAULT_OLLAMA_URL

    print("\nDiscovering Hexstrike tools...")
    STATE["tools"] = discover_tools()
    print(f"Found {len(STATE['tools'])} tools.")

    models = requests.get(f"{STATE['ollama_url']}/api/tags", timeout=TIMEOUT).json()["models"]

    print("\nAvailable Ollama models:")
    for i, m in enumerate(models, 1):
        print(f"{i}. {m['name']}")

    choice = int(input("\nSelect model number: "))
    STATE["model"] = models[choice-1]["name"]
    STATE["objective"] = input("\n🎯 Objective: ").strip()

# ===================== ENTRY =====================

if __name__ == "__main__":
    setup()
    curses.wrapper(main)
