# AI-Guided Pentesting Agent

## Overview

This project is a simple proof-of-concept agent that explores automation in penetration testing by combining Hexstrike for tooling and Ollama for local AI-driven decision making.

The goal is to experiment with how an agent can run tools, review results, and decide next steps during authorized penetration tests.

This is a research and learning project, not a replacement for a human penetration tester.

---

## How It Works (High Level)

1. The agent runs security tools through Hexstrike
2. Tool output is sent to a local LLM running in Ollama
3. The model suggests what to do next based on the results
4. The agent repeats this process

Both Hexstrike and Ollama must be running and reachable by the agent.

---

## A Look at my local environment
```
1.Bare Metal PC Running Ubuntu 24.04 (Running VirtualBox, and Ollama)     
  1.1 Virtualbox
  1.2 Ollama
2. VM Running KaliOS
  2.1 HexstrikeAI
  2.2 Juiceshop Running Locally (Docker)
  2.3 Host-Only Networking ( This allows the Host and Guest to communicate, as well as not allow the Guest to communicate with the outside world.  
```
---

## Requirements

* Python 3.x
* Hexstrike installed and running
* Ollama installed and running
* A local or lab environment you are authorized to test (Initially, I used a Docker JuiceShop container)

Hexstrike and Ollama must be able to communicate with the agent (same host or network, correct IPs/ports). The tools that Hexstrike is running should be able to access your JuiceShop application.

---

## Installation

### 1. Install Hexstrike

Follow the official Hexstrike installation instructions (I used Kali to install Hexstrike, as KaliOS comes with pre-installed tools) and confirm it is running.

Example check:

```bash
curl http://<hexstrike-ip>:<port>/health
```

---

### 2. Install Ollama

Install Ollama from the official site and pull a supported model (for this test, I am using qwen2.57b).

Example:

```bash
ollama pull qwen2.5:7b
```

Confirm Ollama is accessible:

```bash
curl http://<ollama-ip>:11434
```

---

### 3. Install/Run JuiceShop

```bash
docker pull bkimminich/juice-shop
docker run -d -p 3000:3000 --name juice-shop bkimminich/juice-shop
```

---

### 4. Clone This Repository

```bash
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name
```

Install Python dependencies: **This step is not done yet, meaning there is no requirements.txt file**

```bash
pip install -r requirements.txt
```

---

## Configuration

While running the agent, it will initially ask you for the needed configurations. If needed you can update the defaults for:
* Hexstrike URL and port
* Ollama URL and port

---

## Usage

> Only run this agent against systems you own or have explicit permission to test.

```bash
python3 agent.py
```

* Enter your Hexstrike URL
* Enter your Ollama URL
* Select Your LLM
* Review Available Tools
* Prompt the agent to do things (i.e. Please review the application hosted at http://127.0.0.1:3000 and let me know if it is vulnerable and exploitable. You have complete permission and the ability to run the available tools, as this is open-source code that runs locally. Once complete during the report writing, I'll need to know the exact command to run to prove the existence of these vulnerabilities.

## Generated Report

* [Sample Report From Assessing Juiceshop](https://github.com/TechTucson/Scripting/blob/master/Hextrike-ai/final_report.md)

### Screenshots

* [Browse Them Here](https://github.com/TechTucson/Scripting/tree/8e3ae4dd2aba910c09782e54a2177f5f9ebc2e2e/Hextrike-ai/Screenshots)



## Limitations

* AI output may be incorrect or incomplete
* Human oversight is required
* Effectiveness depends on model quality
* Intended for labs, demos, and research only

---

## To-Do's

* Fix Screenshots
* Test with other vulnerable-by-design test targets
* Add type of engagement and tailor process for each (i.e. Network, Web Application, AD)
* Add TUI. 

## Legal Disclaimer

This project is for **educational and research purposes only**. Unauthorized scanning or exploitation is illegal. You are responsible for ensuring proper authorization before use.

---

## License

Not sure about this yet. 

## Disclaimers and Acknowledgements

I may not know what I am doing :)
AI wrote most of the code.
