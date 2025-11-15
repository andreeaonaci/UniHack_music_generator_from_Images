import os
import openai

# Configure OpenAI to use Azure OpenAI
openai.api_type = "azure"
openai.api_base = os.environ["AZURE_OPENAI_ENDPOINT"]  # e.g. "https://<your-resource>.openai.azure.com/"
openai.api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-06-01")  # or your Azure OpenAI API version
openai.api_key = os.environ["AZURE_OPENAI_KEY"]

# Example call
response = openai.ChatCompletion.create(
    deployment_id=os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"],
    messages=[{"role": "user", "content": "Hello, world!"}],
    max_tokens=50
)
print(response.choices[0].message.content)
