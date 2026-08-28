# Slack Attachment Bot

Watches the three destination channels and posts a threaded reply whenever a forwarded bank email has one or more attachments, prompting the team to check for an OM / preliminary OM / pricing supplement / term sheet.

## How it works

- Uses **Socket Mode** — the bot opens an outbound WebSocket to Slack, so no public URL, firewall change, or SSL certificate is needed. Runs anywhere Python can run.
- Subscribes to `message` events. For each message it looks in both `message.files` and `message.attachments[].files` for a file with `filetype == "email"`. If that email has one or more attachments (`original_attachment_count > 0`), it replies in-thread.

## One-time Slack app setup

1. Go to <https://api.slack.com/apps> → **Create New App** → **From scratch**.
2. Name it something like `attachment-flagger` and pick your workspace.
3. In **Socket Mode** → toggle on. Generate an **App-Level Token** with the `connections:write` scope. Save it — it starts with `xapp-`.
4. In **OAuth & Permissions** → **Bot Token Scopes**, add:
   - `channels:history`
   - `chat:write`
5. In **Event Subscriptions** → toggle on → under **Subscribe to bot events**, add:
   - `message.channels`
6. Click **Install to Workspace**. Copy the **Bot User OAuth Token** — starts with `xoxb-`.
7. In each of the three destination channels, run `/invite @attachment-flagger` (or whatever you named it).

## Run locally to test

```bash
cd ~/Desktop/Claude
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export SLACK_BOT_TOKEN=xoxb-...      # from step 6
export SLACK_APP_TOKEN=xapp-...      # from step 3

python3 slack_attachment_bot.py
```

You should see log output like `INFO … connected to Slack`. Now forward a bank email into one of the channels the bot is in — it should reply in-thread within a second or two.

While your laptop is running the process, the bot is live. When you close the laptop it stops — that's what the hosting decision is for.

## Deploying so it runs 24/7

Any of these will work. Easiest → most flexible:

- **Render.com** background worker. Point it at a Git repo containing these files, set the start command to `python3 slack_attachment_bot.py`, and add `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` as environment variables in the dashboard. Starter plan is ~$7/month; the free tier sleeps and will miss events.
- **Fly.io** or **Railway** — same idea, similar cost, slightly more CLI-driven.
- **Your company's existing Python-hosting setup** (if 9fin runs one). Hand over the three files plus the two tokens and ask them to run it as a long-lived process.

Whatever you pick, the deploy-time contract is: **run `python3 slack_attachment_bot.py` with `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` in the environment.** That's it — no ports, no ingress, no domain.

## Tweaking the reply text

Edit `REPLY_TEXT` at the top of `slack_attachment_bot.py`. `:paperclip:` renders as 📎; you can use any Slack emoji. `*bold*` and `_italic_` work.

## Files

- `slack_attachment_bot.py` — the bot
- `requirements.txt` — one dependency (`slack-bolt`)
- `inspect_slack_email.py` — the throwaway inspection script from earlier; not needed at runtime
