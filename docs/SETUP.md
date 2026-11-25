# Setup and configuration

How to run the project locally, configure it, and how deployment works. For the project overview, see the [main README](../README.md).

## Folder structure

```
sports-calendar/
├─ config.json                  ← driver, team and season settings (change who you follow here)
├─ .github/workflows/deploy.yml ← GitHub Actions: fetches fresh data and deploys to Azure
├─ .gitignore
├─ scripts/
│  ├─ build_data.py             ← the script you run (fetches F1 + NHL data into site/data)
│  ├─ f1.py                     ← Jolpica API: schedule, Oscar's results, standings
│  ├─ nhl.py                    ← NHL web API: Senators schedule, results, division standings
│  ├─ circuits.py               ← local time zone for each circuit
│  ├─ f1_manual_2027.json       ← placeholder 2027 calendar (ignored once Jolpica has 2027)
│  └─ common.py                 ← shared helpers
└─ site/                        ← the website (this folder is what gets deployed)
   ├─ index.html
   ├─ style.css
   ├─ app.js
   ├─ favicon.svg               ← browser tab icon
   ├─ apple-touch-icon.png      ← icon when added to a phone's home screen
   └─ data/                     ← JSON written by build_data.py (don't edit by hand)
```

## Running it locally

Needs Python 3.8 or newer; there are no extra packages to install. In a terminal, go to this folder and run:

```bash
# 1. Fetch the data (takes about a minute)
python scripts/build_data.py

# 2. Start a local web server
python -m http.server 8000 -d site
```

Then open http://localhost:8000 in your browser.
On a Mac, use `python3` if `python` doesn't work.

- Double-clicking `index.html` won't load the data. Browsers block that for security reasons, so always open the site through the server in step 2.
- To get fresh data, run step 1 again and refresh the browser.
  On race weekends, re-run it after a session ends to pick up Oscar's result.

## Testing tip

Add `?now=` to the URL to see the page as if it were a different moment. Handy for checking the LIVE badge and countdowns.

```
http://localhost:8000/?now=2026-11-28T15:00:00Z
```

## Good to know

- **2027 F1 schedule**: not on Jolpica yet, so only race days from the official calendar are listed (`Time TBD`).
  Once Jolpica publishes it, the script automatically switches to that data (every session, with times).
- **F1 result delays**: Jolpica sometimes posts results a few days late. Until then the event shows `Result pending`.
- **Sprint qualifying results**: Jolpica doesn't have them, so sprint qualifying shows the time only.
- **NHL API**: it's undocumented, so the NHL can change it without notice. If a fetch fails, the script prints a warning,
  and if only one league fails, that league's previous data is kept.
- **New circuits**: if a circuit's time zone is unknown, the script prints a warning. Add one line to `scripts/circuits.py`.

## Settings (config.json)

| Setting | What it does |
|---|---|
| `f1.seasons` | F1 seasons to fetch (e.g. change to `[2027]` to drop 2026) |
| `f1.driver_id` / `constructor_id` | Whose results to show and highlight (Jolpica IDs: `piastri`, `mclaren`) |
| `nhl.team` / `season` | Team code and season (`OTT`, `20262027`) |
| `nhl.division` | Division the standings open on (all four can be viewed with the toggle) |
| `nhl.include_preseason` | Whether to include preseason games |

## Deploying online (GitHub Actions + Azure Blob Storage static website)

How it works: GitHub Actions (`.github/workflows/deploy.yml`) runs `build_data.py` on a schedule to build fresh data,
then uploads the `site` folder to the `$web` container of an Azure Storage account with static website hosting turned on.
Every file is uploaded with `Cache-Control: no-cache`, so browsers always pick up the latest version.
`site/data` is not committed to GitHub (see `.gitignore`).

When it runs (times in UTC):
- on every push to the `main` branch
- daily at 04:17 and 10:17 (about 11 pm and 5 am in Ottawa; an hour later during daylight saving time)
- every 3 hours Friday to Monday (so F1 weekend results show up quickly)
- manually: GitHub repo > Actions > "Build data and deploy" > Run workflow

Required settings in the GitHub repo (Settings > Secrets and variables > Actions):
- Secret `AZURE_STORAGE_CONNECTION_STRING`: storage account > Security + networking > Access keys > Connection string
- Variable `SITE_URL` (optional): the static website's primary endpoint, without a trailing slash. With it, a run keeps the published data for a league whose API is temporarily down.

Why not Azure Static Web Apps? Azure for Students subscriptions only allow a few regions, and Static Web Apps
supports only a handful of regions too. When they don't overlap, creation fails with `RequestDisallowedByAzure`.
A storage account can be created in any region the subscription allows.

To publish code changes:

```bash
git add .
git commit -m "Describe what changed"
git push
```
