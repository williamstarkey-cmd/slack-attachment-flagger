"""
Polling version of the attachment-flagger bot.

Meant to be run on a schedule (GitHub Actions cron). For each channel listed
in POLL_CHANNEL_IDS, fetches recent messages and posts a threaded reply on
any forwarded email that has attachments and hasn't already been replied to
by this bot.

Env vars:
  SLACK_BOT_TOKEN   the xoxb-... token (needs channels:history, groups:history, chat:write)
  POLL_CHANNEL_IDS  comma-separated list of channel IDs (e.g. "C0BPAP96P7V,C012345678")
"""

import logging
import os
import sys
import time

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


REPLY_TEXT = (
    ":paperclip: *Attachment detected* — check for OM / preliminary OM / "
    "pricing supplement / term sheet and take any action needed."
)

# 15-min lookback covers the 10-min cron interval plus GitHub Actions' schedule drift.
LOOKBACK_SECONDS = 60 * 15

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def iter_email_files(msg):
    for f in msg.get("files") or []:
        if f.get("filetype") == "email":
            yield f
    for att in msg.get("attachments") or []:
        for f in att.get("files") or []:
            if f.get("filetype") == "email":
                yield f


def email_has_attachments(email_file):
    if email_file.get("original_attachment_count"):
        return True
    return bool(email_file.get("attachments"))


def bot_already_replied(client, channel, ts, bot_user_id):
    try:
        replies = client.conversations_replies(channel=channel, ts=ts, limit=200)
    except SlackApiError as e:
        log.warning("failed to read replies for %s/%s: %s", channel, ts, e.response.get("error"))
        # Fail safe: assume yes so we don't double-post.
        return True
    for reply in replies.get("messages", [])[1:]:  # skip parent message
        if reply.get("user") == bot_user_id:
            return True
    return False


def main():
    token = os.environ["SLACK_BOT_TOKEN"]
    raw_ids = os.environ.get("POLL_CHANNEL_IDS", "")
    channel_ids = [c.strip() for c in raw_ids.split(",") if c.strip()]
    if not channel_ids:
        log.error("POLL_CHANNEL_IDS is empty — set it to a comma-separated list of channel IDs.")
        sys.exit(1)

    client = WebClient(token=token)
    bot_user_id = client.auth_test()["user_id"]
    oldest = str(time.time() - LOOKBACK_SECONDS)

    for channel in channel_ids:
        log.info("polling channel %s", channel)
        try:
            history = client.conversations_history(channel=channel, oldest=oldest, limit=200)
        except SlackApiError as e:
            log.error("history failed for %s: %s", channel, e.response.get("error"))
            continue

        for msg in history.get("messages", []):
            for email_file in iter_email_files(msg):
                if email_has_attachments(email_file):
                    if not bot_already_replied(client, channel, msg["ts"], bot_user_id):
                        try:
                            client.chat_postMessage(
                                channel=channel,
                                thread_ts=msg["ts"],
                                text=REPLY_TEXT,
                            )
                            log.info("flagged ts=%s channel=%s", msg["ts"], channel)
                        except SlackApiError as e:
                            log.error(
                                "post failed for %s/%s: %s",
                                channel, msg["ts"], e.response.get("error"),
                            )
                    break


if __name__ == "__main__":
    main()
