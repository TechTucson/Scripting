import requests
import time
import re
import json
from datetime import datetime
from flask import Flask, request, Response, render_template_string

# ================= CONFIG =================

OLLAMA_URL = "http://localhost:11434"
Hexstrike = "http://192.168.56.101:8888"

TIMEOUT = 10
MAX_CYCLES = 5
MEMORY_FILE = "agent_memory.json"

HEX_PATTERN = re.compile(r"^!hex\s+(.+)$", re.IGNORECASE)

app = Flask(__name__)

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


def save_memory(mem):
    mem["last_updated"] = datetime.utcnow().isoformat()
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2)


# ================= HEXSTRIKE =================

def discover_tools():
    r = requests.get(f"{Hexstrike}/health", timeout=TIMEOUT)
    r.raise_for_status()
    tools_status = r.json().get("tools_status", {})
    return sorted(t for t, ok in tools_status.items() if ok)


def exec_hex(cmd):
    r = requests.post(
        f"{Hexstrike}/api/command",
        json={"command": cmd},
        timeout=300
    )
    if r.status_code == 200:
        return r.json().get("output", "")
    return f"HTTP {r.status_code}"


# ================= OLLAMA =================

def ollama(model, system, prompt):
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


def system_prompt(tools):
    return f"""
You are an autonomous cybersecurity agent.

PHASES:
PLAN → EXECUTE → ANALYZE

EXECUTE RULES (MANDATORY):
- Output EXACTLY ONE of:
  !hex <tool> <args>
  NO TOOL
- No explanations
- One tool max
- Use ONLY allowed tools
- Say DONE only when finished

Allowed tools:
{", ".join(tools)}
"""


# ================= AGENT =================

def run_agent(objective, model):
    tools = discover_tools()
    sys_prompt = system_prompt(tools)
    memory = load_memory(objective)

    yield f"Objective: {objective}\n"
    yield f"Available tools: {', '.join(tools)}\n\n"

    for cycle in range(1, MAX_CYCLES + 1):
        yield f"\n===== CYCLE {cycle} =====\n"

        context = (
            f"Objective: {objective}\n"
            f"Known facts:\n" + "\n".join(memory["facts"])
        )

        plan = ollama(model, sys_prompt, context + "\n[PLAN]\nNext step?")
        yield f"\nPLAN:\n{plan}\n"

        if "DONE" in plan.upper():
            break

        exec_prompt = (
            context +
            f"\nPLAN:\n{plan}\n\n"
            "[PHASE: EXECUTE]\n"
            "Output ONLY command or NO TOOL."
        )

        execute = ollama(model, sys_prompt, exec_prompt).strip()
        yield f"\nEXECUTE:\n{execute}\n"

        output = "NO TOOL EXECUTED"

        if execute != "NO TOOL":
            m = HEX_PATTERN.match(execute)
            if m:
                cmd = m.group(1)
                tool = cmd.split()[0]
                if tool in tools:
                    output = exec_hex(cmd)
                    memory["tools_used"].append(tool)
                else:
                    output = f"Tool not allowed: {tool}"
            else:
                output = "INVALID EXECUTE OUTPUT"

        yield f"\nOUTPUT:\n{output}\n"

        analysis = ollama(
            model,
            sys_prompt,
            context +
            f"\nPLAN:\n{plan}\nEXECUTE:\n{execute}\nOUTPUT:\n{output}\n[ANALYZE]"
        )
        yield f"\nANALYSIS:\n{analysis}\n"

        memory["notes"].append(analysis[:200])
        save_memory(memory)

        if "DONE" in analysis.upper():
            break

        time.sleep(1)

    yield "\n=== AGENT FINISHED ===\n"


# ================= WEB UI =================

HTML = """
<!doctype html>
<title>Hexstrike Agent</title>
<h2>🧠 Hexstrike Autonomous Agent</h2>

<form action="/run" method="post">
  Objective:<br>
  <input name="objective" size="60" required><br><br>
  Ollama Model:<br>
  <input name="model" value="llama3" size="30"><br><br>
  <button type="submit">Run Agent</button>
</form>

<pre id="log"></pre>

<script>
const evtSource = new EventSource("/stream");
evtSource.onmessage = e => {
  document.getElementById("log").textContent += e.data;
};
</script>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/run", methods=["POST"])
def run():
    global agent_generator
    objective = request.form["objective"]
    model = request.form["model"]
    agent_generator = run_agent(objective, model)
    return "Agent started. Go back."


@app.route("/stream")
def stream():
    def generate():
        while True:
            try:
                yield next(agent_generator)
            except Exception:
                time.sleep(0.5)
    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
