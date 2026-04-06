# Strava Test Sync

Test script to validate Strava API integration and Git commit workflow.

## What it does

Fetches one or more Strava activities by ID and commits them to a Git repository with the original activity dates preserved. If any activity fails (e.g., 404 error), the script continues processing remaining activities and reports a summary at the end.

## Use of Strava Credentials

**1. Get Strava API credentials:**
- Go to https://www.strava.com/settings/api
- Create an application and note your Client ID and Client Secret
- See `OAUTH_SETUP.md` for getting a refresh token

**2. Configure environment:**
```bash
cp .env.example .env
# Edit .env with your credentials
# Note: Activity IDs are now passed as command-line arguments, not in .env
```

**4. Initialize activities repository:**
```bash
mkdir -p /path/to/strava-activities
cd /path/to/strava-activities
git init
```

## Usage

Sync one or more activities by providing their IDs as command-line arguments:

```bash
# Sync a single activity
python sync_test.py 12345678

# Sync multiple activities
python sync_test.py 12345678 87654321 11223344

# Show help
python sync_test.py --help
```

**Finding activity IDs:** Look at any Strava activity URL: `https://www.strava.com/activities/12345678`

## Output

Creates commits in `YYYY/MM/DD/activity.md` format with commit messages like:
```
TrailRun on 2024-03-15: 10.50 km
```

### Example output

```
============================================================
SUMMARY
============================================================
✓ Successfully synced: 2 activity(ies)
  - 12345678
  - 87654321
✗ Failed: 1 activity(ies)
  - 99999999: Not found (404)
============================================================
```

The script exits with code 0 if all activities succeed, or code 1 if any fail.

## License

MIT