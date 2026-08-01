# Setup: going from "code in a repo" to "channel actually posting"

Everything in this repo is built and ready to run. What's left is a short list
of steps that **only you can do**, because Google requires the account owner
to personally create the channel and click "Allow" on API access — no AI or
script can do this part on your behalf. It takes about 10-15 minutes, once.

## 1. Create the channel

1. Go to youtube.com, sign in with (or create) a Google account.
2. Click your profile icon > **Create a channel**. Pick a name/handle.

## 2. Enable the YouTube Data API

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (any name).
3. Go to **APIs & Services > Library**, search **YouTube Data API v3**, click **Enable**.
4. Go to **APIs & Services > OAuth consent screen**:
   - User type: External.
   - Fill in app name / your email.
   - Add scope: `.../auth/youtube.upload`.
   - Under **Test users**, add your own Google account email.
   - Save. (You can leave publishing status as "Testing" — see note below.)
5. Go to **APIs & Services > Credentials > Create Credentials > OAuth client ID**.
   - Application type: **Desktop app**.
   - Download the resulting JSON, save it as `client_secret.json`.

## 3. Mint a refresh token (run this locally, not in CI)

On your own machine, with this repo cloned:

```bash
pip install google-auth-oauthlib
python scripts/get_refresh_token.py --client-secret client_secret.json
```

This opens a browser, you log in and click Allow, and it prints:

```
YT_CLIENT_ID=...
YT_CLIENT_SECRET=...
YT_REFRESH_TOKEN=...
```

**Delete `client_secret.json` afterwards** — don't commit it anywhere.

## 4. Add the secrets to GitHub

In this repo: **Settings > Secrets and variables > Actions > New repository secret**.
Add all three: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

## 5. Go live

The workflow defaults `PRIVACY_STATUS` to `private` so nothing goes public until
you've checked a test upload. To flip it:
**Settings > Secrets and variables > Actions > Variables tab > New repository variable**
`PRIVACY_STATUS = public`.

Once merged to your default branch, `.github/workflows/post_short.yml` runs
daily and posts one short automatically — pick **Actions > Post daily YouTube
Short > Run workflow** any time to trigger it manually and check the result.

## Notes / limits to know about

- **OAuth token expiry**: while your Google Cloud OAuth app is in "Testing"
  status, refresh tokens can expire after 7 days, which would break the
  automation until you re-run step 3. To avoid that, in the OAuth consent
  screen click **Publish App** (moves it out of Testing). For a single-user
  script like this, Google does not require full verification to do this —
  you may see an "unverified app" warning when you re-auth, which is fine to
  click through since it's your own app and your own data.
- **API quota**: the default YouTube Data API quota is 10,000 units/day, and
  a video upload costs ~1,600 units — comfortably enough for one short a day.
- **Content**: `data/facts.json` has 35 curated facts; `scripts/generate_content.py`
  rotates through them without repeats and starts a new cycle once they're all
  used. Add more facts to that file any time.
