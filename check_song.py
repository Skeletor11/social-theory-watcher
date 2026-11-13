#!/usr/bin/env python3
"""
Social Theory airplay watcher (cloud edition)

Checks one or more radio stations' recently-played feeds for any Social Theory
track and emails + pushes (ntfy) when one airs. Runs on a schedule via GitHub
Actions.

Each station in STATIONS declares its feed URL and which JSON fields hold the
artist, title, timestamp, and (optionally) a human time string -- so stations
with different feed formats are handled by the same code. Per-station state
files in state/ hold the newest play already alerted on; they only advance (and
are committed back by the workflow), so delayed/skipped runs never miss or
repeat.

Env vars (GitHub Secrets):
  GMAIL_ADDRESS       sending Gmail address
  GMAIL_APP_PASSWORD  16-char Google App Password (NOT the normal password)
  NOTIFY_EMAIL        where to email alerts (defaults to GMAIL_ADDRESS)
  NTFY_TOPIC          ntfy.sh topic to push phone alerts to (private random string)
  TEST_RUN            "true" to send a one-off test message and exit
"""
import os, json, ssl, smtplib, urllib.request
from email.message import EmailMessage
from pathlib import Path

ARTIST = "social theory"          # case-insensitive substring match

STATIONS = [
    {
        "name": "88.9 WSTB",
        "feed": "https://wp.rock889.com/nowplaying/nowplaying.php?range=1d&format=json",
        "artist_key": "artist", "title_key": "title",
        "ts_key": "timestamp", "time_key": "datetime",
        "state": "state/last_seen.txt",
    },
    {
        "name": "98.9 Magic FM",
        "feed": "https://socast-public.s3.amazonaws.com/player/lp_3326_3126.js",
        "artist_key": "artist_name", "title_key": "song_name",
        "ts_key": "last_played", "time_key": "locale_time",
        "state": "state/last_seen_magic.txt",
    },
]

GMAIL      = os.environ["GMAIL_ADDRESS"]
APP_PW     = os.environ["GMAIL_APP_PASSWORD"]
EMAIL_TO   = os.environ.get("NOTIFY_EMAIL", GMAIL).strip()
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
TEST       = os.environ.get("TEST_RUN", "").strip().lower() in ("1", "true", "yes")


def fetch_json(url):
    """Fetch JSON, tolerating a JSONP wrapper like callbackName( ... );"""
    req = urllib.request.Request(url, headers={"User-Agent": "song-watcher/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        text = r.read().decode("utf-8", "replace").strip()
    if not text.startswith(("[", "{")):          # strip JSONP wrapper
        i, j = text.find("("), text.rfind(")")
        if 0 <= i < j:
            text = text[i + 1:j]
    return json.loads(text)


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
    """Phone push via ntfy.sh. Title must be ASCII (HTTP header)."""
    if not NTFY_TOPIC:
        return
    url = NTFY_TOPIC if NTFY_TOPIC.startswith("http") else f"https://ntfy.sh/{NTFY_TOPIC}"
    req = urllib.request.Request(
        url, data=message.encode("utf-8"), method="POST",
        headers={"Title": title, "Tags": tags})
    urllib.request.urlopen(req, timeout=30)


def alert(station, artist, title, when=""):
    send(EMAIL_TO,
         f"Social Theory just played on {station}: {title}",
         (f"Social Theory aired on {station}!\n\n"
          f"  Artist: {artist}\n"
          f"  Title:  {title}\n"
          + (f"  Time:   {when}\n" if when else "")
          + "\nStations watched: " + ", ".join(s["name"] for s in STATIONS)))
    push(f"Social Theory on {station}", f"{title}" + (f" - {when}" if when else ""))


def process(st):
    name = st["name"]
    ak, tk, tsk, timek = st["artist_key"], st["title_key"], st["ts_key"], st.get("time_key")
    statefile = Path(st["state"])

    try:
        data = fetch_json(st["feed"])
    except Exception as e:
        print(f"[{name}] FETCH FAILED: {e}")      # just try again next cycle
        return

    def ts_of(x):
        try:
            return int(x.get(tsk) or 0)
        except (TypeError, ValueError):
            return 0

    # First run for this station: baseline so we only alert on FUTURE plays.
    if not statefile.exists():
        newest = max((ts_of(x) for x in data), default=0)
        statefile.parent.mkdir(parents=True, exist_ok=True)
        statefile.write_text(str(newest))
        print(f"[{name}] initialized baseline {newest}; no alerts on first run.")
        return

    last_seen = int((statefile.read_text().strip() or "0"))
    hits = sorted(
        (x for x in data
         if x.get(ak) and ARTIST in str(x.get(ak)).lower() and ts_of(x) > last_seen),
        key=ts_of)

    if not hits:
        print(f"[{name}] no match (scanned {len(data)} entries).")
        return

    for h in hits:
        alert(name, str(h.get(ak)), str(h.get(tk)), str(h.get(timek) or ""))
        print(f"[{name}] ALERTED: {h.get(tk)}")
    statefile.write_text(str(ts_of(hits[-1])))


def main():
    if TEST:
        lines = []
        for st in STATIONS:
            try:
                top = fetch_json(st["feed"])[0]
                lines.append(f"{st['name']}: {top.get(st['artist_key'])} - {top.get(st['title_key'])}")
            except Exception as e:
                lines.append(f"{st['name']}: FETCH FAILED ({e})")
        body = ("Test OK - your watcher is live.\nPlaying now:\n  "
                + "\n  ".join(lines)
                + "\n\nYou'll be alerted whenever Social Theory airs on any of these.")
        send(EMAIL_TO, "Song Watcher - test", body)
        push("Song watcher test", "Watcher live. " + " | ".join(lines), tags="white_check_mark")
        print("Test message sent.")
        return

    for st in STATIONS:
        process(st)


if __name__ == "__main__":
    main()
