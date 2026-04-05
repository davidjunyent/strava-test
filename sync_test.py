#!/usr/bin/env python3
"""
Strava Test Sync Script

Fetches a single Strava activity by ID and commits it to the strava_activities
repository with the activity's original date.
"""

import os
import sys
import logging
from typing import Dict
from pathlib import Path

import requests
from dotenv import load_dotenv

from strava_lib import (
    refresh_access_token,
    get_activity_file_path,
    save_activity_file,
    create_commit_with_date,
    validate_repo,
    format_activity_markdown,
)

# Constants
STRAVA_ACTIVITY_URL = "https://www.strava.com/api/v3/activities/{id}"

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_test_config() -> Dict[str, str]:
    """
    Load and validate environment variables for test script.

    Returns:
        Dictionary containing all required configuration values

    Raises:
        ValueError: If any required environment variable is missing
    """
    # Load .env from script directory
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)

    required_vars = [
        "STRAVA_CLIENT_ID",
        "STRAVA_CLIENT_SECRET",
        "STRAVA_REFRESH_TOKEN",
        "STRAVA_ACTIVITY_ID",
        "ACTIVITIES_REPO_PATH",
        "GIT_EMAIL",
        "GIT_NAME",
    ]

    config = {}
    missing_vars = []

    for var in required_vars:
        value = os.environ.get(var)
        if not value:
            missing_vars.append(var)
        else:
            config[var] = value

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    return config


def get_activity(access_token: str, activity_id: str) -> Dict:
    """
    Fetch activity data from Strava API.

    Args:
        access_token: Valid Strava access token
        activity_id: ID of the activity to fetch

    Returns:
        Dictionary containing full activity data

    Raises:
        requests.HTTPError: If the API request fails
        requests.Timeout: If the request times out
    """
    logger.info(f"Fetching activity {activity_id}...")

    url = STRAVA_ACTIVITY_URL.format(id=activity_id)
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        activity = response.json()
        logger.info(f"Activity fetched: {activity.get('name', 'Unknown')}")
        return activity
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            logger.error(f"Activity {activity_id} not found")
            logger.error("")
            logger.error("Possible causes:")
            logger.error("  1. Activity ID is incorrect")
            logger.error("  2. Activity doesn't belong to your account")
            logger.error("  3. Missing 'activity:read_all' OAuth scope")
            logger.error("")
            logger.error("To fix scope issues, run: python authorize.py")
            logger.error("See OAUTH_SETUP.md for detailed instructions")
        elif e.response.status_code == 401:
            logger.error("Unauthorized - check your access token")
            logger.error("Your token may have expired or have insufficient scopes")
            logger.error("Run: python authorize.py")
        elif e.response.status_code == 403:
            logger.error("Forbidden - insufficient permissions")
            logger.error("Your OAuth token doesn't have the required scopes")
            logger.error("Required scope: activity:read_all")
            logger.error("Run: python authorize.py")
        else:
            logger.error(f"Failed to fetch activity: {e}")
        raise
    except requests.Timeout:
        logger.error("Request timed out while fetching activity")
        raise


def main() -> None:
    """Main test sync function."""
    logger.info("Starting Strava test sync...")

    # Load configuration
    try:
        config = load_test_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Validate repository
    repo_path = config["ACTIVITIES_REPO_PATH"]
    try:
        validate_repo(repo_path)
        logger.info(f"Activities repository validated: {repo_path}")
    except ValueError as e:
        logger.error(f"Repository validation failed: {e}")
        sys.exit(1)

    # Refresh access token
    try:
        access_token = refresh_access_token(
            config["STRAVA_CLIENT_ID"],
            config["STRAVA_CLIENT_SECRET"],
            config["STRAVA_REFRESH_TOKEN"],
        )
    except Exception as e:
        logger.error(f"Failed to refresh token: {e}")
        sys.exit(1)

    # Fetch activity
    try:
        activity = get_activity(access_token, config["STRAVA_ACTIVITY_ID"])
    except Exception as e:
        logger.error(f"Failed to fetch activity: {e}")
        sys.exit(1)

    # Format markdown
    markdown = format_activity_markdown(activity)

    # Get file path
    file_path = get_activity_file_path(activity, repo_path)

    # Save activity file
    relative_path = save_activity_file(markdown, file_path, repo_path)
    logger.info(f"Activity saved to {relative_path}")

    # Create commit with activity date
    create_commit_with_date(
        repo_path,
        relative_path,
        activity,
        config["GIT_NAME"],
        config["GIT_EMAIL"],
    )

    logger.info("✓ Sync completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
