"""
Inspect a Slack forwarded-email to see exactly what the API returns.

Usage:
    export SLACK_BOT_TOKEN=xoxb-...
    python inspect_slack_email.py <link>

<link> can be either:
  * A file permalink (from right-clicking the blue email card):
      https://9fin.slack.com/files/UXXX/F0BPP1W1QMA/...
  * A message permalink (from right-clicking the message):
      https://9fin.slack.com/archives/C0123ABCD/p1723456789012345

The script prints the file record (and the surrounding message, if given a
message link) and lists the nested attachments Slack sees.
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request


SLACK_API = "https://slack.com/api"


def slack_get(method: str, params: dict) -> dict:
    token = os.environ["SLACK_BOT_TOKEN"]
    url = f"{SLACK_API}/{method}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    if not data.get("ok"):
        raise RuntimeError(f"{method} failed: {data}")
    return data


def parse_link(link: str) -> dict:
    m = re.search(r"/files/[A-Z0-9]+/(F[A-Z0-9]+)", link)
    if m:
        return {"kind": "file", "file_id": m.group(1)}
    m = re.search(r"/archives/([A-Z0-9]+)/p(\d+)", link)
    if m:
        raw_ts = m.group(2)
        return {"kind": "message", "channel": m.group(1), "ts": f"{raw_ts[:-6]}.{raw_ts[-6:]}"}
    raise ValueError(f"Not a Slack file or message permalink: {link}")


def dump_file(file_id: str) -> None:
    print(f"\n=== files.info for {file_id} ===")
    info = slack_get("files.info", {"file": file_id})
    file_obj = info.get("file", {})
    print(json.dumps(file_obj, indent=2))
    print(f"\n-> filetype={file_obj.get('filetype')!r}")
    atts = file_obj.get("attachments") or []
    print(f"-> {len(atts)} nested attachment(s)")
    for a in atts:
        print(f"   - name={a.get('filename') or a.get('name')!r} mimetype={a.get('mimetype')}")


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    parsed = parse_link(sys.argv[1])

    if parsed["kind"] == "file":
        dump_file(parsed["file_id"])
        return

    channel, ts = parsed["channel"], parsed["ts"]
    print(f"channel={channel} ts={ts}\n")
    history = slack_get(
        "conversations.history",
        {"channel": channel, "latest": ts, "inclusive": "true", "limit": 1},
    )
    messages = history.get("messages", [])
    if not messages:
        print("No message found. Is the bot in this channel?")
        sys.exit(1)
    msg = messages[0]
    print("=== message ===")
    print(json.dumps(msg, indent=2))
    for f in msg.get("files", []) or []:
        dump_file(f["id"])


if __name__ == "__main__":
    main()
