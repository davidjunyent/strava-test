# Strava OAuth Setup

Get a refresh token with the required `activity:read_all` scope to access all your Strava activities.

## Prerequisites

1. Strava API application created at https://www.strava.com/settings/api
2. `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` in your `.env` file

## Quick Setup

**1. Run authorization script:**
```bash
python authorize.py
```

**2. Open the generated URL in your browser**
- Log in to Strava
- Click **Authorize** (check that scope shows `activity:read_all`)

**3. Copy the callback URL**

After authorizing, you'll be redirected to `http://localhost/?code=XXX...`

The page will error (expected) — just copy the entire URL from your browser's address bar.

**4. Paste the URL in the terminal**

The script will extract the code and display your `STRAVA_REFRESH_TOKEN`.

**5. Update `.env` file:**
```bash
STRAVA_REFRESH_TOKEN=your_new_token_here
```

**6. Test it:**
```bash
python sync_test.py
```

## Troubleshooting

**404 "Activity not found"**
- Wrong scope: Re-run `authorize.py` to get `activity:read_all` scope
- Wrong activity ID: Get ID from Strava URL `strava.com/activities/12345678`

**401 "Unauthorized"**
- Re-run `authorize.py` to get a fresh token
- Verify `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` are correct

## Security

- Never commit `.env` or share tokens
- Revoke access at: https://www.strava.com/settings/apps
