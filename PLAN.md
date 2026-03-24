# Discord Invite Bot — Plan

## Context

AI Coding Eesti Discord server (19 members, 94% engagement) is growing via invite-only strategy. Need a bot so any member can generate tracked, single-use invite links via `/invite` slash command, with generation logged in an `#invite-log` channel.

## Architecture

**Slash-command-only HTTP bot** — no WebSocket gateway. Discord sends HTTP POST to the bot's URL when someone types `/invite`. Bot responds, creates the invite, logs it. Stateless.

- **Language:** Python (discord-interactions library for slash commands, no discord.py needed)
- **Repo:** `~/Work/ai-coding-bot/` (new standalone repo)
- **Hosting:** Cloud Run (GCP, min-instances=0, existing closaria project)
- **Tracking:** Log invite generation only (not join tracking)

## Bot Behavior

1. Member types `/invite` in `#invite` channel (the only channel where the command works)
2. Bot creates a single-use Discord invite to `#welcome-and-rules`, expires in 7 days
3. Bot responds **ephemerally** (only visible to the invoker): "Here's your invite link: https://discord.gg/abc123 (single-use, expires in 7 days)"
4. Bot posts a visible message in `#invite` itself: "**Maido** generated an invite (3rd this month)" — this doubles as the invite log, visible to all members

## Files

```
ai-coding-bot/
├── bot.py              # Flask app handling Discord interactions endpoint
├── requirements.txt    # flask, discord-interactions, requests
├── Dockerfile          # Python slim, gunicorn
├── register_commands.py # One-time script to register /invite slash command
└── .env.example        # DISCORD_BOT_TOKEN, DISCORD_APP_ID, DISCORD_PUBLIC_KEY, INVITE_CHANNEL_ID, WELCOME_CHANNEL_ID, GUILD_ID
```

## Implementation Steps

### 1. Project setup
- `git init`
- Create `requirements.txt`: `flask`, `discord-interactions`, `gunicorn`, `requests`
- Create `.env.example` with required vars
- Create `.gitignore` (`.env`, `__pycache__/`, `*.pyc`)

### 2. bot.py (~80 lines)
- Flask app with single POST endpoint `/interactions`
- Verify Discord request signature (discord-interactions library handles this)
- Handle `PING` (required by Discord)
- Handle `/invite` command:
  - Extract invoking user info from interaction payload
  - Call Discord API: `POST /channels/{WELCOME_CHANNEL_ID}/invites` with `max_uses=1, max_age=604800` (7 days), `unique=true`
  - Check that interaction came from `INVITE_CHANNEL_ID` — if not, return ephemeral error "Use this command in #invite"
  - Call Discord API: `POST /channels/{INVITE_CHANNEL_ID}/messages` to post visible log message in #invite
  - Return ephemeral response with the invite URL

### 3. register_commands.py (~20 lines)
- One-time script to register the `/invite` slash command with Discord
- `PUT /applications/{APP_ID}/guilds/{GUILD_ID}/commands` with command definition
- Run once locally: `python register_commands.py`

### 4. Dockerfile (~10 lines)
- `python:3.13-slim`, install deps, run gunicorn on `$PORT`

### 5. Discord setup
- In Discord Developer Portal: set **Interactions Endpoint URL** to Cloud Run URL (e.g., `https://ai-coding-bot-xxxxx.europe-north1.run.app/interactions`)
- Bot permissions needed: `Create Instant Invite`, `Send Messages`, `View Channels`
- Create `#invite` channel in Discord (private initially — only you + bot can see it, for testing. Make public when ready)

### 6. Deploy to Cloud Run
- `gcloud run deploy ai-coding-bot --source . --region europe-north1 --project closaria-fb517 --min-instances 0 --max-instances 1 --allow-unauthenticated`
- Set env vars via `--set-env-vars` or Secret Manager
- Cold start is fine — slash commands have a 3-second response window, Flask + gunicorn cold starts in ~1s

## Verification

1. Run locally with `flask run` + ngrok for testing
2. Type `/invite` in `#invite` → get ephemeral invite link
3. Check `#invite` → see visible log message
4. Type `/invite` in `#general` → get ephemeral error
5. Open invite link in incognito → verify it works and is single-use
6. Use invite, try again → verify it's expired
