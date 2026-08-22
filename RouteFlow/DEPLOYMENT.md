# Deploying RouteFlow — Free Public Demo

This guide takes a **brand-new person** from zero to a **publicly accessible** RouteFlow demo using
only free tiers. No prior DevOps experience required. Total time: ~20–30 minutes.

**The free stack**

| Piece | Host | Why | Cost |
|------|------|-----|------|
| Database | [Neon](https://neon.tech) | Serverless PostgreSQL, generous free tier | Free |
| Backend API | [Render](https://render.com) | Free Python web service, blueprint support | Free |
| Frontend SPA | [Vercel](https://vercel.com) | Best-in-class free static hosting for Vite | Free |

```mermaid
flowchart LR
    User(("👤 Visitor"))
    subgraph Vercel["Vercel (free)"]
        FE["RouteFlow SPA<br/>(static dist/)"]
    end
    subgraph Render["Render (free)"]
        BE["FastAPI<br/>uvicorn"]
    end
    subgraph Neon["Neon (free)"]
        DB[("PostgreSQL")]
    end
    User -->|"https://your-app.vercel.app"| FE
    FE -->|"https://your-api.onrender.com/api"| BE
    BE -->|"postgresql+psycopg2 (SSL)"| DB
```

> **What you'll need first:** a [GitHub](https://github.com) account, and this project pushed to a
> GitHub repository (see Step 0). Neon, Render and Vercel all let you sign in **with GitHub**.

---

## Step 0 — Push the project to GitHub

If the code isn't on GitHub yet:

```bash
# from the project root
git init
git add .
git commit -m "RouteFlow"
# create an empty repo on github.com, then:
git remote add origin https://github.com/<you>/routeflow.git
git branch -M main
git push -u origin main
```

`.env`, `*.db`, `node_modules/` and `.venv/` are already git-ignored, so no secrets or build
artifacts are committed.

---

## Step 1 — Database on Neon (free PostgreSQL)

1. Go to <https://neon.tech> → **Sign up** (use GitHub).
2. Click **Create project**. Pick a name (`routeflow`) and the region closest to you. Leave the
   Postgres version at the default.
3. After creation, Neon shows a **Connection string** that looks like:

   ```
   postgresql://alex:AbC123@ep-cool-name-12345.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```

4. **Copy it** and turn it into a SQLAlchemy URL by inserting `+psycopg2` after `postgresql`:

   ```
   postgresql+psycopg2://alex:AbC123@ep-cool-name-12345.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
   ```

   Keep `?sslmode=require` — Neon requires SSL. Save this as your **`DATABASE_URL`** for Step 2.

> Neon's free project can sleep when idle; the first query after idle wakes it in a second or two.

---

## Step 2 — Backend API on Render (free web service)

You can deploy with the included **blueprint** (fastest) or **manually**.

### Option A — Blueprint (recommended)

The repo ships a [`render.yaml`](render.yaml) at the root.

1. Go to <https://render.com> → **Sign up** (GitHub) → **New +** → **Blueprint**.
2. Connect your repo. Render reads `render.yaml` and proposes a `routeflow-api` web service.
3. When prompted for environment variables, set:
   - **`DATABASE_URL`** → the Neon URL from Step 1.
   - **`CORS_ORIGINS`** → leave a placeholder for now (e.g. `https://example.vercel.app`); you'll
     update it in Step 4 once you know your Vercel URL.
   - `JWT_SECRET` is generated automatically.
4. Click **Apply**. Render builds and deploys. First build takes a few minutes.

### Option B — Manual web service

1. **New +** → **Web Service** → connect your repo.
2. Configure:

   | Setting | Value |
   |--------|-------|
   | Root Directory | `backend` |
   | Language / Runtime | `Python 3` |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `alembic upgrade head && python -m app.seeds.seed && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Health Check Path | `/health` |
   | Instance Type | **Free** |

3. Add environment variables (**Advanced → Add Environment Variable**):

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | your Neon `postgresql+psycopg2://…?sslmode=require` |
   | `JWT_SECRET` | a long random string (e.g. `python -c "import secrets;print(secrets.token_urlsafe(48))"`) |
   | `CORS_ORIGINS` | your Vercel URL (fill in Step 4) |
   | `ENVIRONMENT` | `production` |
   | `DEBUG` | `false` |
   | `PYTHON_VERSION` | `3.12.7` |
   | `EMAIL_PROVIDER` | `console` |
   | `SMS_ENABLED` | `false` |

4. **Create Web Service**.

**What the start command does:** applies DB migrations (`alembic upgrade head`), runs the
**idempotent** seeder (creates demo users/zones/rates/orders — and self-skips on later restarts),
then starts the API. When it's live you'll get a URL like `https://routeflow-api.onrender.com`.

Verify:

```bash
curl https://routeflow-api.onrender.com/health
# {"status":"healthy"}
```

Open `https://routeflow-api.onrender.com/docs` for interactive Swagger.

> **Free-tier cold starts:** Render free web services spin down after ~15 min idle; the next
> request wakes them in ~50 seconds. That's normal for a demo — just retry once.

---

## Step 3 — Frontend on Vercel (free static hosting)

1. Go to <https://vercel.com> → **Sign up** (GitHub) → **Add New… → Project** → import your repo.
2. Configure the project:

   | Setting | Value |
   |--------|-------|
   | Root Directory | `frontend` |
   | Framework Preset | **Vite** (auto-detected) |
   | Build Command | `npm run build` (default) |
   | Output Directory | `dist` (default) |

3. Add an **Environment Variable**:

   | Key | Value |
   |-----|-------|
   | `VITE_API_BASE_URL` | `https://routeflow-api.onrender.com/api` (your Render URL + `/api`) |

4. Click **Deploy**. You'll get a URL like `https://routeflow.vercel.app`.

The included [`frontend/vercel.json`](frontend/vercel.json) rewrites all routes to `index.html` so
deep links (e.g. `/admin/orders/12`) work on refresh.

> `VITE_*` variables are baked in at **build time**. If you change `VITE_API_BASE_URL` later,
> trigger a **redeploy** so the new value is compiled in.

---

## Step 4 — Connect the two (CORS)

The browser calls the API from the Vercel origin, so the backend must allow it.

1. In **Render → your service → Environment**, set:

   ```
   CORS_ORIGINS = https://routeflow.vercel.app
   ```

   (Use your real Vercel domain. Add multiple origins comma-separated, e.g. include a preview URL.)
2. Save — Render redeploys automatically.

---

## Step 5 — Verify the live demo

1. Open your Vercel URL.
2. On the login screen click a **demo login** button, or sign in with:

   | Role | Email | Password |
   |------|-------|----------|
   | Admin | `admin@routeflow.app` | `Password123!` |
   | Customer | `customer@routeflow.app` | `Password123!` |
   | Agent | `agent@routeflow.app` | `Password123!` |

3. As **Customer** → Create Order → get a live quote → place & confirm.
4. As **Admin** → Orders → auto-assign → watch the timeline; open Analytics for charts.

If login works and the dashboard loads data, you're fully deployed. 🎉

---

## Troubleshooting

| Symptom | Cause & fix |
|--------|-------------|
| First request hangs ~50s, then works | Render free cold start. Normal — retry. |
| Login/API calls fail with a CORS error in the console | `CORS_ORIGINS` on Render doesn't match your exact Vercel origin (scheme + host, no trailing slash). Fix and redeploy. |
| Frontend loads but every API call 404s | `VITE_API_BASE_URL` missing `/api`, or pointed at the wrong host. Fix the Vercel env var and **redeploy**. |
| Backend deploy fails at DB connect | `DATABASE_URL` missing `+psycopg2` or `?sslmode=require`. Use the exact form from Step 1. |
| `relation "users" does not exist` | Migrations didn't run. Ensure the start command includes `alembic upgrade head`. |
| Login says invalid credentials on a fresh DB | Seed didn't run. Check Render logs for the seeder; it prints demo credentials. |
| Deep link 404s on refresh (Vercel) | Ensure `frontend/vercel.json` exists (it's included). |

---

## Alternative free hosts

- **Database:** [Supabase](https://supabase.com) (free Postgres) — same idea; use its
  connection string as `DATABASE_URL` (`postgresql+psycopg2://…`).
- **Backend:** [Fly.io](https://fly.io) (free allowance, use the included `backend/Dockerfile`) or
  [Railway](https://railway.app) (trial credit). Any host that runs a Python web process works —
  just set the same env vars and start command.
- **Frontend:** [Netlify](https://netlify.com) — base directory `frontend`, build `npm run build`,
  publish `dist`, and add a SPA redirect (`/*  /index.html  200`).

---

## Security checklist for a public demo

- [x] `JWT_SECRET` is a strong, unique value (Render's `generateValue` handles this).
- [x] `DEBUG=false` and `ENVIRONMENT=production`.
- [x] `CORS_ORIGINS` lists only your real frontend origin(s).
- [x] No secrets committed — `.env` is git-ignored; secrets live in host dashboards.
- [x] Demo accounts use throwaway credentials and no real personal data.
- [ ] Optional: rotate demo passwords, or disable public registration, before sharing widely.

---

## What "done" looks like

- **Frontend:** `https://<you>.vercel.app`
- **API + docs:** `https://<you>-api.onrender.com/docs`
- **Health:** `https://<you>-api.onrender.com/health` → `{"status":"healthy"}`

Put these URLs at the top of the [README](README.md) so reviewers can click straight through.
