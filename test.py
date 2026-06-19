import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=key)

try:
    # Yeh command Groq ke saare active models ki list nikalegi
    models = client.models.list()
    print("====================================")
    print("Groq par is waqt yeh models chal rahe hain:")
    for model in models.data:
        print(f"- {model.id}")
    print("====================================")
except Exception as e:
    print(f"Error: {e}")