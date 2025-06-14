from fastapi import FastAPI, Request
import json

app = FastAPI()

VERIFY_TOKEN = ""

@app.get("/webhook")
async def verify(request: Request):
    params = dict(request.query_params)
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params["hub.challenge"])
    return "Invalid verification token"

@app.post("/webhook")
async def incoming_message(request: Request):
    data = await request.json()
    print(json.dumps(data, indent=2))

    # Process message
    try:
        msg_body = data['entry'][0]['changes'][0]['value']['messages'][0]['text']['body']
        phone_number = data['entry'][0]['changes'][0]['value']['messages'][0]['from']
        print(f"Received: {msg_body} from {phone_number}")
    except:
        pass

    return {"status": "received"}
