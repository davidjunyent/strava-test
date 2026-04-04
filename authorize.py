#!/usr/bin/env python3
"""
Strava OAuth Authorization Script

This script helps you authorize your Strava application and obtain
a refresh token with the correct scopes (activity:read_all).
"""

import os
import sys
import logging
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
STRAVA_AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"


def load_client_credentials():
    """
    Load Strava client credentials from environment.

    Returns:
        Tuple of (client_id, client_secret)

    Raises:
        ValueError: If credentials are missing
    """
    load_dotenv()

    client_id = os.environ.get("STRAVA_CLIENT_ID")
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError(
            "Missing STRAVA_CLIENT_ID or STRAVA_CLIENT_SECRET in .env file"
        )

    return client_id, client_secret


def generate_authorization_url(client_id: str, redirect_uri: str = "http://localhost") -> str:
    """
    Generate Strava OAuth authorization URL.

    Args:
        client_id: Strava application client ID
        redirect_uri: OAuth redirect URI (default: http://localhost)

    Returns:
        Authorization URL for the user to visit
    """
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "activity:read_all",
        "approval_prompt": "force",  # Force re-authorization to ensure new scopes
    }

    return f"{STRAVA_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code_for_token(
    client_id: str, client_secret: str, code: str
) -> dict:
    """
    Exchange authorization code for access and refresh tokens.

    Args:
        client_id: Strava application client ID
        client_secret: Strava application client secret
        code: Authorization code from OAuth callback

    Returns:
        Dictionary containing access_token, refresh_token, and scope info

    Raises:
        requests.HTTPError: If token exchange fails
    """
    logger.info("Exchanging authorization code for tokens...")

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "grant_type": "authorization_code",
    }

    try:
        response = requests.post(STRAVA_TOKEN_URL, data=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        logger.info("Tokens obtained successfully!")
        return data
    except requests.HTTPError as e:
        logger.error(f"Failed to exchange code for token: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {e.response.text}")
        raise


def print_instructions(auth_url: str) -> None:
    """Print step-by-step instructions for the user."""
    print("\n" + "=" * 80)
    print("STRAVA OAUTH AUTHORIZATION")
    print("=" * 80)
    print("\nFollow these steps to authorize your application:\n")
    print("1. Open this URL in your browser:")
    print(f"\n   {auth_url}\n")
    print("2. Click 'Authorize' to grant access to your Strava activities")
    print("3. After authorization, you'll be redirected to a URL like:")
    print("   http://localhost/?state=&code=XXXXXXXXXXXXX&scope=read,activity:read_all")
    print("\n4. Copy the ENTIRE URL from your browser's address bar")
    print("   (or just the 'code' parameter value)")
    print("\n" + "=" * 80 + "\n")


def extract_code_from_url(url: str) -> str:
    """
    Extract authorization code from callback URL.

    Args:
        url: Full callback URL or just the code value

    Returns:
        Authorization code

    Raises:
        ValueError: If code cannot be extracted
    """
    # If it looks like a full URL, parse it
    if url.startswith("http"):
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        if "code" not in params:
            raise ValueError("No 'code' parameter found in URL")
        
        code = params["code"][0]
        
        # Also extract and display scopes if present
        if "scope" in params:
            scopes = params["scope"][0]
            logger.info(f"Granted scopes: {scopes}")
            
            if "activity:read_all" not in scopes:
                logger.warning(
                    "WARNING: activity:read_all scope not granted! "
                    "You may not have full access to activities."
                )
        
        return code
    else:
        # Assume it's just the code value
        return url.strip()


def main():
    """Main execution flow."""
    try:
        # Load credentials
        client_id, client_secret = load_client_credentials()

        # Generate authorization URL
        auth_url = generate_authorization_url(client_id)

        # Print instructions
        print_instructions(auth_url)

        # Get authorization code from user
        callback_url = input("Paste the callback URL (or just the code): ").strip()
        
        if not callback_url:
            logger.error("No URL provided. Exiting.")
            sys.exit(1)

        # Extract code
        code = extract_code_from_url(callback_url)
        logger.info(f"Authorization code: {code[:20]}...")

        # Exchange for tokens
        token_data = exchange_code_for_token(client_id, client_secret, code)

        # Display results
        print("\n" + "=" * 80)
        print("SUCCESS! Tokens obtained")
        print("=" * 80)
        print("\nAdd these to your .env file:\n")
        print(f"STRAVA_REFRESH_TOKEN={token_data['refresh_token']}")
        print(f"# Access token (expires in {token_data.get('expires_in', 0)} seconds):")
        print(f"# {token_data['access_token']}")
        print(f"\n# Athlete ID: {token_data.get('athlete', {}).get('id', 'N/A')}")
        print(f"# Athlete: {token_data.get('athlete', {}).get('firstname', '')} "
              f"{token_data.get('athlete', {}).get('lastname', '')}")
        print("\n" + "=" * 80 + "\n")

        print("⚠️  IMPORTANT: Update your .env file with the new STRAVA_REFRESH_TOKEN")
        print("   The old refresh token will no longer work.\n")

    except KeyboardInterrupt:
        logger.info("\nAuthorization cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Authorization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
