from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
import httpx
import os

load_dotenv()

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ADALO_API_KEY = os.getenv("ADALO_API_KEY")
ADALO_APP_ID = os.getenv("ADALO_APP_ID")
ADALO_COLLECTION_ID = os.getenv("ADALO_COLLECTION_ID")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextInput(BaseModel):
    text: str

@app.get("/")
def root():
    return {"message": "APIが動いています！"}

@app.post("/summarize")
async def summarize(input: TextInput):
    prompt = "以下の通話内容を日本語で要約してください。タイトル、要点、TODOを含めてください。\n\n" + input.text
    summary_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    summary_text = summary_response.choices[0].message.content
    title = summary_text.split("\n")[0].strip()

    adalo_url = "https://api.adalo.com/v0/apps/" + ADALO_APP_ID + "/collections/" + ADALO_COLLECTION_ID
    adalo_headers = {
        "Authorization": "Bearer " + ADALO_API_KEY,
        "Content-Type": "application/json",
    }
    adalo_data = {
        "title": title,
        "summary": summary_text,
        "transcript": input.text,
        "color": "yellow"
    }

    async with httpx.AsyncClient() as http:
        response = await http.post(adalo_url, headers=adalo_headers, json=adalo_data)
        print("Adalo status:", response.status_code)
        print("Adalo body:", response.text)

    return {"summary": summary_text}