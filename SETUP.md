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

## 6. (Optional but recommended) Natural-sounding voice

By default narration uses a free, robotic offline voice (espeak-ng). To use a
natural voice instead, reusing the same Google Cloud project from step 2:

1. In [Google Cloud Console](https://console.cloud.google.com/), same project
   as before, go to **APIs & Services > Library**, search **Cloud Text-to-Speech
   API**, click **Enable**.
2. You'll be prompted to attach a **billing account** (a card on file) — this
   is required by Google to enable the API at all. At this project's usage
   (~1 short/day, a few hundred characters each) you'll stay well under the
   1-million-character/month free tier, so actual cost should be $0, but the
   card itself is a real requirement, not optional.
3. Go to **IAM & Admin > Service Accounts > Create Service Account**. Any name
   is fine. Grant it the role **Cloud Text-to-Speech User**. Create it.
4. Click the new service account > **Keys** tab > **Add Key > Create new key**
   > **JSON**. This downloads a JSON key file.
5. Open that file, copy its entire contents, and add it as a GitHub repo
   secret named `GOOGLE_TTS_CREDENTIALS_JSON` (**Settings > Secrets and
   variables > Actions > New repository secret** — paste the whole JSON as
   the value).
6. **Delete the downloaded key file afterwards.**

Once that secret exists, every future run automatically uses the natural
voice — no code changes needed. If it's ever missing or fails, rendering
falls back to the robotic voice rather than breaking.

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
