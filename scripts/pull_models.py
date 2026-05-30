#!/usr/bin/env python3
"""Script to programmatically pull Ollama models via API.

Uses Python standard library only to avoid external dependency issues.
"""

import json
import sys
import time
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434"
MODELS_TO_PULL = ["llama3.2:1b", "qwen2.5:0.5b"]

def check_ollama_ready(url: str, retries: int = 15, delay: int = 4) -> bool:
    print(f"Checking if Ollama is running at {url}...")
    for i in range(retries):
        try:
            with urllib.request.urlopen(f"{url}/api/tags") as response:
                if response.status == 200:
                    print("Ollama is ready!")
                    return True
        except Exception:
            pass
        print(f"Ollama not reachable (attempt {i+1}/{retries}). Retrying in {delay}s...")
        time.sleep(delay)
    return False

def pull_model(url: str, model_name: str) -> bool:
    print(f"\nPulling model '{model_name}'...")
    req = urllib.request.Request(
        f"{url}/api/pull",
        data=json.dumps({"name": model_name}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            last_status = ""
            for line in response:
                if not line:
                    continue
                try:
                    data = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                status = data.get("status", "")
                if status != last_status:
                    print(f"\nStatus: {status}")
                    last_status = status
                # If there's progress info, display it
                completed = data.get("completed", 0)
                total = data.get("total", 0)
                if total > 0:
                    percent = (completed / total) * 100
                    sys.stdout.write(f"\rProgress: {percent:.2f}% ({completed}/{total} bytes)")
                    sys.stdout.flush()
            print(f"\nFinished pulling {model_name}!")
            return True
    except urllib.error.URLError as e:
        print(f"Failed to pull {model_name}: {e}")
        return False

def main():
    if not check_ollama_ready(OLLAMA_URL):
        print("Error: Ollama is not running. Please start the Ollama service/container first.")
        sys.exit(1)
        
    success = True
    for model in MODELS_TO_PULL:
        if not pull_model(OLLAMA_URL, model):
            success = False
            
    if success:
        print("\nAll models pulled successfully!")
    else:
        print("\nSome models failed to pull.")
        sys.exit(1)

if __name__ == "__main__":
    main()
