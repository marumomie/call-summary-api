from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
import httpx, os

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

    # GPT-4oで要約
    summary_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": f"""
以下の通話内容を日本語で要約してください。

【出力形式】
タイトル：（通話相手や話題を一言で）
要点：
・（重要なポイント1）
・（重要なポイント2）
・（重要なポイント3）
TODO：（あれば記載、なければ「なし」）

【通話内容】
{input.text}
"""
        }]
    )

    summary_text = summary_response.choices[0].message.content

    # Adaloに保存
    async with httpx.AsyncClient() as http:
        await http.post(
            f"https://api.adalo.com/v0/apps/{ADALO_APP_ID}/collections/{ADALO_COLLECTION_ID}",
            headers={
                "Authorization": f"Bearer {ADALO_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "title": summary_text.split("\n")[0],
                "summary": summary_text,
                "transcript": input.text,
                "color": "yellow"
            }
        )

    return {
        "summary": summary_text
    }