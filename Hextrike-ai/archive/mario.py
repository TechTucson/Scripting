import requests
import sys

OLLAMA_URL = "http://localhost:11434"


def get_models():
    """Fetch available Ollama models."""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags")
        response.raise_for_status()
        return response.json().get("models", [])
    except requests.RequestException as e:
        print(f"Error connecting to Ollama: {e}")
        sys.exit(1)


def select_model(models):
    """Let user select a model by number."""
    if not models:
        print("No models found. Run `ollama pull <model>` first.")
        sys.exit(1)

    print("\nAvailable Ollama models:\n")
    for i, model in enumerate(models, start=1):
        print(f"{i}. {model['name']}")

    while True:
        try:
            choice = int(input("\nSelect a model number: "))
            if 1 <= choice <= len(models):
                return models[choice - 1]["name"]
            else:
                print("Invalid number.")
        except ValueError:
            print("Please enter a number.")


def chat(model):
    """Simple chat loop."""
    print(f"\nChatting with model: {model}")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in {"exit", "quit"}:
            break

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

