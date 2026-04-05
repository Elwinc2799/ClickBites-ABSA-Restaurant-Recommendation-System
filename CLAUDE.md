# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ClickBites is a full-stack restaurant recommendation system using Aspect-Based Sentiment Analysis (ABSA). The system analyzes restaurant reviews to extract sentiment across five aspects (food, service, price, ambience, miscellaneous) and generates personalized recommendations using cosine similarity.

**Tech Stack:**
- Frontend: Next.js (Pages Router) with TypeScript, TailwindCSS, DaisyUI
- Backend: Flask (Python 3.10) with BERT + VADER for sentiment analysis
- Database: MongoDB
- Data: Yelp Open Dataset

## Development Commands

### Frontend (Next.js)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
yarn install
# or
npm install

# Run development server (http://localhost:3000)
yarn dev
# or
npm run dev

# Build for production
yarn build
# or
npm run build

# Lint code
yarn lint
# or
npm run lint
```

### Backend (Flask)

```bash
# Navigate to backend directory
cd backend

# Create and activate conda environment
conda create --name myenv python=3.10
conda activate myenv

# Install dependencies
conda install --file requirements.txt
# or
conda env update --name myenv --file environment.yml

# Run Flask server (http://localhost:5000)
python3 app.py
```

### Database Setup

```bash
# Navigate to data directory
cd data

# Map photos from Yelp dataset
python3 photos_mapping.py

# Import JSON data to MongoDB
python3 import_json.py
```

## Architecture

### Backend Structure

The Flask backend uses a **blueprint-based architecture** with three main domains:

- `business/` - Restaurant data and operations (routes.py, models.py)
- `review/` - Review data and analysis (routes.py, models.py)
- `user/` - User data and preferences (routes.py, models.py)
- `ai/` - ABSA model pipeline (generate_vector.py)

**Key files:**
- `app.py` - Entry point, registers blueprints, configures CORS
- `database.py` - Singleton MongoDB connection manager
- `config.py` - Configuration (MONGO_URI, MONGO_PORT, MONGO_TIMEOUT) - **not in git**

### AI/ML Pipeline

The ABSA system (`backend/ai/generate_vector.py`) works as follows:

1. **Aspect Extraction**: Fine-tuned BERT model (`fine_tuned_model/`) identifies which aspect (food, service, price, ambience, misc) each review sentence refers to
2. **Sentiment Analysis**: VADER analyzes sentiment polarity for each aspect-opinion pair
3. **Vector Representation**: Each review is represented as a 5D vector (one score per aspect)
4. **Recommendation**: User preference scores and restaurant aspect scores are calculated, then matched using cosine similarity

**Required AI files** (downloaded separately from Google Drive):
- `backend/ai/fine_tuned_model/` - Fine-tuned BERT model directory
- `backend/ai/label_encoder.pkl` - Label encoder for aspect categories
- These files are **NOT** in the repository due to size

### Frontend Structure

Next.js uses the **Pages Router** (not App Router):

- `pages/` - Route pages (index.tsx, dashboard.tsx, results.tsx, profile.tsx, etc.)
- `pages/api/` - API routes (if any client-side API handlers)
- `components/` - Feature-based component organization:
  - `Dashboard/` - User dashboard components
  - `BusinessDetails/` - Restaurant detail views
  - `Layout/` - Layout wrapper components
  - `NavigationBar/` - Navigation components
  - `utils/` - Shared utilities

**Styling**: TailwindCSS + DaisyUI for component library

### API Communication

- Frontend makes REST API calls to Flask backend
- Backend runs on `http://localhost:5000`
- Frontend configured via `next.config.js` with `API_URL` environment variable
- CORS enabled in `app.py` for `http://localhost:3000`

### Database Schema

MongoDB (`ckbt_db`) contains collections for:
- **businesses** - Restaurant data (name, location, categories, aspect scores)
- **reviews** - Review text and generated 5D aspect vectors
- **users** - User data and preference vectors

The `database.py` uses a **singleton pattern** to manage the MongoDB connection.

## Configuration Files

### Frontend Configuration

Create `frontend/next.config.js` (not in git):

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
    reactStrictMode: true,
};

module.exports = {
    env: {
        API_URL: 'http://127.0.0.1:5000',
        NEXT_PUBLIC_GOOGLE_MAPS_API_KEY: 'your-api-key',
    },
};
```

### Backend Configuration

Create `backend/config.py` (not in git):

```python
MONGO_URI = "your-mongodb-connection-string"
MONGO_PORT = 5000
MONGO_TIMEOUT = 1000
```

## Data Flow

1. **User submits preferences** → Frontend sends to Flask API
2. **Flask receives request** → Loads user preference vector from MongoDB
3. **AI pipeline processes** → If new reviews, BERT extracts aspects, VADER analyzes sentiment
4. **Similarity calculation** → Cosine similarity between user preferences and restaurant aspect scores
5. **Results returned** → Ranked recommendations sent to frontend
6. **Frontend displays** → Results page shows personalized restaurant recommendations with aspect scores

## Important Notes

- The fine-tuned BERT model and label encoder must be downloaded manually from Google Drive (see README)
- Photos are processed separately using `data/photos_mapping.py` and stored in `frontend/public/business_photo/`
- The system requires both frontend and backend servers running simultaneously
- MongoDB must be running locally or accessible via the configured MONGO_URI
