"""
Slack bot: flags forwarded bank emails that have attachments.

Listens on `message` events in whichever channels the bot is invited to.
When it sees a forwarded email (a file with filetype="email") that carries
one or more original attachments, it posts a threaded reply asking the team
to check the doc type.
"""

import logging
import os

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()


REPLY_TEXT = (
    ":paperclip: *Attachment detected* — check for OM / preliminary OM / "
    "pricing supplement / term sheet and take any action needed."
)

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = App(token=os.environ["SLACK_BOT_TOKEN"])


def iter_email_files(event):
    """Yield every file dict on this message whose filetype is "email".

    The team forwards emails via Slack's native "share" action, which lands
    the email file inside message.attachments[*].files. A direct upload/drag
    would land it in message.files. Check both.
    """
    for f in event.get("files") or []:
        if f.get("filetype") == "email":
            yield f
    for att in event.get("attachments") or []:
        for f in att.get("files") or []:
            if f.get("filetype") == "email":
                yield f


def email_has_attachments(email_file):
    if email_file.get("original_attachment_count"):
        return True
    return bool(email_file.get("attachments"))


@app.event("message")
def on_message(event, client, logger):
    import json
    logger.info("EVENT RECEIVED subtype=%s ts=%s", event.get("subtype"), event.get("ts"))
    logger.info("FULL EVENT:\n%s", json.dumps(event, indent=2)[:4000])

    if event.get("subtype") in {"message_changed", "message_deleted", "channel_join", "channel_leave"}:
        logger.info("skipping subtype=%s", event.get("subtype"))
        return

    found_any_email = False
    for email_file in iter_email_files(event):
        found_any_email = True
        logger.info(
            "email file id=%s original_attachment_count=%s attachments_len=%s",
            email_file.get("id"),
            email_file.get("original_attachment_count"),
            len(email_file.get("attachments") or []),
        )
        if email_has_attachments(email_file):
            client.chat_postMessage(
                channel=event["channel"],
                thread_ts=event["ts"],
                text=REPLY_TEXT,
            )
            logger.info("flagged ts=%s channel=%s", event["ts"], event["channel"])
            return
    if not found_any_email:
        logger.info("no email files found on this message")


if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
