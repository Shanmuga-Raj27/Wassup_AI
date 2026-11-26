# Deploying Wassup AI to Streamlit Community Cloud (Free, No Credit Card)

A simple step-by-step guide to deploy your **Wassup AI** Streamlit app (`backend/streamlit/stream_app.py`) to **Streamlit Community Cloud** for free without a credit card.

## Step 1: Create `backend/streamlit/requirements.txt`

Create a new file at `backend/streamlit/requirements.txt` with only the packages needed to run the Streamlit app:

```text
streamlit>=1.67.0
google-genai>=3.6.1
ddgs>=9.16.1
trafilatura>=2.3.1
python-dotenv>=1.2.4
```

*(You do not need `fastapi`, `uvicorn`, or `crawl4ai` for the Streamlit UI deployment.)*

---

## Step 2: Verify `.env` Is Ignored and Push to GitHub

1. Confirm `.env` is listed in `.gitignore` (it is already included) so your API key is **never** uploaded to GitHub.
2. Commit and push your code (including `backend/streamlit/requirements.txt`) to a GitHub repository:
   - Public repositories are unlimited on Streamlit Community Cloud.
   - 1 private repository is also supported on the free tier.

---

## Step 3: Sign In to Streamlit Community Cloud

1. Open [share.streamlit.io](https://share.streamlit.io).
2. Click **Continue with GitHub** and authorize access to your repository.
3. No credit card or billing information is required.

---

## Step 4: Configure Your App Deployment

1. Click **Create app**
2. Fill in the deployment form:
   - **Repository:** `<your-github-username>/Wassup_AI`
   - **Branch:** `main` *(or your active branch)*
   - **Main file path:** `backend/streamlit/stream_app.py`
   - **App URL (optional):** Choose a custom subdomain like `wassupai.streamlit.app`.

---

## Step 5: Add Your `GEMINI_API_KEY` in Secrets

Your app reads `GEMINI_API_KEY` from environment variables in `backend/app/core/config.py`. On Streamlit Cloud, secrets added in the dashboard are automatically injected as environment variables.

1. Before clicking Deploy, click **Advanced settings...**.
2. In the **Secrets** box, paste your API key in TOML format:
   ```toml
   GEMINI_API_KEY = "your-actual-gemini-api-key"
   ```
3. Click **Save**.

---

## Step 6: Deploy & Test

1. Click **Deploy!**.
2. Watch the build logs—Streamlit Cloud will detect `backend/streamlit/requirements.txt`, install the 5 packages, and launch **Wassup AI** in about 1–2 minutes.
3. Once live at `https://<your-app-name>.streamlit.app`, test:
   - A greeting (`"Hi"`) $\rightarrow$ Instant direct reply.
   - A live question (`"Latest Python release"`) $\rightarrow$ `Searched DDGS (Text)...`.
   - A URL (`"Summarize https://fastapi.tiangolo.com/tutorial/first-steps/"`) $\rightarrow$ `Scraped: ...`.

---

## Quick Troubleshooting

| Issue | Fix |
| :--- | :--- |
| **`GEMINI_API_KEY is missing from .env`** | Open your app dashboard $\rightarrow$ **Settings** $\rightarrow$ **Secrets**, ensure `GEMINI_API_KEY = "..."` is saved, then click **Reboot app**. |
| **`ModuleNotFoundError`** | Make sure `backend/streamlit/requirements.txt` is committed and pushed to the same GitHub branch you deployed. |
| **App is sleeping** | Free Streamlit Cloud apps sleep after inactivity (~12–24 hours). Visiting the URL wakes it up in ~15–30 seconds. |
