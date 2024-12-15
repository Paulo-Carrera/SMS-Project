from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from twilio.rest import Client
from datetime import datetime
from supabase import create_client
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure Supabase credentials
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Ensure Supabase credentials are available
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials are not set!")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Twilio credentials
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

# Ensure Twilio credentials are available
if not ACCOUNT_SID or not AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
    raise ValueError("Twilio credentials are not set!")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Serve the index.html file
@app.route("/")
def home():
    return render_template("index.html")

# Endpoint to send SMS
@app.route("/send-sms", methods=["POST"])
def send_sms():
    data = request.json
    phone_number = data.get("phone_number")
    sender_name = data.get("sender_name")
    message = data.get("message")

    if not sender_name or not message:
        return jsonify({"success": False, "error": "Sender name and message are required!"}), 400

    # Get current date and time as a string
    message_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    message_body = f"FROM: {sender_name} \nDATE: {message_date} \nMESSAGE: {message}"

    try:
        # Send the message using Twilio API
        message_sent = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )

        # Store the sent message in Supabase
        response = supabase.table("messages").insert({
            "sender_name": sender_name,
            "phone_number": phone_number,
            "message_body": message_body,
            "date": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')  # Save datetime as a string
        }).execute()

        # Check if the insertion was successful
        if response.data:  # Check if the response contains data (success)
            return jsonify({
                "success": True,
                "message_sid": message_sent.sid,
                "conversation": message_sent.sid
            })
        else:
            return jsonify({"success": False, "error": response.error}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# Endpoint to retrieve conversations
@app.route("/conversations")
def conversations():
    try:
        # Fetch messages from Supabase or your database
        response = supabase.table("messages").select("*").execute()
        if response.status_code != 200:
            raise ValueError("Error fetching messages from Supabase")
        messages = response.data if response.data else []
    except Exception as e:
        print(f"Error: {e}")
        messages = []
    return render_template("conversations.html", messages=messages)


if __name__ == "__main__":
    app.run(debug=True)
