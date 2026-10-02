# Bhavin Moriya — YouTube Shorts Dashboard

This project adds an automated YouTube Shorts dashboard to the existing
`bhavinmoriya/bhavinmoriya` GitHub profile repository.

## What it does

Every day at **07:00 Europe/Berlin**, GitHub Actions:

1. Determines the previous German calendar day.
2. Reads your channel's uploads playlist using the YouTube Data API.
3. Retrieves video metadata and view counts.
4. Identifies Shorts uploaded on that day.
5. Selects the most-viewed Short among them.
6. Writes `shorts/data/shorts.json`.
7. Deploys the repository to GitHub Pages.

The website embeds the real YouTube videos using YouTube's iframe player. The
videos remain hosted by YouTube.

GitHub's scheduler supports an IANA timezone such as `Europe/Berlin`; scheduled
runs can nevertheless be delayed by GitHub under load.

## Architecture

```text
YouTube
   │
   │ YouTube Data API v3
   ▼
GitHub Actions ──► Python updater ──► shorts/data/shorts.json
   │
   └─────────────────────────────────► GitHub Pages
                                      │
                                      ▼
                              /bhavinmoriya/shorts/
```

## One-time setup

### 1. Create a YouTube Data API key

In Google Cloud:

- create/select a project
- enable **YouTube Data API v3**
- create an API key
- restrict the key to YouTube Data API v3 where practical

No YouTube password and no OAuth token are needed for this public read-only
workflow.

### 2. Add GitHub Actions secrets

In the repository:

`Settings → Secrets and variables → Actions → New repository secret`

Create:

```text
YOUTUBE_API_KEY
YOUTUBE_CHANNEL_ID
```

`YOUTUBE_CHANNEL_ID` is the channel ID, not the channel display name.

### 3. Enable GitHub Pages

In:

`Settings → Pages`

select:

```text
Source: GitHub Actions
```

The workflow in `.github/workflows/update-shorts-pages.yml` performs the build
and deployment.

### 4. Test manually

Go to:

`Actions → Update YouTube Shorts Pages → Run workflow`

The workflow supports a `target_date` input in `YYYY-MM-DD` format. Leaving it
blank makes the workflow use yesterday in `Europe/Berlin`.

## Local development

This project uses `uv`.

```bash
uv sync
uv run pytest
```

To run the updater locally:

```bash
export YOUTUBE_API_KEY="..."
export YOUTUBE_CHANNEL_ID="..."
uv run python scripts/update_shorts.py
```

For a particular date:

```bash
uv run python scripts/update_shorts.py --date 2026-09-29
```

## Shorts detection

YouTube currently categorizes eligible square/vertical videos up to three
minutes as Shorts for standard channels. The public Data API does not expose a
simple reliable `isShort` flag or the video's aspect ratio in the video
resource.

Because your workflow is specifically based on your daily Shorts uploads, the
default configuration assumes the uploads you make for this automation are
Shorts and applies a maximum duration of 180 seconds.

If you later start mixing long-form uploads into the same channel, set
`assume_all_uploads_are_shorts` to `false`. In that mixed-channel case, an
additional classification mechanism should be added rather than pretending
the public API can always distinguish the formats.

## Security

The API key is never placed in the generated website and is never committed to
Git. It is read from the GitHub Actions secret at runtime.

Do not put the key in:

- `README.md`
- HTML
- JavaScript
- JSON
- `pyproject.toml`
- Git history
- workflow source

## Repository integration

This package deliberately adds files rather than replacing your existing
profile README or other project files.

After installing it, your repository will have roughly:

```text
bhavinmoriya/
├── .github/
│   └── workflows/
│       └── update-shorts-pages.yml
├── shorts/
│   ├── assets/
│   ├── data/
│   ├── config.json
│   ├── index.html
│   └── styles.css
├── scripts/
│   └── update_shorts.py
└── tests/
    └── test_update_shorts.py
```

A link to `/shorts/` can then be added to your profile README.
