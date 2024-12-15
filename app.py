from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from twilio.rest import Client
from datetime import datetime
from supabase import create_client
import os
from dotenv import load_dotenv  # Import dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure Supabase credentials
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Ensure that the required credentials are available
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials are not set!")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Twilio credentials (use environment variables for production)
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

# Ensure Twilio credentials are set
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

    # Get current date and time (Supabase will handle the datetime type properly)
    message_body = f"FROM: {sender_name} \nDATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \nMESSAGE: {message}"

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
            "date": datetime.utcnow()  # UTC format datetime, let Supabase handle it
        }).execute()

        # Check if the insertion was successful
        if response.status_code == 201:
            return jsonify({"success": True, "message_sid": message_sent.sid, "conversation": message_sent.sid})
        else:
            return jsonify({"success": False, "error": "Failed to store message in Supabase"}), 500

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# Endpoint to receive replies from Twilio
@app.route("/receive-reply", methods=["POST"])
def receive_reply():
    from_number = request.form.get('From')
    body = request.form.get('Body')

    try:
        # Save the reply to Supabase
        response = supabase.table("messages").insert({
            "sender_name": from_number,
            "message_body": body,
            "date": datetime.utcnow(),  # UTC datetime
            "phone_number": from_number
        }).execute()

        # Check if the insertion was successful
        if response.status_code == 201:
            return "<Response></Response>"
        else:
            return "<Response><Message>Failed to save reply</Message></Response>"

    except Exception as e:
        return "<Response><Message>Failed to save reply</Message></Response>"

if __name__ == "__main__":
    app.run(debug=True)
