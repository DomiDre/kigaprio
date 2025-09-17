import os
import subprocess
import hmac
import hashlib

from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
assert WEBHOOK_SECRET is not None, "Webhook Secret not set"


@app.route("/deploy", methods=["POST"])
def deploy():
    # Verify webhook signature (if using GitHub webhooks)
    signature = request.headers.get("X-Hub-Signature-256")
    assert WEBHOOK_SECRET is not None, "Webhook Secret not set"
    if signature:
        expected = (
            "sha256="
            + hmac.new(
                WEBHOOK_SECRET.encode(), request.data, hashlib.sha256
            ).hexdigest()
        )
        if not hmac.compare_digest(expected, signature):
            return "Unauthorized", 401

    # Run deployment commands
    try:
        subprocess.run(["git", "pull"], check=True, cwd="/path/to/your/project")
        subprocess.run(["just", "build-prod"], check=True, cwd="/path/to/your/project")
        subprocess.run(["just", "prod"], check=True, cwd="/path/to/your/project")
        return "Deployment successful", 200
    except subprocess.CalledProcessError as e:
        return f"Deployment failed: {e}", 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9000)
