# How to Deploy Your Project Evaluator Web App

You can host this tool for **FREE** using [Streamlit Community Cloud](https://streamlit.io/cloud).

## Prerequisites
1.  A GitHub Account.
2.  This project folder uploaded to a GitHub Repository.

## Step 1: Upload to GitHub
1.  Create a new repository on GitHub (e.g., `project-evaluator`).
2.  Upload the following files to it:
    *   `app.py`
    *   `evaluator.py`
    *   `requirements.txt`
    *   `packages.txt` (if needed, but usually not for this)

## Step 2: Deploy on Streamlit Cloud
1.  Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub.
2.  Click **"New app"**.
3.  Select your GitHub repository (`project-evaluator`).
4.  Set **"Main file path"** to `app.py`.
5.  Click **"Deploy!"**.

## Step 3: Success!
*   In 1-2 minutes, you will get a permanent URL (e.g., `https://project-evaluator.streamlit.app`).
*   You can share this link with anyone. They can upload an Excel file, run the validation, and download the results.

## Configuration (Optional)
*   **Secrets**: If you later add API keys (e.g., for proxies), add them in the Streamlit Cloud "Settings" -> "Secrets".
*   **Reboot**: If the app goes to sleep, just visit the link to wake it up.
