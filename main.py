from fastapi import FastAPI, Request, Response
from whatsapp_handler import handle_whatsapp_webhook
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
import uvicorn

load_dotenv()

app = FastAPI()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "bigbellsecret2025")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "Jenkins")

client = AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB_NAME]

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.json()
    return await handle_whatsapp_webhook(body, db)

@app.get("/webhook")
async def verify(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        challenge = params.get("hub.challenge")
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Invalid verification token", status_code=403)

@app.get("/")
def root():
    return {"message": "BigBell WhatsApp Bot is running!"}

# ✅ MAIN ENTRYPOINT FOR RAILWAY
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # use Railway's dynamic port
    uvicorn.run("main:app", host="0.0.0.0", port=port)
