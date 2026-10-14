# 🚀 DEPLOYMENT GUIDE

## AI Governance and Ethics Platform
### Ethical Guideline and Governance Framework for AI Use in Nigerian Tech Startups

From your laptop to a **live link you can send your supervisor** — using only free
services.

| Option | Cost | Best for | Difficulty |
|---|---|---|---|
| **A. GitHub + Streamlit Community Cloud** | Free | A permanent public link | Easy |
| **B. Temporary public link from your laptop** | Free | A live demo right now, no account | Easiest |
| **C. Hugging Face Spaces** | Free | An alternative host | Easy |

**Recommended: Option A**, with Option B as an instant fallback on defence day.

> ⚠️ **Read Section D before deploying.** The database is a local SQLite file. On a
> cloud host the filesystem is ephemeral, which is *fine for a demonstration* but must
> be understood before you promise persistence.

---

# PART A — GitHub + Streamlit Community Cloud

## A1. Prerequisites

1. Free **GitHub** account → https://github.com/signup
2. Free **Streamlit Community Cloud** account → https://share.streamlit.io (sign in with
   GitHub; no card required)
3. **Git** installed → https://git-scm.com/download/win → verify with `git --version`

## A2. Prepare the folder

```bat
cd C:\Users\TECHDEBIA\Documents\pro\aigovtech
dir
```

Confirm you can see `app.py`, `setup_db.py`, `requirements.txt`, `auth.py`, `db.py`,
`risk_calculator.py`, `audit_logger.py`, `reports.py`.

### ⚠️ Two things to check before pushing

**1. The database must NOT be pushed.** `.gitignore` already excludes `data/*.db`. This
is deliberate: the app **creates and seeds the database automatically** on first run
(`ensure_database()` in `app.py`), which is exactly what makes cloud deployment work
with no setup at all.

**2. The virtual environment must NOT be pushed.** `venv/` is already ignored.

```bat
git status --porcelain
```

If you see `venv/` or `data/aigovtech.db` listed, fix `.gitignore` before continuing.

## A3. Push to GitHub

Create the repository at https://github.com/new:

| Field | Value |
|---|---|
| Repository name | `ai-governance-nigerian-startups` |
| Description | AI Governance and Ethics Platform — framework for Nigerian tech startups |
| Visibility | **Public** (required for the free Streamlit tier) |
| Initialise with README | **Leave unticked** |

Then:

```bat
cd C:\Users\TECHDEBIA\Documents\pro\aigovtech

git init
git branch -M main
git add .
git commit -m "AI Governance and Ethics Platform - ethical guideline and governance framework for AI use in Nigerian tech startups"
git remote add origin https://github.com/YOUR-USERNAME/ai-governance-nigerian-startups.git
git push -u origin main
```

Replace `YOUR-USERNAME`. Git opens a browser to authenticate.

For later changes:

```bat
git add .
git commit -m "Describe what you changed"
git push
```

## A4. Deploy on Streamlit Community Cloud

1. Go to **https://share.streamlit.io** and sign in with GitHub
2. Click **Create app** → **Deploy a public app from GitHub**
3. Fill in:

| Field | Value |
|---|---|
| Repository | `YOUR-USERNAME/ai-governance-nigerian-startups` |
| Branch | `main` |
| Main file path | `app.py` |
| App URL | e.g. `ai-governance-nigeria` |
| Python version (Advanced settings) | `3.11` (or 3.10) |

4. Click **Deploy!**

The first build takes **2–4 minutes**. When it finishes the app opens automatically and
creates its own seeded database.

### If the build fails on a very new Python

Set **Advanced settings → Python version → 3.11**, or add a file named `runtime.txt`
containing exactly:

```
python-3.11
```

## A5. Share the live link

```
https://ai-governance-nigeria.streamlit.app
```

Suggested e-mail to your supervisor:

> **Subject:** AI Governance and Ethics Platform — live demonstration
>
> Good day sir/ma. The platform is deployed and can be viewed at the link below:
>
> **https://ai-governance-nigeria.streamlit.app**
>
> **Sign-in accounts** (the platform is role-based, so please try at least two)
> * Administrator — `admin@startup.ng` / `admin123`
> * Startup Developer — `dev@startup.ng` / `dev123`
> * AI Governance Officer — `governance@startup.ng` / `gov123`
> * Auditor (read-only) — `auditor@startup.ng` / `audit123`
> * Reporter (any employee) — `reporter@startup.ng` / `rep123`
>
> Suggested path: sign in as the **Administrator** and open the **Compliance
> Dashboard**, then sign in as the **Developer** to register an AI system and score its
> risk. The risk score is calculated live from the six weighted dimensions.
>
> Thank you.

---

# PART B — A Temporary Public Link (no account needed)

Use this if your supervisor asks to see it **right now**, or as a backup on defence day.

```bat
setup_and_start.bat
```

Then, in a **new** Command Prompt (download `cloudflared.exe` once from
https://github.com/cloudflare/cloudflared/releases/latest — rename to `cloudflared.exe`):

```bat
cloudflared.exe tunnel --url http://localhost:8501
```

It prints a public URL such as `https://random-words.trycloudflare.com`. It works while
the Command Prompt and the platform stay open. The URL changes each restart, so this is
for live demonstrations only.

Alternative: `ngrok http 8501` (requires a free ngrok account).

---

# PART C — Hugging Face Spaces

1. Create a free account at https://huggingface.co/join
2. **New → Space**
3. SDK: **Streamlit**, Hardware: **CPU basic (free)**
4. Upload `app.py`, `setup_db.py`, `auth.py`, `db.py`, `risk_calculator.py`,
   `audit_logger.py`, `reports.py`, `requirements.txt` and `README.md`
5. Hugging Face builds automatically

Spaces also has an ephemeral filesystem (see Section D) and sleeps after inactivity —
the first visit afterwards takes about 30 seconds to wake.

---

# PART D — Important: how the cloud database behaves

Streamlit Community Cloud and Hugging Face Spaces give each app an **ephemeral
filesystem**:

* On the **first** visit the platform detects that no database exists, creates it and
  seeds the demonstration data automatically — so the app is never empty.
* Records you create are kept **while the app is running**, but a **reboot or redeploy
  resets everything** to the seeded demonstration state.
* This is **ideal for a demonstration** (the data is always clean and predictable) but
  it is **not** suitable for real governance records.

**For a real deployment**, replace SQLite in `db.py` with a hosted database. Free tiers
that work well: **Supabase** or **Neon** (PostgreSQL). Because every database call in
this platform goes through the four helpers in `db.py`
(`get_connection`, `execute_query`, `fetch_all`, `fetch_one`), only that one file needs
to change — no page code is affected.

**For the defence itself, run the platform locally.** It is faster, the data persists,
and there is no dependency on the venue's internet.

---

# PART E — Deployment Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `No module named streamlit` | `requirements.txt` not committed | `git add requirements.txt && git commit -m "add requirements" && git push` |
| Build fails on numpy/pyarrow | Python version too new | Set Python **3.11** in Advanced settings, or add `runtime.txt` |
| "database could not be initialised" | The `data/` folder could not be created | Reboot the app; the platform creates `data/` automatically |
| Charts do not appear | Plotly still loading | Wait, or switch page and return |
| `Error: Your app is having trouble` | Unhandled exception | **Manage app → Logs** and read the traceback |
| Login fails with the demo password | Database re-seeded differently | **Manage app → Reboot**, then use the seeded credentials |
| Changes on GitHub not visible | Streamlit cached the app | **Manage app → Reboot** |
| Charts slow on a big dataset | Plotly rendering | Expected; the seeded dataset is small by design |

---

# PART F — Pre-Submission Checklist

| ✔ | Item |
|---|---|
| ☐ | GitHub repository is **public** and contains no `venv/` or `.db` files |
| ☐ | `requirements.txt` is committed and installs cleanly from scratch |
| ☐ | The live URL opens in an **incognito** window (proves it is public) |
| ☐ | Admin signs in on the live link and the dashboard renders with charts |
| ☐ | Developer signs in, registers a system, and the risk score calculates |
| ☐ | Auditor signs in and sees the audit trail but **no** edit buttons |
| ☐ | Reporter signs in and sees **only** the Incidents page |
| ☐ | A report downloads and opens correctly |
| ☐ | `python tests\functional_test.py` → **0 failures** |
| ☐ | `python tests\ui_smoke_test.py` → **0 failures** |
| ☐ | `DEMO_SCRIPT.txt` has been rehearsed at least twice |
| ☐ | Live link **and** credentials e-mailed to your supervisor |

---

# PART G — Command Reference

```bat
REM ---- run locally -----------------------------------------------------------
setup_and_start.bat                 normal start
setup_and_start.bat reset           wipe and re-seed the demonstration data
setup_and_start.bat fresh           ignore myenv, build a clean local venv

REM ---- manual control -------------------------------------------------------
myenv\Scripts\activate              activate your environment
python setup_db.py --reset          rebuild the database
python -m streamlit run app.py      start the platform manually
python tests\functional_test.py     logic test suite
python tests\ui_smoke_test.py       role-based interface test

REM ---- git ------------------------------------------------------------------
git status                          what has changed
git add .                           stage everything
git commit -m "message"             commit
git push                            push to GitHub

REM ---- public tunnel for a live demo ----------------------------------------
cloudflared.exe tunnel --url http://localhost:8501
ngrok http 8501
```

---

*AI Governance and Ethics Platform · Ethical Guideline and Governance Framework for AI
Use in Nigerian Tech Startups · Built entirely on free and open-source tooling.*
