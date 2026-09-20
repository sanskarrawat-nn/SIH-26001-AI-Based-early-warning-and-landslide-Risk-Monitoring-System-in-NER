# Online Cloud Deployment Guide: AI-Based early warning and landslide Risk Monitoring System in NER

This system is fully architected for 100% turnkey deployment on all major cloud hosting platforms.

---

## 🚀 Option 1: Render (Recommended — Free Tier & 1-Click Blueprint)

The repository includes `render.yaml` infrastructure-as-code.

### Step 1: Push Code to GitHub
```bash
# Verify all changes are committed
git add -A
git commit -m "feat: production cloud readiness"

# Create a repo on GitHub (e.g. using gh CLI or web UI)
gh repo create landslide-early-warning-system --public --source=. --remote=origin --push
```

### Step 2: Deploy on Render
1. Go to [dashboard.render.com](https://dashboard.render.com).
2. Click **New +** $\to$ **Blueprint**.
3. Connect your GitHub repository.
4. Render will automatically parse `render.yaml` and provision:
   - **`ner-landslide-command-center`**: Web Service (Docker runtime, Free plan).
   - **`ner-landslide-db`**: PostgreSQL 16 database (Free plan).
5. Click **Apply**.
6. Once deployed, Render will provide a public URL: `https://ner-landslide-command-center.onrender.com`.

> **Note:** If you prefer zero-cost without a separate PostgreSQL database, the app automatically falls back to built-in SQLite when `DATABASE_URL` is omitted.

---

## 🚂 Option 2: Railway

Railway provides zero-config deployment using Docker or Nixpacks.

1. Install Railway CLI: `npm i -g @railway/cli` or use [railway.app](https://railway.app).
2. Run in project root:
   ```bash
   railway login
   railway init
   railway up
   ```
3. (Optional) Add a PostgreSQL database:
   - In your Railway project dashboard, click **+ New** $\to$ **Database** $\to$ **PostgreSQL**.
   - Railway will automatically connect `DATABASE_URL`.
4. Generate a public domain:
   - In Settings $\to$ **Networking** $\to$ **Generate Domain**.

---

## 🪂 Option 3: Fly.io

1. Install flyctl: `brew install flyctl` (or `curl -L https://fly.io/install.sh | sh`).
2. Run in project root:
   ```bash
   fly auth login
   fly launch --no-deploy
   ```
3. Deploy:
   ```bash
   fly deploy
   ```

---

## ⚡ Option 4: Split Hosting (Vercel Frontend + Render/Railway Backend)

If you prefer hosting the React frontend on Vercel's global CDN:

1. **Deploy Backend on Render or Railway:**
   - Deploy backend to Render/Railway to get `https://your-backend.onrender.com`.
2. **Deploy Frontend on Vercel:**
   - Import repository to [Vercel](https://vercel.com).
   - Set **Root Directory** to `frontend`.
   - Add Environment Variable:
     - `VITE_API_URL` = `https://your-backend.onrender.com/api`
   - Click **Deploy**.

---

## 🐳 Option 5: Self-Hosted Linux VPS (Ubuntu/Debian)

```bash
# Clone and enter repo
git clone <repo-url> landslide-early-warning-system
cd landslide-early-warning-system

# Run with Docker Compose
docker compose up --build -d

# Check status
docker compose ps
curl http://localhost:8000/health
```

---

## 🔑 Environment Variables Reference

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `PORT` | `8000` | Port listened to by uvicorn (automatically bound by Render/Railway) |
| `DATABASE_URL` | `sqlite:///./landslide_system.db` | PostgreSQL connection string or SQLite fallback |
| `WEATHER_PROVIDER` | `hybrid` | `openmeteo` (live API), `simulated` (sensor simulator), or `hybrid` (auto-failover) |
| `SERVE_STATIC_FRONTEND`| `true` | Enables FastAPI to serve the compiled React SPA at `/` |
| `FRONTEND_DIST_DIR` | `/app/frontend/dist` | Directory containing production Vite assets |
| `DEFAULT_THRESHOLD_LOW` | `25.0` | Boundary for LOW risk |
| `DEFAULT_THRESHOLD_MODERATE` | `50.0` | Boundary for MODERATE risk |
| `DEFAULT_THRESHOLD_HIGH` | `75.0` | Boundary for HIGH/SEVERE risk |

