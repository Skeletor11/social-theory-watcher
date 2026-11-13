# Social Theory – Airplay Watcher (cloud)

Checks multiple radio stations' recently-played feeds every 30 minutes and
emails + pushes (ntfy) when any **Social Theory** track airs. Runs on GitHub
Actions, so it works regardless of whether any personal computer is on.

Stations watched (see `STATIONS` in `check_song.py`):
- **88.9 WSTB** (Streetsboro OH) – feed `wp.rock889.com/nowplaying`
- **98.9 Magic FM / KKMG** (Colorado Springs CO) – SoCast feed
  `socast-public.s3.amazonaws.com/player/lp_3326_3126.js`

## How it works
- `check_song.py` reads each station's JSON feed and matches any artist
  containing "social theory" (case-insensitive). Each station declares which
  JSON fields hold the artist/title/timestamp, so differing feed formats share
  one code path.
- It emails via Gmail SMTP and pushes to a phone via ntfy.sh.
- Per-station `state/last_seen*.txt` files (committed back by the workflow)
  prevent duplicate or missed alerts across delayed/skipped runs.

To add another station, inspect its page for the recently-played feed and add an
entry to `STATIONS` with the right field names and a unique `state` file.

## One-time setup
1. **Gmail App Password** – create at https://myaccount.google.com/apppasswords
   (needs 2-Step Verification). 16 characters.
2. **Set the four repo secrets** (Settings → Secrets and variables → Actions, or
   `gh secret set`):
   - `GMAIL_ADDRESS` – your sending Gmail
   - `GMAIL_APP_PASSWORD` – the 16-char app password
   - `NOTIFY_EMAIL` – where alerts go
   - `NTFY_TOPIC` – private ntfy.sh topic for phone push (Verizon killed email-to-SMS)
3. **Test**: Actions tab → "WSTB Song Watcher" → Run workflow → test = true,
   or `gh workflow run "WSTB Song Watcher" -f test=true`.

## Notes / limits
- Make the repo **public** so Actions minutes are free; secrets stay encrypted.
- GitHub cron timing is best-effort (can run a few minutes late).
- GitHub auto-pauses scheduled workflows after ~60 days of no repo activity; a
  manual run re-arms it.
- If WSTB rebuilds their site the feed URL may change (watch for failures).
