# Little Days

A Streamlit baby log for feeds, naps, diaper changes, weight notes, and memorable moments. Every caregiver creates an account. History is stored in Supabase and separated by authenticated account, so it remains available across devices and is not tied to a browser session or IP address.

## Run locally

Install the dependencies and start Streamlit:

```sh
python -m pip install -r requirements.txt
streamlit run app.py
```

## Configure persistent storage

1. Create a Supabase project.
2. In the Supabase SQL Editor, run the contents of `supabase_schema.sql`.
3. In the Supabase project settings, enable email/password authentication.
4. For local use, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add the project URL and public anon key:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_ANON_KEY = "your-public-anon-key"
```

For Streamlit Community Cloud, enter the same values in the app's Secrets settings instead. Use only the public anon key. Never put a Supabase service-role key in Streamlit secrets for this app. Row-level security policies restrict each account to its own records. The local `secrets.toml` file is ignored by Git.

## Deploy to Streamlit Community Cloud

Push this project to a GitHub repository, then create an app in Streamlit Community Cloud using `app.py` as the entry point. Add `SUPABASE_URL` and `SUPABASE_ANON_KEY` in the app's Secrets settings. Do not commit credentials or publish the app until you are ready.

Anyone can open the deployed app and create an account, but each account sees only its own history. To review the same log on multiple devices, sign in with the same account. Separate accounts have separate, private histories.

## Notes

- Feed entries support breast, bottle, or mixed, with start/end times and an automatically calculated duration. Bottle amounts use US fluid ounces; older milliliter entries are converted for display.
- Naps can be started and ended, or entered as a completed nap from earlier.
- Times use the viewer's browser timezone, so "today" and the daily charts match the caregiver's local clock wherever they are.
- Weight defaults to pounds, with kilograms available as an alternative.
- History is saved to Supabase on every change; it is not stored only in Streamlit session state.
- Use the History tab's importer to bring in a JSON export from the older browser app.
- The history screen can export a JSON backup.
- This is a family log, not a medical device or source of medical advice.