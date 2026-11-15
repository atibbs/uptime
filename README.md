# uptime

Checks Andrew's sites every 5 minutes with GitHub Actions. When a site goes down, it opens an **Outage** issue, and GitHub emails and pushes it to the mobile app. When the site comes back, the issue gets a recovery comment and closes itself.

- Sites live in [`sites.yaml`](sites.yaml). Keep them in sync with `apps.yaml` in the private `atibbs/factory` repo.
- A URL counts as up when it returns a status below 400 within 20 seconds. Redirects are followed.
- Each failure is retried once after 20 seconds before an issue opens.
- This repo is public so the checks run on free Actions minutes. GitHub may delay scheduled runs by a few minutes.
- The factory's daily digest reads the outage issues here.

Run a check locally without touching issues:

```bash
python3 check.py --dry-run
```
