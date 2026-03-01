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

BUBBLE_API_KEY = os.getenv("BUBBLE_API_KEY")
BUBBLE_APP_ID = os.getenv("BUBBLE_APP_ID")

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

    bubble_url = "https://" + BUBBLE_APP_ID + ".bubbleapps.io/version-test/api/1.1/obj/callnote"
    bubble_headers = {
        "Authorization": "Bearer " + BUBBLE_API_KEY,
        "Content-Type": "application/json",
    }
    bubble_data = {
        "title": title,
        "summary": summary_text,
        "transcript": input.text,
        "color": "yellow"
    }

    async with httpx.AsyncClient() as http:
        response = await http.post(bubble_url, headers=bubble_headers, json=bubble_data)
        print("Bubble status:", response.status_code)
        print("Bubble body:", response.text)

    return {"summary": summary_text}