"""One-time helper: run this on YOUR OWN computer (not in a server/CI) to mint
a YouTube API refresh token. It opens a browser for you to log in and grant
consent, then prints the values to store as GitHub Actions secrets.

Usage:
    pip install google-auth-oauthlib
    python get_refresh_token.py --client-secret client_secret.json

`client_secret.json` is the file you download from Google Cloud Console after
creating an OAuth client of type "Desktop app". See SETUP.md for the full
walkthrough.
"""
import argparse
import json

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-secret", required=True, help="Path to client_secret.json")
    args = parser.parse_args()

    with open(args.client_secret) as f:
        client_config = json.load(f)
    client_id = client_config["installed"]["client_id"]
    client_secret = client_config["installed"]["client_secret"]

    flow = InstalledAppFlow.from_client_secrets_file(args.client_secret, SCOPES)
    creds = flow.run_local_server(port=0)

    print("\nAdd these as GitHub Actions repo secrets (Settings > Secrets and variables > Actions):\n")
    print(f"YT_CLIENT_ID={client_id}")
    print(f"YT_CLIENT_SECRET={client_secret}")
    print(f"YT_REFRESH_TOKEN={creds.refresh_token}")
