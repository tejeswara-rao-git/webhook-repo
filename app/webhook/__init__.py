from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# Connect to MongoDB (update URI if using MongoDB Atlas)
client = MongoClient("mongodb://localhost:27017/")
db = client['webhook_db']
collection = db['events']

@app.route('/webhook', methods=['POST'])
def github_webhook():
    data = request.json

    if not data:
        return jsonify({"status": "fail", "reason": "no data"}), 400

    event_type = request.headers.get('X-GitHub-Event')
    author = data.get("pusher", {}).get("name") if event_type == "push" else data.get("sender", {}).get("login")

    if event_type == "push":
        doc = {
            "author": author,
            "from_branch": None,
            "to_branch": data["ref"].split("/")[-1],
            "timestamp": datetime.utcnow().isoformat(),
            "action": "push"
        }

    elif event_type == "pull_request":
        doc = {
            "author": author,
            "from_branch": data["pull_request"]["head"]["ref"],
            "to_branch": data["pull_request"]["base"]["ref"],
            "timestamp": data["pull_request"]["created_at"],
            "action": "pull_request"
        }

    else:
        return jsonify({"status": "ignored", "reason": f"Unhandled event {event_type}"}), 200

    collection.insert_one(doc)
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)
