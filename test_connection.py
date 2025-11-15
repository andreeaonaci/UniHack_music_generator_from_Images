import requests

response = requests.post(
    "http://localhost:5022/api/trivia/generate",
    json={
        "monumentName": "Turnul Eiffel",
        "description": "situat în Paris"
    }
)

print(response.status_code)
print(response.text)
