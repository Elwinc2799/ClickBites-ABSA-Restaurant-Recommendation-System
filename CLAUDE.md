# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ClickBites is a full-stack restaurant recommendation system using Aspect-Based Sentiment Analysis (ABSA). The system analyzes restaurant reviews to extract sentiment across five aspects (food, service, price, ambience, miscellaneous) and generates personalized recommendations using cosine similarity.

**Tech Stack:**
- Frontend: Next.js 15 (Pages Router) with TypeScript, TailwindCSS, DaisyUI, Leaflet + OpenStreetMap
- Backend: FastAPI (Python 3.10) hosted on HuggingFace Spaces (Docker SDK)
- Database: Supabase PostgreSQL (ap-southeast-1)
- AI/ML: Fine-tuned BERT (aspect extraction) + VADER (sentiment analysis)

**Live site:** https://clickbites.vercel.app  
**Backend API:** https://elwinc2799-clickbites-api.hf.space

**Legacy Flask backend** is preserved in `backend_legacy/` for reference only — do not modify it.

## Development Commands

### Frontend (Next.js)

```bash
cd frontend

# Install dependencies
npm install

# Run development server (http://localhost:3000)
npm run dev

# Build for production
npm run build

# Lint code
npm run lint
```

### Backend (FastAPI)

```bash
cd backend

# Create and activate conda environment
conda create --name clickbites python=3.10
conda activate clickbites

pip install -r requirements.txt

# Download the spaCy model used by the ABSA pipeline (NOT pulled in by requirements.txt)
python -m spacy download en_core_web_sm

# Run FastAPI server (http://localhost:8000)
python3 app.py
```

## Architecture

### Backend Structure (`backend/`)

The FastAPI backend uses a **router-based architecture**:

- `routers/business.py` - Restaurant search and detail endpoints
- `routers/review.py` - Review submission + ABSA inference
- `routers/user.py` - Auth, profile, preference vector updates
- `ai/generate_vector.py` - ABSA pipeline (BERT + VADER)

**Key files:**
- `app.py` - Entry point, registers routers, configures CORS
- `auth.py` - JWT token creation and verification
- `database.py` - Supabase REST client (`supabase-py`) used by all routers, plus a best-effort asyncpg pool (`get_pool`/`close_pool`) that `app.py` initializes but no router actually uses

**Important:** All router data access goes through the Supabase Python REST client (`supabase.table(...)` / `supabase.rpc(...)`) — treat it as the only working data path. `database.py` *does* define a direct asyncpg pool and `app.py` initializes it on startup, but the call is non-fatal and no router uses it: it targets Supabase's direct DB host (IPv6-only), which is unreachable from HuggingFace Spaces (IPv4-only). The asyncpg pool is therefore vestigial — don't add queries through it expecting them to work in production.

### AI/ML Pipeline

The ABSA system (`backend/ai/generate_vector.py`) works as follows:

1. **Aspect Extraction**: Fine-tuned BERT model classifies each review sentence into food/service/price/ambience/misc
2. **Sentiment Analysis**: VADER analyzes polarity for each aspect-opinion pair
3. **Vector Representation**: Each review is represented as a 5D vector (one score per aspect)
4. **Recommendation**: Cosine similarity between user preference vector and restaurant aspect score vector

**Required AI files** (downloaded separately from Google Drive):
- `backend/ai/fine_tuned_model/` - Fine-tuned BERT model directory
- `backend/ai/label_encoder.pkl` - Label encoder for aspect categories
- These files are **NOT** in the repository due to size

### Frontend Structure

Next.js uses the **Pages Router** (not App Router):

- `pages/` - Route pages (index.tsx, dashboard.tsx, results.tsx, profile.tsx, etc.)
- `components/` - Feature-based component organization:
  - `Dashboard/` - User dashboard components
  - `BusinessDetails/` - Restaurant detail views + AddReviewForm
  - `SharedComponents/` - AspectRadar (recharts RadarChart)
  - `Map/` - Leaflet map with drag-to-filter
  - `NavigationBar/` - NavBar
  - `Layout/` - Footer, Background
  - `utils/` - UseLoginStatus, UseLoadingAnimation, UseHasBusinessStatus

**Styling**: TailwindCSS + DaisyUI for component library

### API Communication

- Frontend makes REST API calls to FastAPI backend via `process.env.API_URL`
- Backend runs on `http://localhost:8000` locally
- Production API: `https://elwinc2799-clickbites-api.hf.space`
- CORS enabled in `app.py` for `http://localhost:3000` and the Vercel frontend URL

### Database Schema (Supabase PostgreSQL)

- **businesses** - Restaurant data: name, location, categories, `aspect_scores` (JSONB with food/service/price/ambience/misc), `photo_url`
- **reviews** - Review text, star rating, `aspect_vector` (pgvector), `user_id`, `business_id`
- **users** - Credentials, `preference_vector` (5D), `has_business_id`

## Configuration Files

### Frontend Configuration

Create `frontend/next.config.js` (not in git):

```javascript
module.exports = {
    env: {
        API_URL: 'http://127.0.0.1:8000',
    },
};
```

To use the production backend instead of running locally:
```javascript
module.exports = {
    env: {
        API_URL: 'https://elwinc2799-clickbites-api.hf.space',
    },
};
```

### Backend Configuration

Create `backend/.env` (not in git):

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
JWT_SECRET=your-jwt-secret
FRONTEND_URL=http://localhost:3000
```

## Data Flow

1. **User submits preferences** → Frontend sends to FastAPI
2. **FastAPI receives request** → Reads user preference vector from Supabase
3. **AI pipeline processes** → BERT extracts aspects, VADER analyzes sentiment, updates vectors
4. **Similarity calculation** → Cosine similarity between user preferences and restaurant aspect scores
5. **Results returned** → Ranked recommendations sent to frontend
6. **Frontend displays** → Results page with aspect score rings, distance filtering via geolocation

## Important Notes

- The fine-tuned BERT model and label encoder must be downloaded manually from Google Drive (see README)
- Photos: `frontend/public/business_photo/` contains Yelp dataset photos; missing photos fall back to random food category images (`cafe.jpg`, `chinese.jpg`, etc.)
- Maps use Leaflet + OpenStreetMap — no API key required
- Distance filtering uses browser geolocation (20km radius); fires automatically on page load if permission is granted
