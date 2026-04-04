#!/usr/bin/env python3
"""
Strava Test Sync Script

Fetches a single Strava activity by ID and commits it to the strava_activities
repository with the activity's original date.
"""

import os
import sys
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import requests
from dotenv import load_dotenv

# Constants
STRAVA_TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"
STRAVA_ACTIVITY_URL = "https://www.strava.com/api/v3/activities/{id}"

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_environment() -> Dict[str, str]:
    """
    Load and validate environment variables.

    Returns:
        Dictionary containing all required configuration values

    Raises:
        ValueError: If any required environment variable is missing
    """
    load_dotenv()

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


def refresh_access_token(
    client_id: str, client_secret: str, refresh_token: str
) -> str:
    """
    Refresh Strava OAuth access token.

    Args:
        client_id: Strava application client ID
        client_secret: Strava application client secret
        refresh_token: Current refresh token

    Returns:
        New access token string

    Raises:
        requests.HTTPError: If the API request fails
        requests.Timeout: If the request times out
    """
    logger.info("Refreshing Strava access token...")

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    try:
        response = requests.post(STRAVA_TOKEN_URL, data=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info("Access token refreshed successfully")
        return data["access_token"]
    except requests.HTTPError as e:
        logger.error(f"Failed to refresh token: {e}")
        raise
    except requests.Timeout:
        logger.error("Request timed out while refreshing token")
        raise


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


def parse_activity_date(date_str: str) -> datetime:
    """
    Parse ISO 8601 date string to datetime object.

    Args:
        date_str: ISO 8601 formatted date string

    Returns:
        Parsed datetime object
    """
    # Handle both with and without 'Z' suffix
    if date_str.endswith("Z"):
        date_str = date_str[:-1]
    return datetime.fromisoformat(date_str)


def get_activity_file_path(activity: Dict, repo_path: str) -> Path:
    """
    Determine the file path for the activity markdown file.

    Args:
        activity: Activity data dictionary
        repo_path: Path to the activities repository

    Returns:
        Path object for the activity markdown file
    """
    date = parse_activity_date(activity["start_date_local"])
    year = date.strftime("%Y")
    month = date.strftime("%m")
    day = date.strftime("%d")

    activity_dir = Path(repo_path) / year / month / day
    base_filename = "activity.md"

    # Check if activity.md exists, find next available number
    if not (activity_dir / base_filename).exists():
        return activity_dir / base_filename

    # Find next available number
    counter = 2
    while (activity_dir / f"activity-{counter}.md").exists():
        counter += 1

    return activity_dir / f"activity-{counter}.md"


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to HH:MM:SS or MM:SS.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def format_pace(distance_m: float, moving_time: int) -> Optional[str]:
    """
    Calculate and format pace in min/km.
    
    Args:
        distance_m: Distance in meters
        moving_time: Moving time in seconds
        
    Returns:
        Formatted pace string (e.g., "5:58 min/km") or None if cannot calculate
    """
    if distance_m <= 0 or moving_time <= 0:
        return None
    
    # Calculate pace: seconds per kilometer
    pace_per_km = (moving_time / distance_m) * 1000
    
    minutes = int(pace_per_km // 60)
    seconds = int(pace_per_km % 60)
    
    return f"{minutes}:{seconds:02d} min/km"


def format_activity_markdown(activity: Dict) -> str:
    """
    Format activity data as markdown.

    Args:
        activity: Activity data dictionary

    Returns:
        Formatted markdown string
    """
    # Extract basic fields
    name = activity.get("name", "Untitled Activity")
    description = activity.get("description")
    # Use sport_type for more specific activity types (TrailRun, Run, etc.)
    # Fall back to type if sport_type is not available
    activity_type = activity.get("sport_type") or activity.get("type", "Unknown")
    activity_id = activity.get("id")
    date_str = activity.get("start_date_local", "")
    distance_m = activity.get("distance", 0)
    moving_time = activity.get("moving_time", 0)
    elevation_gain = activity.get("total_elevation_gain", 0)

    # Convert distance to km
    distance_km = distance_m / 1000

    # Format date
    date = parse_activity_date(date_str)
    formatted_date = date.strftime("%Y-%m-%d %H:%M:%S")

    # Format duration
    duration = format_duration(moving_time)
    
    # Calculate pace
    pace = format_pace(distance_m, moving_time)

    # Build markdown
    markdown_parts = []
    
    # Add title
    markdown_parts.append(f"# {name}")
    
    # Add description if present
    if description and description.strip():
        markdown_parts.append("")  # Blank line after title
        markdown_parts.append(description.strip())
    
    # Add blank line before metadata
    markdown_parts.append("")
    
    # Add activity type
    markdown_parts.append(f"**Type:** {activity_type}  ")
    
    # Add remaining metadata
    markdown_parts.append(f"**Date:** {formatted_date}  ")
    markdown_parts.append(f"**Distance:** {distance_km:.2f} km  ")
    markdown_parts.append(f"**Duration:** {duration}  ")
    
    # Add pace if available
    if pace:
        markdown_parts.append(f"**Pace:** {pace}  ")
    
    # Add elevation gain if significant (> 10m)
    if elevation_gain > 10:
        markdown_parts.append(f"**Elevation gain:** {elevation_gain:.0f} m  ")
    
    # Add Strava link with activity ID
    if activity_id:
        strava_url = f"https://www.strava.com/activities/{activity_id}"
        gpx_export_url = f"https://www.strava.com/activities/{activity_id}/export_gpx"
        markdown_parts.append(f"**Strava:** [View on Strava]({strava_url})  ")
        markdown_parts.append(f"**GPX:** [Export GPX]({gpx_export_url})  ")
    
    return "\n".join(markdown_parts) + "\n"


def save_activity_file(activity: Dict, repo_path: str) -> Path:
    """
    Save activity data to markdown file.

    Args:
        activity: Activity data dictionary
        repo_path: Path to the activities repository

    Returns:
        Relative path from repo root
    """
    file_path = get_activity_file_path(activity, repo_path)

    # Create parent directories
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate and write content
    content = format_activity_markdown(activity)
    file_path.write_text(content)

    # Return relative path from repo root
    relative_path = file_path.relative_to(repo_path)
    logger.info(f"Activity saved to {relative_path}")

    return relative_path


def create_commit_with_date(
    repo_path: str, file_path: Path, activity: Dict, git_name: str, git_email: str
) -> None:
    """
    Create a git commit with the activity's date.

    Args:
        repo_path: Path to the activities repository
        file_path: Relative path to the activity file
        activity: Activity data dictionary
        git_name: Git author name
        git_email: Git author email

    Raises:
        subprocess.CalledProcessError: If git command fails
    """
    # Parse activity date
    date = parse_activity_date(activity["start_date_local"])
    date_str = date.isoformat()

    # Build commit message
    activity_type = activity.get("sport_type") or activity.get("type", "Activity")
    distance_km = activity.get("distance", 0) / 1000
    date_formatted = date.strftime("%Y-%m-%d")
    commit_message = f"{activity_type} on {date_formatted}: {distance_km:.2f} km"

    # Git add
    logger.info(f"Staging {file_path}...")
    subprocess.run(
        ["git", "add", str(file_path)],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )

    # Git commit with custom date
    logger.info(f"Creating commit with date {date_str}...")
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = date_str
    env["GIT_COMMITTER_DATE"] = date_str

    result = subprocess.run(
        [
            "git",
            "commit",
            "-m",
            commit_message,
            "--author",
            f"{git_name} <{git_email}>",
        ],
        cwd=repo_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    # Get commit hash
    commit_hash = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    logger.info(f"Commit created: {commit_hash[:8]} - {commit_message}")


def validate_repo(repo_path: str) -> None:
    """
    Validate that the activities repository exists and is a git repo.

    Args:
        repo_path: Path to validate

    Raises:
        ValueError: If path doesn't exist or is not a git repository
    """
    path = Path(repo_path)

    if not path.exists():
        raise ValueError(
            f"Activities repository not found at {repo_path}. "
            "Please create it first with 'git init'."
        )

    if not (path / ".git").exists():
        raise ValueError(
            f"Directory {repo_path} exists but is not a git repository. "
            "Run 'git init' inside it first."
        )

    logger.info(f"Activities repository validated: {repo_path}")


def main() -> None:
    """Main execution flow."""
    logger.info("Starting Strava test sync...")

    # Load environment variables
    config = load_environment()

    # Validate activities repository
    validate_repo(config["ACTIVITIES_REPO_PATH"])

    # Refresh access token
    access_token = refresh_access_token(
        config["STRAVA_CLIENT_ID"],
        config["STRAVA_CLIENT_SECRET"],
        config["STRAVA_REFRESH_TOKEN"],
    )

    # Get activity by ID
    activity = get_activity(access_token, config["STRAVA_ACTIVITY_ID"])

    # Save activity file
    file_path = save_activity_file(activity, config["ACTIVITIES_REPO_PATH"])

    # Create commit with activity date
    create_commit_with_date(
        config["ACTIVITIES_REPO_PATH"],
        file_path,
        activity,
        config["GIT_NAME"],
        config["GIT_EMAIL"],
    )

    logger.info("✓ Sync completed successfully!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed: {e}")
        sys.exit(1)
