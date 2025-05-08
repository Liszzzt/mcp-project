import httpx

result = httpx.post("http://localhost:11434/api/chat", json={
    "model": "llama3.1",
    "messages": [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm fine, thank you! How can I assist you today?"}
    ],
    "stream": False,
    "tools": []
})

print(result.json())