import os
import subprocess
import hmac
import hashlib
import logging

from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
PROJECT_PATH = os.getenv("PROJECT_PATH")

assert WEBHOOK_SECRET is not None, "Webhook Secret not set"
assert PROJECT_PATH is not None, "Project path not set"
assert os.path.exists(PROJECT_PATH), f"Project path {PROJECT_PATH} does not exist"


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return "OK", 200


@app.route("/deploy", methods=["POST"])
def deploy():
    app.logger.info(f"Deploy webhook triggered from {request.remote_addr}")
    assert WEBHOOK_SECRET is not None, "Webhook Secret not set"
    assert PROJECT_PATH is not None, "Project path not set"
    # Verify webhook signature (if using GitHub webhooks)
    signature = request.headers.get("X-Hub-Signature-256")
    if signature:
        expected = (
            "sha256="
            + hmac.new(
                WEBHOOK_SECRET.encode(), request.data, hashlib.sha256
            ).hexdigest()
        )
        if not hmac.compare_digest(expected, signature):
            return "Unauthorized", 401
    else:
        app.logger.warning("No signature provided. Aborting")
        return "Signature missing", 401

    # Run deployment commands
    try:
        app.logger.info(f"Running deployment in {PROJECT_PATH}")

        result = subprocess.run(
            ["git", "pull"],
            check=True,
            cwd=PROJECT_PATH,
            capture_output=True,
            text=True,
        )
        app.logger.info(f"Git pull: {result.stdout}")

        subprocess.run(["just", "build-prod"], check=True, cwd=PROJECT_PATH)
        app.logger.info("Build completed")

        subprocess.run(["just", "prod"], check=True, cwd=PROJECT_PATH)
        app.logger.info("Deployment successful")
        return "Deployment successful", 200
    except subprocess.CalledProcessError as e:
        app.logger.error(f"Deployment failed: {e}")
        return f"Deployment failed: {e}", 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return f"Error: {e}", 500


if __name__ == "__main__":
    print("Starting webhook server...")
    print(f"Project path: {PROJECT_PATH}")
    print(f"Secret configured: {'Yes' if WEBHOOK_SECRET else 'No'}")
    app.run(host="172.0.18.1", port=9000)
