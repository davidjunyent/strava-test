# Strava Test Sync

Test script to validate Strava API integration and Git commit workflow.

## What it does

Fetches a single Strava activity by ID and commits it to a Git repository with the original activity date preserved.

## Use of Strava Credentials

**1. Get Strava API credentials:**
- Go to https://www.strava.com/settings/api
- Create an application and note your Client ID and Client Secret
- See `OAUTH_SETUP.md` for getting a refresh token

**2. Configure environment:**
```bash
cp .env.example .env
# Edit .env with your credentials
```

**4. Initialize activities repository:**
```bash
mkdir -p /path/to/strava-activities
cd /path/to/strava-activities
git init
```

## Usage

```bash
python sync_test.py
```

**Finding activity IDs:** Look at any Strava activity URL: `https://www.strava.com/activities/12345678`

## Output

Creates commits in `YYYY/MM/DD/activity.md` format with commit messages like:
```
TrailRun on 2024-03-15: 10.50 km
```

## License

MIT