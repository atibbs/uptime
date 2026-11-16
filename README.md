# uptime

Checks Andrew's sites every 5 minutes with GitHub Actions. When a site goes down, it opens an **Outage** issue, and GitHub emails and pushes it to the mobile app. When the site comes back, the issue gets a recovery comment and closes itself.

- Sites live in [`sites.yaml`](sites.yaml). Keep them in sync with `apps.yaml` in the private `atibbs/factory` repo.
- A URL counts as up when it returns a status below 400 within 20 seconds. Redirects are followed.
- Each failure is retried once after 20 seconds before an issue opens.
- This repo is public so the checks run on free Actions minutes.
- GitHub's cron scheduler dropped most 5-minute runs here, so the workflow doesn't rely on it. One run loops for 5½ hours ([`loop.sh`](loop.sh)), checking every 5 minutes, then starts the next run itself. An hourly cron (:07) only restarts the chain if it breaks.
- Changes pushed to `main` take effect when the current loop ends. To apply one sooner, cancel the running workflow; the queued run starts immediately. (A cancelled run doesn't start a successor.)
- Each morning between 14:17 and 14:55 UTC the loop also starts `digest-data` in `atibbs/factory`, using the `FACTORY_DISPATCH_TOKEN` secret (fine-grained PAT, factory repo only, Actions read/write). Without the secret it skips this.
- The factory's daily digest reads the outage issues here.

Run a check locally without touching issues:

```bash
python3 check.py --dry-run
```
