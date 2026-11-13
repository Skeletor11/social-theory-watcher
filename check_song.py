#!/usr/bin/env python3
"""
WSTB Song Watcher (cloud edition)

Checks 88.9 WSTB's recently-played JSON feed for any Social Theory track and
emails + texts you when one airs. Runs on a schedule via GitHub Actions.

De-dup: 'state/last_seen.txt' holds the Unix timestamp of the newest play we've
already alerted on; it only advances (and is committed back) when there's a new
hit, so delayed or skipped scheduled runs never cause a miss or a repeat.

Env vars (set as GitHub Secrets):
  GMAIL_ADDRESS       the sending Gmail address
  GMAIL_APP_PASSWORD  16-char Google App Password (NOT the normal password)
  NOTIFY_EMAIL        where to email alerts (defaults to GMAIL_ADDRESS)
  NTFY_TOPIC          ntfy.sh topic to push phone alerts to (private random string)
  TEST_RUN            "true" to send a one-off test message and exit
"""
import os, json, ssl, smtplib, urllib.request
from email.message import EmailMessage
from pathlib import Path

ARTIST = "social theory"          # case-insensitive substring match
FEED   = "https://wp.rock889.com/nowplaying/nowplaying.php?range=1d&format=json"
STATE  = Path("state/last_seen.txt")

GMAIL    = os.environ["GMAIL_ADDRESS"]
APP_PW   = os.environ["GMAIL_APP_PASSWORD"]
EMAIL_TO = os.environ.get("NOTIFY_EMAIL", GMAIL).strip()
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
TEST     = os.environ.get("TEST_RUN", "").strip().lower() in ("1", "true", "yes")


def fetch():
    req = urllib.request.Request(FEED, headers={"User-Agent": "wstb-watcher/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def send(to_addr, subject, body):
    if not to_addr:
        return
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = GMAIL, to_addr, subject
    msg.set_content(body)
    ctx = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as s:
        s.starttls(context=ctx)
        s.login(GMAIL, APP_PW)
        s.send_message(msg)


def push(title, message, tags="radio"):
    """Send a phone push via ntfy.sh. Title must be ASCII (HTTP header)."""
    if not NTFY_TOPIC:
        return
    url = NTFY_TOPIC if NTFY_TOPIC.startswith("http") else f"https://ntfy.sh/{NTFY_TOPIC}"
    req = urllib.request.Request(
        url, data=message.encode("utf-8"), method="POST",
        headers={"Title": title, "Tags": tags})
    urllib.request.urlopen(req, timeout=30)


def alert(hit):
    # full email
    send(EMAIL_TO,
         f"Social Theory just played on 88.9 WSTB: {hit['title']}",
         ("Your song aired on WSTB (88.9 FM, Streetsboro OH)!\n\n"
          f"  Artist: {hit['artist']}\n"
          f"  Title:  {hit['title']}\n"
          f"  Album:  {hit.get('album','')}\n"
          f"  Time:   {hit['datetime']}\n\n"
          "Recently played: https://www.wstb.org/page/recently-played"))
    # phone push
    push("Social Theory on 88.9 WSTB", f"{hit['title']} - {hit['datetime']}")


def main():
    data = fetch()

    if TEST:
        latest = data[0]
        send(EMAIL_TO, "WSTB Song Watcher - test",
             ("Test OK - your cloud watcher is live.\n"
              f"Most recent song on WSTB right now: {latest['artist']} - {latest['title']} "
              f"({latest['datetime']}).\nYou'll be alerted whenever Social Theory airs."))
        push("WSTB watcher test", f"Watcher is live. Latest on WSTB: {latest['title']}",
             tags="white_check_mark")
        print("Test message sent.")
        return

    # First ever run: set a baseline so we only alert on FUTURE plays.
    if not STATE.exists():
        newest = max(int(x["timestamp"]) for x in data)
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(str(newest))
        print(f"Initialized baseline {newest}; no alerts on first run.")
        return

    last_seen = int((STATE.read_text().strip() or "0"))

    hits = sorted(
        (x for x in data
         if x.get("artist") and ARTIST in x["artist"].lower()
         and int(x["timestamp"]) > last_seen),
        key=lambda x: int(x["timestamp"]))

    if not hits:
        print(f"No match (scanned {len(data)} entries).")
        return

    for h in hits:
        alert(h)
        print(f"ALERTED: {h['datetime']}  {h['artist']} - {h['title']}")

    STATE.write_text(str(int(hits[-1]["timestamp"])))


if __name__ == "__main__":
    main()
