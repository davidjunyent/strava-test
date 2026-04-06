#!/usr/bin/env python3
"""
Strava Test Sync Script

Fetches one or more Strava activities by ID and commits them to the 
strava_activities repository with each activity's original date.

Usage:
    python sync_test.py ACTIVITY_ID [ACTIVITY_ID ...]
    python sync_test.py 12345678
    python sync_test.py 12345678 87654321 11223344
"""

import os
import sys
import logging
import argparse
from typing import Dict, List
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


def parse_arguments() -> List[str]:
    """
    Parse command-line arguments.

    Returns:
        List of activity IDs to process

    Raises:
        SystemExit: If no activity IDs are provided or --help is used
    """
    parser = argparse.ArgumentParser(
        description="Sync Strava activities to Git repository",
        epilog="Example: python sync_test.py 12345678 87654321",
    )
    parser.add_argument(
        "activity_ids",
        metavar="ACTIVITY_ID",
        type=str,
        nargs="+",
        help="One or more Strava activity IDs to sync",
    )

    args = parser.parse_args()
    return args.activity_ids


def main() -> None:
    """Main test sync function."""
    logger.info("Starting Strava test sync...")

    # Parse command-line arguments
    activity_ids = parse_arguments()
    logger.info(f"Processing {len(activity_ids)} activity(ies)...")

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

    # Track results
    successful = []
    failed = {}

    # Process each activity
    for activity_id in activity_ids:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing activity {activity_id}...")
        logger.info(f"{'='*60}")

        try:
            # Fetch activity
            activity = get_activity(access_token, activity_id)

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

            logger.info(f"✓ Activity {activity_id} synced successfully!")
            successful.append(activity_id)

        except requests.HTTPError as e:
            error_msg = f"HTTP {e.response.status_code}"
            if e.response.status_code == 404:
                error_msg = "Not found (404)"
            elif e.response.status_code == 401:
                error_msg = "Unauthorized (401)"
            elif e.response.status_code == 403:
                error_msg = "Forbidden (403)"

            logger.error(f"✗ Activity {activity_id} failed: {error_msg}")
            failed[activity_id] = error_msg

        except Exception as e:
            logger.error(f"✗ Activity {activity_id} failed: {str(e)}")
            failed[activity_id] = str(e)

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"✓ Successfully synced: {len(successful)} activity(ies)")

    if successful:
        for activity_id in successful:
            logger.info(f"  - {activity_id}")

    if failed:
        logger.info(f"✗ Failed: {len(failed)} activity(ies)")
        for activity_id, error in failed.items():
            logger.info(f"  - {activity_id}: {error}")

    logger.info(f"{'='*60}\n")

    # Exit with error code if any failed
    if failed:
        sys.exit(1)
    else:
        logger.info("All activities synced successfully!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️  Cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
