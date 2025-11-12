#!/usr/bin/env python3
import requests, os
from config import ServerIp, Port, Model, API_KEY

LM_URL = f"http://{ServerIp}:{Port}/v1/chat/completions"

def ask(message):
    payload = {
        "model": Model,
        "messages": [{"role": "user", "content": message}],
        "temperature": 0.7,
        "max_tokens": 4096
    }
    headers={"Content-Type":"application/json"}
    if API_KEY:
        headers["Authorization"]=f"Bearer {API_KEY}"
    r=requests.post(LM_URL,json=payload,headers=headers)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def main():
    print("Enter the message (Ctrl+C to exit):")
    try:
        while True:
            msg = input("> ")
            if not msg.strip(): continue
            reply = ask(msg)
            print(f"Assistant: {reply}")
    except KeyboardInterrupt:
        print("\nExit")

if __name__ == "__main__":
    main()
