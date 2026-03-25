import os
import threading
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request
from discord_interactions import InteractionResponseType, InteractionType, verify_key_decorator

app = Flask(__name__)

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
APP_ID = os.environ["DISCORD_APP_ID"]
PUBLIC_KEY = os.environ["DISCORD_PUBLIC_KEY"]
INVITE_CHANNEL_ID = os.environ["INVITE_CHANNEL_ID"]
WELCOME_CHANNEL_ID = os.environ["WELCOME_CHANNEL_ID"]

DISCORD_API = "https://discord.com/api/v10"
HEADERS = {"Authorization": f"Bot {BOT_TOKEN}"}


def edit_followup(interaction_token, content):
    requests.patch(
        f"{DISCORD_API}/webhooks/{APP_ID}/{interaction_token}/messages/@original",
        json={"content": content},
    )


def invite_already_generated_today():
    resp = requests.get(f"{DISCORD_API}/channels/{INVITE_CHANNEL_ID}/messages?limit=10", headers=HEADERS)
    resp.raise_for_status()
    today = datetime.now(timezone.utc).date()
    for msg in resp.json():
        if msg["author"]["id"] == APP_ID and msg["timestamp"][:10] == str(today):
            return True
    return False


def create_invite():
    resp = requests.post(
        f"{DISCORD_API}/channels/{WELCOME_CHANNEL_ID}/invites",
        json={"max_uses": 1, "max_age": 86400, "unique": True},
        headers=HEADERS,
    )
    resp.raise_for_status()
    return resp.json()["code"]


def post_log_message(username, channel_id):
    resp = requests.get(f"{DISCORD_API}/channels/{channel_id}/messages?limit=100", headers=HEADERS)
    resp.raise_for_status()
    now = datetime.now(timezone.utc)
    month_count = 0
    for msg in resp.json():
        if (
            msg["author"]["id"] == APP_ID
            and msg["timestamp"][:7] == now.strftime("%Y-%m")
        ):
            month_count += 1

    ordinal = month_count + 1
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(ordinal if ordinal < 20 else ordinal % 10, "th")

    requests.post(
        f"{DISCORD_API}/channels/{channel_id}/messages",
        json={"content": f"**{username}** generated an invite ({ordinal}{suffix} this month)"},
        headers=HEADERS,
    )


def handle_invite(interaction):
    channel_id = interaction["channel_id"]
    token = interaction["token"]

    if channel_id != INVITE_CHANNEL_ID:
        edit_followup(token, "Use this command in #invite")
        return

    if invite_already_generated_today():
        edit_followup(token, "An invite was already generated today. Try again tomorrow!")
        return

    code = create_invite()
    username = interaction["member"]["user"]["global_name"] or interaction["member"]["user"]["username"]
    post_log_message(username, channel_id)
    edit_followup(token, f"Here's your invite link: https://discord.gg/{code} (single-use, expires in 24h)")


@app.route("/interactions", methods=["POST"])
@verify_key_decorator(PUBLIC_KEY)
def interactions():
    interaction = request.json

    if interaction["type"] == InteractionType.PING:
        return jsonify({"type": InteractionResponseType.PONG})

    if interaction["type"] == InteractionType.APPLICATION_COMMAND and interaction["data"]["name"] == "invite":
        threading.Thread(target=handle_invite, args=(interaction,)).start()
        return jsonify({"type": 5, "data": {"flags": 64}})

    return jsonify({"type": InteractionResponseType.PONG})
