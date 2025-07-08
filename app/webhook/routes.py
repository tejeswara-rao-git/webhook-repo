from pymongo import MongoClient
from datetime import datetime

client = MongoClient("mongodb://localhost:27017/")
db = client["webhook_db"]
collection = db["events"]

######

from flask import Blueprint, jsonify, request

webhook = Blueprint('Webhook', __name__, url_prefix='/webhook')


@webhook.route('/events', methods=["GET"])
def get_events():
    events = list(collection.find({}, {"_id": 0}))  # exclude MongoDB internal _id
    return jsonify(events)


@webhook.route('/receiver', methods=["POST"])
def receiver():
    data = request.json
    event_type = request.headers.get("X-GitHub-Event", "unknown")

    author = data.get("pusher", {}).get("name") or data.get("sender", {}).get("login", "unknown")
    timestamp = datetime.utcnow().isoformat()

    event = {
        "author": author,
        "timestamp": timestamp,
        "action": event_type,
        "from_branch": None,
        "to_branch": None
    }

    if event_type == "push":
        event["to_branch"] = data.get("ref", "").split("/")[-1]

    elif event_type == "pull_request":
        event["from_branch"] = data.get("pull_request", {}).get("head", {}).get("ref")
        event["to_branch"] = data.get("pull_request", {}).get("base", {}).get("ref")
        event["timestamp"] = data.get("pull_request", {}).get("created_at")

    # Debug print to console
    print("Saving event to MongoDB:", event)

    collection.insert_one(event)
    return jsonify({"status": "success"}), 200

  
@webhook.route('/dashboard')
def dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Webhook Events Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 2rem; }
            h1 { color: #2c3e50; }
            .event {
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 1rem;
                margin-bottom: 1rem;
                background: #f9f9f9;
            }
        </style>
    </head>
    <body>
        <h1>Webhook Events</h1>
        <div id="events"></div>

        <script>
            async function fetchEvents() {
                const response = await fetch('/webhook/events');
                const data = await response.json();

                const container = document.getElementById('events');
                container.innerHTML = '';

                data.reverse().forEach(event => {
                    const div = document.createElement('div');
                    div.className = 'event';
                    div.innerHTML = `
                        <strong>Author:</strong> ${event.author}<br>
                        <strong>Action:</strong> ${event.action}<br>
                        <strong>From:</strong> ${event.from_branch || '-'} → <strong>To:</strong> ${event.to_branch || '-'}<br>
                        <strong>Timestamp:</strong> ${event.timestamp}
                    `;
                    container.appendChild(div);
                });
            }

            fetchEvents();
            setInterval(fetchEvents, 15000);
        </script>
    </body>
    </html>
    """
