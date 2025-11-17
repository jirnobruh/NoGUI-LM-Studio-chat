#!/usr/bin/env python3
import base64
import json
import os
import sys
import requests
from config import ServerIp, Port, Model, API_KEY

# URL address LM Studio
LM_URL = f"http://{ServerIp}:{Port}/v1/chat/completions"
# The maximum total size of base64 fields in bytes (for example, configure it for the server)
MAX_TOTAL_BYTES = 100 * 1024 * 1024
# Max count for tokens
MAX_TOKENTS = 131000

def encode_file_to_b64(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("ascii"), len(data)

def build_messages_with_files(user_message, file_paths):
    messages = [{"role": "user", "content": user_message}]
    total_bytes = 0

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
        # The message format can be changed to meet the requirements of the server.
        file_message = {
            "role": "user",
            "content": json.dumps({
                "type": "file",
                "filename": fname,
                "encoding": "base64",
                "size_bytes": raw_len,
                "content_b64": b64
            })
        }
        messages.append(file_message)

    return messages

def ask_with_embedded_files(message, file_paths=None, temperature=0.7, max_tokens=4096, timeout=3600):
    try:
        messages = build_messages_with_files(message, file_paths or [])
    except Exception as e:
        raise

    payload = {
        "model": Model,
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

def main():
    print("Enter the message (Ctrl+C to exit):")
    try:
        while True:
            msg = input("> ").strip()
            if not msg:
                continue

            file_input = input("Files (comma separated full paths, enter to skip): ").strip()
            paths = [p.strip() for p in file_input.split(",") if p.strip()] if file_input else None

            try:
                reply = ask_with_embedded_files(msg, file_paths=paths, max_tokens=MAX_TOKENTS)
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