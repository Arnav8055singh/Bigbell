from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["bigbell_db"]
messages = db["messages"]

def save_message_to_db(sender, user_msg, bot_reply):
    messages.insert_one({
        "sender": sender,
        "message": user_msg,
        "reply": bot_reply
    })
