import os
import requests

APP_ID = os.environ["DISCORD_APP_ID"]
GUILD_ID = os.environ["GUILD_ID"]
BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]

url = f"https://discord.com/api/v10/applications/{APP_ID}/guilds/{GUILD_ID}/commands"

commands = [
    {
        "name": "invite",
        "description": "Generate a single-use invite link",
        "type": 1,
    }
]

resp = requests.put(url, json=commands, headers={"Authorization": f"Bot {BOT_TOKEN}"})
resp.raise_for_status()
print(f"Registered commands: {resp.json()}")
