import requests
import json
import sys

def check_ollama():
    print("Checking Ollama connection...")
    try:
        # Check if running
        base_resp = requests.get("http://localhost:11434/")
        if base_resp.status_code == 200:
            print("✅ Ollama is RUNNING.")
        else:
            print(f"⚠️  Ollama is running but returned {base_resp.status_code} at root.")
            
        # Check models
        print("\nChecking available models...")
        tags_resp = requests.get("http://localhost:11434/api/tags")
        if tags_resp.status_code == 200:
            models = tags_resp.json().get("models", [])
            if models:
                print("Installed models:")
                found_llama3 = False
                for m in models:
                    name = m.get("name")
                    print(f" - {name}")
                    if "llama3" in name:
                        found_llama3 = True
                
                if not found_llama3:
                    print("\n❌ 'llama3' NOT found. Please run: ollama pull llama3")
                else:
                    print("\n✅ 'llama3' is installed.")
            else:
                print("❌ No models installed. Please run: ollama pull llama3")
        else:
            print(f"❌ Failed to list models: {tags_resp.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Ollama at http://localhost:11434")
        print("Please ensure Ollama is installed and running.")

if __name__ == "__main__":
    check_ollama()
