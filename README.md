# Social Theory – WSTB Song Watcher (cloud)

Checks [88.9 WSTB](https://www.wstb.org/page/recently-played)'s recently-played
feed every 30 minutes and emails + texts when any **Social Theory** track airs.
Runs on GitHub Actions, so it works regardless of whether any personal computer
is on.

## How it works
- `check_song.py` reads the station's JSON feed
  (`https://wp.rock889.com/nowplaying/nowplaying.php`) and matches any artist
  containing "social theory" (case-insensitive).
- It emails via Gmail SMTP and texts via a carrier SMS gateway.
- `state/last_seen.txt` (committed back by the workflow) prevents duplicate or
  missed alerts across delayed/skipped runs.

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
