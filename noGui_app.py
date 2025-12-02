#!/usr/bin/env python3
import base64
import json
import os
import sys
import requests
from config import ServerIp, Port, API_KEY

# URL address LM Studio
LM_URL = f"http://{ServerIp}:{Port}/v1/chat/completions"
MODELS_URL = f"http://{ServerIp}:{Port}/v1/models"
# The maximum total size of base64 fields in bytes (for example, configure it for the server)
MAX_TOTAL_BYTES = 100 * 1024 * 1024
# Max count for tokens
MAX_TOKENTS = 131000
# Supported image formats
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
# A variable for storing models
SELECTED_MODEL = None


def get_available_models():
    # Get list of available models from LM Studio
    headers = {}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    try:
        resp = requests.get(MODELS_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        models_data = resp.json()

        models = []
        for model in models_data.get("data", []):
            model_info = {
                "id": model.get("id"),
                "name": model.get("id", "Unknown"),
            }
            models.append(model_info)

        return models
    except requests.RequestException as e:
        print(f"Error fetching models: {e}", file=sys.stderr)
        return e


def set_model(model):
    global SELECTED_MODEL
    SELECTED_MODEL = model


def select_model():
    """Allow user to select a model from available ones"""
    print("Fetching available models...")
    try:
        models = get_available_models()

        if not models:
            print("No models found or couldn't connect to LM Studio")
            print("Please check if LM Studio is running and the server settings in config.py")
            return None

        print(f"\nAvailable models ({len(models)}):")
        for i, model in enumerate(models, 1):
            print(f"{i}. {model['name']}")

        while True:
            try:
                choice = input(f"\nSelect model (1-{len(models)}): ").strip()
                if not choice:
                    continue

                choice_num = int(choice)
                if 1 <= choice_num <= len(models):
                    selected = models[choice_num - 1]
                    print(f"Selected model: {selected['name']}")
                    return selected['id']
                else:
                    print(f"Please enter a number between 1 and {len(models)}")
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                print("\nOperation cancelled")
                return None
    except Exception as ex:
        print(ex)


def encode_file_to_b64(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("ascii"), len(data)


def is_image_file(path):
    _, ext = os.path.splitext(path.lower())
    return ext in IMAGE_EXTENSIONS


def get_mime_type(path):
    _, ext = os.path.splitext(path.lower())
    mime_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.webp': 'image/webp'
    }
    return mime_map.get(ext, 'application/octet-stream')


def build_messages_with_files(user_message, file_paths):
    messages = [{"role": "user", "content": []}]
    total_bytes = 0

    # Add text part
    if user_message:
        messages[0]["content"].append({
            "type": "text",
            "text": user_message
        })

    if not file_paths:
        return messages

    for path in file_paths:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"File not found: {path}")

        b64, raw_len = encode_file_to_b64(path)
        total_bytes += len(b64)
        if total_bytes > MAX_TOTAL_BYTES:
            raise ValueError(f"Total encoded payload too large (> {MAX_TOTAL_BYTES} bytes). Reduce files or size.")

        fname = os.path.basename(path)

        if is_image_file(path):
            # For images, use the vision-compatible format
            image_message = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{get_mime_type(path)};base64,{b64}"
                }
            }
            messages[0]["content"].append(image_message)
        else:
            # For non-image files, keep the original format or add as text
            file_message = {
                "type": "text",
                "text": f"File: {fname}\nContent (base64): {b64[:100]}..."  # Show only first 100 chars
            }
            messages[0]["content"].append(file_message)

    return messages


def ask_with_embedded_files(message, file_paths=None, temperature=0.7, max_tokens=MAX_TOKENTS, timeout=3600):
    global SELECTED_MODEL

    if not SELECTED_MODEL:
        raise ValueError("No model selected. Please select a model first.")

    try:
        messages = build_messages_with_files(message, file_paths or [])
    except Exception as e:
        raise

    payload = {
        "model": SELECTED_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"

    resp = requests.post(LM_URL, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    j = resp.json()

    try:
        return j["choices"][0]["message"]["content"]
    except Exception:
        # If the structure is unexpected, return all the JSON for debugging.
        return json.dumps(j, ensure_ascii=False, indent=2)


def print_current_model():
    """Print currently selected model"""
    global SELECTED_MODEL
    if SELECTED_MODEL:
        print(f"Current model: {SELECTED_MODEL}")
    else:
        print("No model selected")


def print_models():
    # Print available models
    print("\nFetching available models...")
    models = get_available_models()

    if not models:
        print("No models found or couldn't connect to LM Studio")
        return

    print(f"\nAvailable models ({len(models)}):")
    for i, model in enumerate(models, 1):
        print(f"{i}. {model['name']}")


def main():
    global SELECTED_MODEL

    print("LM Studio Chat Client")
    print("=" * 50)

    # Step 1: Select model
    SELECTED_MODEL = select_model()
    if not SELECTED_MODEL:
        print("Failed to select model. Exiting.")
        return

    print("\n" + "=" * 50)
    print("Chat session started!")
    print("Commands:")
    print("  /models - Show available models and change")
    print("  /model  - Show current model")
    print("  /exit   - Exit program")
    print("  Ctrl+C  - Exit program")
    print("=" * 50)

    try:
        while True:
            user_input = input("\n> ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() == '/models':
                new_model = select_model()
                if new_model:
                    SELECTED_MODEL = new_model
                    print(f"Model changed to: {SELECTED_MODEL}")
                continue
            elif user_input.lower() == '/model':
                print_current_model()
                continue
            elif user_input.lower() == '/exit':
                break

            # Regular message
            file_input = input("Files (comma separated full paths, enter to skip): ").strip()
            paths = [p.strip() for p in file_input.split(",") if p.strip()] if file_input else None

            try:
                reply = ask_with_embedded_files(user_input, file_paths=paths, max_tokens=MAX_TOKENTS)
                print(f"Assistant: {reply}")
            except FileNotFoundError as e:
                print(f"Error: {e}", file=sys.stderr)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
            except requests.RequestException as e:
                print(f"HTTP error: {e}", file=sys.stderr)
            except Exception as e:
                print(f"Unexpected error: {e}", file=sys.stderr)

    except KeyboardInterrupt:
        print("\nExit")


if __name__ == "__main__":
    main()
