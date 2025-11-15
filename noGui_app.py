#!/usr/bin/env python3
import requests
import json
import os
from config import ServerIp, Port, Model, API_KEY

LM_URL = f"http://{ServerIp}:{Port}/v1/chat/completions"

def ask_with_files(message, file_paths=None):
    payload = {
        "model": Model,
        "messages": [{"role": "user", "content": message}],
        "temperature": 0.7,
        "max_tokens": 4096
    }

    # соберём multipart: поле payload с JSON и одно/несколько полей file
    data = {"payload": json.dumps(payload)}
    files = []
    file_handles = []

    try:
        if file_paths:
            for path in file_paths:
                fname = os.path.basename(path)
                fh = open(path, "rb")
                file_handles.append(fh)
                # имя поля "file" — при необходимости измените на то, что ожидает сервер
                files.append(("file", (fname, fh, "application/octet-stream")))

        headers = {}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"

        resp = requests.post(LM_URL, data=data, files=files, headers=headers)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    finally:
        for fh in file_handles:
            fh.close()

def main():
    print("Enter the message (Ctrl+C to exit):")
    try:
        while True:
            msg = input("> ").strip()
            if not msg:
                continue

            # пример: пользователь вводит пути к файлам через запятую:
            file_input = input("Files (comma separated, enter to skip): ").strip()
            paths = [p.strip() for p in file_input.split(",") if p.strip()] if file_input else None
            reply = ask_with_files(msg, file_paths=paths)
            print(f"Assistant: {reply}")
    except KeyboardInterrupt:
        print("\nExit")

if __name__ == "__main__":
    main()