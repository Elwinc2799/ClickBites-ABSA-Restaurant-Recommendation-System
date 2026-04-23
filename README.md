# ClickBites — ABSA Restaurant Recommendation System

ClickBites is a full-stack restaurant recommendation system powered by Aspect-Based Sentiment Analysis (ABSA). It analyses restaurant reviews to extract sentiment across five aspects — food, service, price, ambience, and miscellaneous — then ranks recommendations for each user using cosine similarity.

**Live site:** https://clickbites.vercel.app

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (Pages Router) · TypeScript · TailwindCSS · DaisyUI |
| Maps | Leaflet + OpenStreetMap (no API key required) |
| Backend | FastAPI (Python 3.10) hosted on HuggingFace Spaces (Docker) |
| Database | Supabase PostgreSQL |
| AI / ML | Fine-tuned BERT (aspect extraction) + VADER (sentiment analysis) |
| Charts | Recharts (RadarChart for aspect score visualisation) |

---

## Architecture

### AI Pipeline

Located in `backend/ai/generate_vector.py`:

1. **Aspect Extraction** — Fine-tuned BERT model classifies each review sentence into one of five aspects: food, service, price, ambience, misc
2. **Sentiment Analysis** — VADER calculates polarity for each aspect-opinion pair
3. **Vector Representation** — Each review becomes a 5D vector (one score per aspect)
4. **Recommendation** — Cosine similarity between a user's preference vector and each restaurant's aspect score vector produces a ranked list

### Backend Structure (`backend/`)

```
app.py          — FastAPI entry point, CORS, router registration
auth.py         — JWT token handling
database.py     — Supabase client singleton
routers/
  business.py   — Restaurant search and detail endpoints
  review.py     — Review submission + ABSA inference
  user.py       — Auth, profile, preference vector
ai/
  generate_vector.py   — ABSA pipeline
  fine_tuned_model/    — BERT model (downloaded separately)
  label_encoder.pkl    — Aspect label encoder (downloaded separately)
```

### Frontend Structure (`frontend/`)

```
pages/
  index.tsx           — Landing page
  dashboard.tsx        — User dashboard
  results.tsx          — Search results with distance filtering
  profile.tsx          — User profile and review history
  business/[id].tsx    — Restaurant detail + AspectRadar chart
  login.tsx / signup.tsx / registerbusiness.tsx
components/
  ResultCard/          — Search result card with aspect score rings
  SharedComponents/    — AspectRadar (recharts RadarChart)
  Map/                 — Leaflet map with drag-to-filter
  Dashboard/           — Profile card, preference input
  NavigationBar/
  Layout/
```

### API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/signup` | Register new user |
| `POST` | `/api/login` | Login, returns JWT |
| `GET` | `/api/results?search_query=` | Search restaurants |
| `GET` | `/api/business/{id}` | Restaurant detail |
| `POST` | `/api/business/{id}/review` | Submit review (triggers ABSA) |
| `GET` | `/api/profile/{user_id}` | User profile + review history |
| `PUT` | `/api/updateprofile/{user_id}` | Update user preferences |
| `GET` | `/api/getHasBusinessFlag/{user_id}` | Check if user owns a business |

---

## Local Development

### Prerequisites

- Node.js 18+ and yarn (or npm)
- Python 3.10 and Conda
- A Supabase project (or use the production instance)

### 1. Frontend

```bash
cd frontend
yarn install

# Create next.config.js
cat > next.config.js << 'EOF'
module.exports = {
    env: {
        API_URL: 'http://127.0.0.1:8000',
    },
};
EOF

yarn dev   # http://localhost:3000
```

> Point `API_URL` at the HuggingFace Spaces backend to skip running the backend locally:
> `API_URL: 'https://elwinc2799-clickbites-api.hf.space'`

### 2. Backend

```bash
cd backend

conda create --name clickbites python=3.10
conda activate clickbites
pip install -r requirements.txt
```

Create a `.env` file:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key
JWT_SECRET=your-jwt-secret
FRONTEND_URL=http://localhost:3000
```

Download the required AI model files from Google Drive and place them in `backend/ai/`:

```
https://drive.google.com/drive/folders/1KruFCU66A7bPACEN3owDbu7JeC3wR6QY?usp=sharing
```

Required files:
- `backend/ai/fine_tuned_model/` — Fine-tuned BERT model directory
- `backend/ai/label_encoder.pkl` — Aspect label encoder

Start the server:

```bash
python app.py   # http://localhost:8000
```

---

## Production Deployment

| Service | Platform | URL |
|---|---|---|
| Frontend | Vercel | https://clickbites.vercel.app |
| Backend | HuggingFace Spaces (Docker) | https://elwinc2799-clickbites-api.hf.space |
| Database | Supabase (ap-southeast-1) | — |

Vercel deploys automatically on every push to `main`. The backend on HuggingFace Spaces is deployed by pushing files to the HF Space repository.

---

## Test Accounts

Use these on the live site (https://clickbites.vercel.app) to try the authenticated flows.

| Role | Email | Password | What to test |
|---|---|---|---|
| Normal user | `testuser@clickbites.test` | `TestUser123!` | Dashboard, profile, preference vector, submit reviews, get personalised recommendations |
| Business owner | `bizowner@clickbites.test` | `BizOwner123!` | Business owner dashboard (linked to *Penang Road Famous Teochew Chendul*), view/edit business details, see aggregated aspect scores |

---

## Database

The Supabase PostgreSQL database (`clickbites-prod`) contains:

- **businesses** — Restaurant data: name, location, categories, aspect scores (`food`, `service`, `price`, `ambience`, `misc`), `photo_url`
- **reviews** — Review text, star rating, aspect vector, user and business foreign keys
- **users** — User credentials, `preference_vector` (5D), `has_business_id`

The backend uses the Supabase Python REST client (`supabase-py`) exclusively — no direct PostgreSQL connections — to ensure compatibility with HuggingFace Spaces (IPv4-only).

---

## License

This project is licensed under the terms of the MIT license.
