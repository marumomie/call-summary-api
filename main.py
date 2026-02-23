from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv
import httpx
import tempfile, os

load_dotenv()

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "APIが動いています！"}

@app.post("/summarize")
async def summarize(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".m4a"
    ) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    with open(tmp_path, "rb") as audio:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio,
            language="ja"
        )

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
{transcript.text}
"""
        }]
    )

    os.unlink(tmp_path)

    summary_text = summary_response.choices[0].message.content

    # Supabaseに保存
    async with httpx.AsyncClient() as http:
        await http.post(
            f"{SUPABASE_URL}/rest/v1/call_notes",
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "title": summary_text.split("\n")[0],
                "summary": summary_text,
                "transcript": transcript.text,
                "color": "yellow"
            }
        )

    return {
        "transcript": transcript.text,
        "summary": summary_text
    }