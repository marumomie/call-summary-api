from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI, OpenAIError
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator
import httpx
import os
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("テキストが空です")
        return v.strip()


async def save_to_adalo(title: str, summary_text: str, transcript: str):
    adalo_url = f"https://api.adalo.com/v0/apps/{ADALO_APP_ID}/collections/{ADALO_COLLECTION_ID}"
    adalo_headers = {
        "Authorization": f"Bearer {ADALO_API_KEY}",
        "Content-Type": "application/json",
    }
    adalo_data = {
        "title": title,
        "summary": summary_text,
        "transcript": transcript,
        "color": "yellow"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            response = await http.post(adalo_url, headers=adalo_headers, json=adalo_data)
            logger.info(f"Adalo status: {response.status_code}")
            logger.info(f"Adalo body: {response.text}")
            if response.status_code not in (200, 201):
                logger.error(f"Adalo保存失敗 (status: {response.status_code}): {response.text}")
    except httpx.TimeoutException:
        logger.error("Adalo APIタイムアウト")
    except httpx.RequestError as e:
        logger.error(f"Adalo API接続エラー: {e}")


async def summarize_text(text: str):
    prompt = "以下の通話内容を日本語で要約してください。タイトル、要点、TODOを含めてください。マークダウン記号（**、##など）は使わず、プレーンテキストで出力してください。\n\n" + text
    summary_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    summary_text = summary_response.choices[0].message.content
    title = summary_text.split("\n")[0].strip() or "タイトルなし"
    return title, summary_text


async def process_in_background(text: str):
    try:
        logger.info("バックグラウンド処理開始")
        title, summary_text = await summarize_text(text)
        await save_to_adalo(title, summary_text, text)
        logger.info("バックグラウンド処理完了")
    except Exception as e:
        logger.error(f"バックグラウンド処理エラー: {e}")


@app.get("/")
def root():
    return {"message": "APIが動いています！"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/summarize")
async def summarize(input: TextInput, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_in_background, input.text)
    return {"status": "受け取りました。バックグラウンドで処理中です。"}


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not file.filename.endswith((".m4a", ".mp3", ".wav", ".mp4", ".mpeg", ".webm")):
        raise HTTPException(status_code=400, detail="対応していないファイル形式です")

    try:
        audio_bytes = await file.read()
        transcript_response = client.audio.transcriptions.create(
            model="whisper-1",
            file=(file.filename, audio_bytes, file.content_type),
        )
        transcript_text = transcript_response.text
        logger.info(f"文字起こし完了: {transcript_text[:50]}...")
    except OpenAIError as e:
        logger.error(f"Whisper APIエラー: {e}")
        raise HTTPException(status_code=502, detail=f"文字起こしエラー: {str(e)}")

    try:
        title, summary_text = await summarize_text(transcript_text)
    except OpenAIError as e:
        logger.error(f"OpenAI APIエラー: {e}")
        raise HTTPException(status_code=502, detail=f"要約エラー: {str(e)}")

    await save_to_adalo(title, summary_text, transcript_text)

    return {
        "transcript": transcript_text,
        "summary": summary_text
    }


@app.post("/transcribe-url")
async def transcribe_url(input: TextInput):
    try:
        async with httpx.AsyncClient(timeout=30.0, verify=False) as http:
            response = await http.get(input.text, follow_redirects=True)
            audio_bytes = response.content
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"音声ファイルの取得に失敗: {str(e)}")

    try:
        transcript_response = client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.m4a", audio_bytes, "audio/m4a"),
        )
        transcript_text = transcript_response.text
    except OpenAIError as e:
        raise HTTPException(status_code=502, detail=f"文字起こしエラー: {str(e)}")

    try:
        title, summary_text = await summarize_text(transcript_text)
    except OpenAIError as e:
        raise HTTPException(status_code=502, detail=f"要約エラー: {str(e)}")

    await save_to_adalo(title, summary_text, transcript_text)

    return {
        "transcript": transcript_text,
        "summary": summary_text
    }
