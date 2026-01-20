import requests
import sys

OLLAMA_URL = "http://localhost:11434"
Hexstrike = "http://192.168.56.101:8888"  # <-- CHANGE IF NEEDED


def execute_Hexstrike_command(cmd, description=""):
    """Execute command via Hexstrike with error handling"""
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


def chat(model):
    print(f"\nChatting with model: {model}")
    print("Type 'exit' to quit.")
    print("Use '!hex <command>' to run Hexstrike commands.\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            break

        # --- Hexstrike command path ---
        if user_input.startswith("!hex"):
            cmd = user_input[4:].strip()
            if not cmd:
                print("Usage: !hex <command>\n")
                continue

            success, output = execute_Hexstrike_command(
                cmd,
                description="Executing Hexstrike command"
            )

            print("\n[Hexstrike Output]")
            print(output)
            print()
            continue

        # --- Ollama LLM path ---
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


def main():
    models = get_models()
    model = select_model(models)
    chat(model)


if __name__ == "__main__":
    main()
