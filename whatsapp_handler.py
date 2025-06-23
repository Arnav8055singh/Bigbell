import httpx
import os
import logging
import json
import traceback
import time

from sessions import get_session, set_session
from jenkins_handler import (
    get_all_jobs,
    get_jobs_by_customer,
    trigger_build,
    get_job_status,
    get_latest_build_number
)

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("PHONE_ID")
CUSTOMERS = ["goognu", "hiringgo"]

async def send_whatsapp_message(phone_id, token, payload):
    url = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            print(" [WHATSAPP STATUS]:", response.status_code)
            print(" [RESPONSE BODY]:", response.text)
            return response
    except Exception as ex:
        print("Unexpected error:", ex)
        traceback.print_exc()

def wait_for_latest_build_number(job_name, retries=5, delay=2):
    for _ in range(retries):
        build_number = get_latest_build_number(job_name)
        if build_number:
            return build_number
        time.sleep(delay)
    return None

async def handle_whatsapp_webhook(body, db):
    try:
        messages = body.get("entry", [])[0].get("changes", [])[0].get("value", {}).get("messages", [])
        if not messages:
            return {"status": "ok"}

        message = messages[0]
        phone = message["from"]

        # --- Extract message text ---
        text = ""
        if "interactive" in message:
            interactive = message["interactive"]
            if "button_reply" in interactive:
                text = interactive["button_reply"]["id"].lower().strip()
            elif "list_reply" in interactive:
                text = interactive["list_reply"]["id"].lower().strip()
        elif "button_reply" in message:
            text = message["button_reply"]["id"].lower().strip()
        elif "text" in message:
            text = message["text"]["body"].lower().strip()

        session = await get_session(db, phone)
        step = session.get("step")

        # Step 1: Initial greeting
        if text == "hi" or not step:
            await set_session(db, phone, {"step": "select_customer"})
            await send_whatsapp_message(PHONE_ID, WHATSAPP_TOKEN, {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": "Welcome to BigBell! Select Customer:"},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": "goognu", "title": "Goognu"}},
                            {"type": "reply", "reply": {"id": "hiringgo", "title": "HiringGo"}},
                            {"type": "reply", "reply": {"id": "custom", "title": "Customize Selection"}}
                        ]
                    }
                }
            })
            return {"status": "waiting for customer"}

        # Step 2: Customer selection
        if step == "select_customer":
            selected = text
            if selected in CUSTOMERS:
                jobs = get_jobs_by_customer(selected)
                if not jobs:
                    await send_whatsapp_message(PHONE_ID, WHATSAPP_TOKEN, {
                        "messaging_product": "whatsapp",
                        "to": phone,
                        "type": "text",
                        "text": {"body": f"No jobs found for {selected}. Type 'hi' to restart."}
                    })
                    return {"status": "no jobs"}
                await set_session(db, phone, {"step": "select_job", "customer": selected, "jobs": jobs})
                buttons = [{"type": "reply", "reply": {"id": job, "title": job}} for job in jobs[:3]]
                await send_whatsapp_message(PHONE_ID, WHATSAPP_TOKEN, {
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "interactive",
                    "interactive": {
                        "type": "button",
                        "body": {"text": "Select Job to Trigger"},
                        "action": {"buttons": buttons}
                    }
                })
                return {"status": "waiting for job"}
            elif selected == "custom":
                jobs = get_all_jobs()
                if not jobs:
                    await send_whatsapp_message(PHONE_ID, WHATSAPP_TOKEN, {
                        "messaging_product": "whatsapp",
                        "to": phone,
                        "type": "text",
                        "text": {"body": "No jobs found. Type 'hi' to restart."}
                    })
                    return {"status": "no jobs"}
                rows = [{"id": job, "title": job} for job in jobs[:10]]
                await set_session(db, phone, {"step": "select_job", "customer": "custom", "jobs": jobs})
                await send_whatsapp_message(PHONE_ID, WHATSAPP_TOKEN, {
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "interactive",
                    "interactive": {
                        "type": "list",
                        "header": {"type": "text", "text": "Select Jenkins Job"},
                        "body": {"text": "Choose a job to trigger or check status."},
                        "action": {
                            "button": "Show Jobs",
                            "sections": [{"title": "All Jenkins Jobs", "rows": rows}]
                        }
                    }
                })
                return {"status": "waiting for job"}
            else:
                await send_whatsapp_message(PHONE_ID, WHATSAPP_TOKEN, {
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {"body": "Invalid selection. Type 'hi' to restart."}
                })
                return {"status": "invalid selection"}

        # Step 3: Job selection
        if step == "select_job":
            job_name = text
            jobs = session.get("jobs", [])
            if job_name not in jobs:
                await send_whatsapp_message(PHONE_ID, WHATSAPP_TOKEN, {
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {"body": "Invalid job. Type 'hi' to restart."}
                })
                return {"status": "invalid job"}
            await set_session(db, phone, {"step": "job_action", "job_name": job_name})
            await send_whatsapp_message(PHONE_ID, WHATSAPP_TOKEN, {
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": f"Job: {job_name}\nChoose action:"},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": "trigger", "title": "Trigger Build"}},
                            {"type": "reply", "reply": {"id": "status", "title": "Check Status"}},
                            {"type": "reply", "reply": {"id": "terminate", "title": "Terminate Session"}}
                        ]
                    }
                }
            })
            return {"status": "waiting for action"}

        # Step 4: Job action
        if step == "job_action":
            job_name = session.get("job_name")

            if text == "trigger":
                triggered = trigger_build(job_name)

                if triggered:
                    build_number = wait_for_latest_build_number(job_name) or "N/A"
                    status = get_job_status(job_name) or "IN_PROGRESS"

                    await send_whatsapp_message(PHONE_ID, WHATSAPP_TOKEN, {
                        "messaging_product": "whatsapp",
                        "to": phone,
                        "type": "text",
                        "text": {
                            "body": (
                                f"✅ Job *'{job_name}'* triggered successfully!\n"
                                f"📦 *Build Number:* #{build_number}\n"
                                f"⏱️ *Status:* {status}\n\n"
                                f"Type *hi* to restart or choose another job."
                            )
                        }
                    })
                else:
                    await send_whatsapp_message(PHONE_ID, WHATSAPP_TOKEN, {
                        "messaging_product": "whatsapp",
                        "to": phone,
                        "type": "text",
                        "text": {"body": f"❌ Failed to trigger job '{job_name}'. Type 'hi' to try again."}
                    })

                await set_session(db, phone, {})
                return {"status": "triggered"}

            elif text == "status":
                status = get_job_status(job_name)
                await send_whatsapp_message(PHONE_ID, WHATSAPP_TOKEN, {
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {"body": f"📈 Job '{job_name}' status: {status}\nType 'hi' to restart."}
                })
                return {"status": "status"}

            elif text == "terminate":
                await send_whatsapp_message(PHONE_ID, WHATSAPP_TOKEN, {
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {"body": "🛑 Session terminated. Type 'hi' to start again."}
                })
                await set_session(db, phone, {})
                return {"status": "terminated"}

            else:
                await send_whatsapp_message(PHONE_ID, WHATSAPP_TOKEN, {
                    "messaging_product": "whatsapp",
                    "to": phone,
                    "type": "text",
                    "text": {"body": "Invalid action. Type 'hi' to restart."}
                })
                return {"status": "invalid action"}

        return {"status": "handled"}

    except Exception as ex:
        print("Error in handle_whatsapp_webhook:", ex)
        traceback.print_exc()
        return {"status": "error"}
