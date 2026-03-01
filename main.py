from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
import httpx, os

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
    summary_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": "以下の通話内容を日本語で要約してください。\n\n【出力形式】\nタイトル：（通話相手や話題を一言で）\n要点：\n・（重要なポイント1）\n・（重要なポイント2）\nTODO：（あれば記載、なければ「なし」）\n\n【通話内容】\n" + input.text
        }]
    )
    summary_text = summary_response.choices[0].message.content
    title = summary_text.split("\n")[0].replace("タイトル：", "").strip()

    async with httpx.AsyncClient() as http:
        response = await http.post(
            "http