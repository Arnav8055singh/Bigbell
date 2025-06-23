# sessions.py
async def get_session(db, phone):
    return await db.sessions.find_one({"phone": phone}) or {}

async def set_session(db, phone, session_data):
    await db.sessions.update_one(
        {"phone": phone},
        {"$set": session_data, "$setOnInsert": {"phone": phone}},
        upsert=True
    )




