# ClickBites Production Deployment Design

**Date:** 2026-04-05  
**Status:** Approved  
**Author:** Claude Code with Elwin

## Overview

This document describes the production deployment strategy for ClickBites, an ABSA (Aspect-Based Sentiment Analysis) restaurant recommendation system. The deployment modernizes the stack from a local-only application to a production-ready system using free-tier cloud services.

## Goals

1. Deploy ClickBites to production on 100% free tier infrastructure
2. Modernize the tech stack (Bun runtime, FastAPI, PostgreSQL with pgvector)
3. Migrate from MongoDB to Supabase PostgreSQL with vector similarity support
4. Host ML model (fine-tuned BERT) on infrastructure designed for it (Hugging Face Spaces)
5. Achieve zero monthly cost while maintaining functionality
6. Support rare review submissions (~few per month) with acceptable latency

## Non-Goals

- Real-time, low-latency review processing (cold starts acceptable)
- Handling high traffic volumes (demo/portfolio project)
- Multi-region deployment
- Advanced monitoring/observability beyond free tier offerings

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Vercel + Bun)                                    │
│  - Next.js 15 with TypeScript                               │
│  - Deployed to Vercel with Bun runtime                      │
│  - Static assets served via CDN                             │
│  - Environment: API URL, Google Maps, Supabase              │
└─────────────────┬───────────────────────────────────────────┘
                  │ HTTPS/REST API
┌─────────────────▼───────────────────────────────────────────┐
│  Backend API (Hugging Face Spaces)                          │
│  - FastAPI (migrated from Flask)                            │
│  - BERT model + VADER sentiment analysis                    │
│  - Business/Review/User REST endpoints                      │
│  - Model files stored in HF repo (Git LFS)                  │
└─────────────────┬───────────────────────────────────────────┘
                  │ psycopg2/asyncpg
┌─────────────────▼───────────────────────────────────────────┐
│  Database (Supabase PostgreSQL)                             │
│  - businesses, reviews, users tables                        │
│  - pgvector extension for cosine similarity                 │
│  - Automatic backups (7 days)                               │
└─────────────────────────────────────────────────────────────┘
                  
┌─────────────────────────────────────────────────────────────┐
│  Storage (Supabase Storage)                                 │
│  - Business photos (94MB) in public bucket                  │
│  - CDN-backed URLs                                          │
└─────────────────────────────────────────────────────────────┘
```

### Component Details

#### Frontend (Vercel + Bun)

**Current state:**
- Next.js 15.5.10 with TypeScript
- Using npm/yarn for package management
- Static photos in `frontend/public/business_photo/`
- Environment variables in `next.config.js`

**Target state:**
- Bun runtime for faster installs and builds
- TypeScript configuration (`next.config.ts`)
- Photos fetched from Supabase Storage
- Environment variables managed in Vercel dashboard

**Why Vercel:**
- Native Next.js support with zero-config deployment
- Supports Bun runtime (confirmed via Vercel docs)
- Generous free tier: 100GB bandwidth, unlimited sites
- Automatic HTTPS, CDN, and preview deployments
- Easy environment variable management

**Why Bun:**
- 2-5x faster package installation vs npm
- Built-in TypeScript support
- Faster dev server startup
- Compatible with Next.js ecosystem
- Already installed locally (v1.3.7)

#### Backend (Hugging Face Spaces with FastAPI)

**Current state:**
- Flask 2.2.2 with blueprints (business, review, user)
- PyMongo for MongoDB connection
- Heavy ML dependencies (PyTorch, transformers, BERT)
- AI model files downloaded separately from Google Drive
- Singleton database connection pattern

**Target state:**
- FastAPI with routers (business, review, user)
- asyncpg/psycopg2 for PostgreSQL connection
- Same ML dependencies
- Model files committed to HF repo (Git LFS automatic)
- Async database connection pooling

**Migration: Flask → FastAPI**

Key changes:
- Blueprint → Router pattern
- `@app.route()` → `@app.get()/@app.post()` decorators
- Request validation via Pydantic models
- Async/await for database operations
- Native OpenAPI/Swagger documentation

Example transformation:
```python
# Flask (before)
@business_bp.route("/api/business", methods=["POST"])
def registerBusiness():
    business = json.loads(request.form.get("business"))
    user_id = decodeToken()
    # ...

# FastAPI (after)
@router.post("/api/business")
async def register_business(
    business: BusinessCreate,
    user_id: str = Depends(get_current_user)
):
    # ...
```

**Why Hugging Face Spaces:**
- Designed specifically for ML model hosting
- Always-on free tier (no cold starts on database)
- Native support for transformers, PyTorch, BERT
- Git LFS handles large model files automatically
- Can host model files directly in repo (no separate download)
- 2GB persistent storage for model files
- Built-in API documentation UI

**Why FastAPI:**
- Native async support (better for I/O-bound database operations)
- Automatic request/response validation with Pydantic
- Built-in OpenAPI documentation (useful for portfolio)
- Type hints improve code quality and IDE support
- Better performance than Flask for async workloads
- Modern Python best practices

#### Database (Supabase PostgreSQL)

**Current state:**
- MongoDB Atlas (deleted, needs recreation)
- Three collections: business, review, user
- Cosine similarity calculated in Python (sklearn)
- Photos stored in frontend/public directory

**Target state:**
- PostgreSQL with pgvector extension
- Three tables: businesses, reviews, users
- Cosine similarity calculated in SQL queries
- Photos stored in Supabase Storage

**Schema Design:**

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Businesses table
CREATE TABLE businesses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id VARCHAR(255) UNIQUE NOT NULL,  -- Original Yelp ID
  name VARCHAR(500) NOT NULL,
  address TEXT,
  city VARCHAR(255),
  state VARCHAR(50),
  postal_code VARCHAR(20),
  latitude DECIMAL(10, 8),
  longitude DECIMAL(11, 8),
  stars DECIMAL(2, 1),
  review_count INTEGER DEFAULT 0,
  categories TEXT[],  -- PostgreSQL array
  aspect_scores JSONB,  -- {food: 0.8, service: 0.6, ...}
  photo_url TEXT,  -- Supabase Storage public URL
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_business_id ON businesses(business_id);
CREATE INDEX idx_city ON businesses(city);
CREATE INDEX idx_categories ON businesses USING GIN(categories);

-- Reviews table
CREATE TABLE reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_id VARCHAR(255) UNIQUE NOT NULL,
  business_id VARCHAR(255) REFERENCES businesses(business_id) ON DELETE CASCADE,
  user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  stars DECIMAL(2, 1),
  aspect_vector VECTOR(5),  -- [food, service, price, ambience, misc]
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_review_business ON reviews(business_id);
CREATE INDEX idx_review_user ON reviews(user_id);
CREATE INDEX idx_aspect_vector ON reviews USING ivfflat (aspect_vector vector_cosine_ops);

-- Users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  preference_vector VECTOR(5),  -- Calculated from user's review history
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_id ON users(user_id);
CREATE INDEX idx_email ON users(email);
CREATE INDEX idx_preference_vector ON users USING ivfflat (preference_vector vector_cosine_ops);
```

**Vector Similarity in SQL:**

Instead of loading all data into Python and using sklearn:

```sql
-- Get restaurant recommendations for a user
SELECT 
  b.business_id,
  b.name,
  b.aspect_scores,
  1 - (b.aspect_vector <=> u.preference_vector) AS similarity_score
FROM businesses b
CROSS JOIN users u
WHERE u.user_id = $1
ORDER BY b.aspect_vector <=> u.preference_vector
LIMIT 20;
```

This is significantly faster than the current approach.

**Why Supabase:**
- Free tier: 500MB database, 1GB storage, 2GB bandwidth
- PostgreSQL with pgvector extension (vector similarity built-in)
- Automatic daily backups (7 days retention)
- Built-in storage for photos (CDN-backed)
- Real-time subscriptions available (future enhancement)
- Built-in auth (could replace JWT implementation later)
- No cold starts (unlike MongoDB Atlas free tier alternatives)

**Why PostgreSQL + pgvector:**
- Vector similarity operations in database (faster than Python)
- Better indexing for high-dimensional vectors (IVFFlat)
- JSONB for flexible schema while keeping relational benefits
- More robust transaction support than MongoDB
- Better tooling and monitoring
- Industry-standard for production applications

#### Storage (Supabase Storage)

**Current state:**
- 94MB of business photos in `frontend/public/business_photo/`
- Photos served from Next.js public directory
- Committed to git (bloats repository)

**Target state:**
- Photos in Supabase Storage public bucket
- CDN-backed URLs
- Photos removed from git repository
- References stored in database

**Migration process:**
1. Create public bucket: `business-photos`
2. Upload all photos with business_id as filename
3. Get public URLs
4. Store URLs in `businesses.photo_url` column
5. Update frontend components to use these URLs
6. Remove photos from git and add to `.gitignore`

## Data Migration Strategy

### Phase 1: Export from MongoDB/JSON

**Data sources:**
- `data/business.json` (1.3MB)
- `data/review.json` (3.6MB)
- `data/user.json` (2.1MB)
- `frontend/public/business_photo/` (94MB)

**Extraction script** (`scripts/export_mongodb.py`):
```python
import json
from pathlib import Path

def export_collections():
    """Load existing JSON data files"""
    business_data = json.load(open('data/business.json'))
    review_data = json.load(open('data/review.json'))
    user_data = json.load(open('data/user.json'))
    return business_data, review_data, user_data
```

### Phase 2: Transform for PostgreSQL

**Transformation script** (`scripts/transform_data.py`):

Key transformations:
1. MongoDB ObjectId → UUID (generate new UUIDs)
2. Nested documents → JSONB columns or separate tables
3. Array fields → PostgreSQL arrays
4. Aspect vectors → pgvector format `[0.1, 0.2, 0.3, 0.4, 0.5]`
5. Null handling (PostgreSQL stricter than MongoDB)

Example:
```python
def transform_business(mongo_doc):
    """Transform MongoDB business document to PostgreSQL row"""
    return {
        'business_id': mongo_doc['business_id'],
        'name': mongo_doc['name'],
        'address': mongo_doc.get('address'),
        'city': mongo_doc.get('city'),
        'state': mongo_doc.get('state'),
        'postal_code': mongo_doc.get('postal_code'),
        'latitude': mongo_doc.get('latitude'),
        'longitude': mongo_doc.get('longitude'),
        'stars': mongo_doc.get('stars'),
        'review_count': mongo_doc.get('review_count', 0),
        'categories': mongo_doc.get('categories', []),
        'aspect_scores': mongo_doc.get('aspect_scores', {}),
        'photo_url': None,  # Will be updated after photo upload
    }
```

### Phase 3: Upload Photos to Supabase Storage

**Upload script** (`scripts/upload_photos.py`):
```python
from supabase import create_client
from pathlib import Path

def upload_photos(supabase_url, supabase_key):
    """Upload all business photos to Supabase Storage"""
    supabase = create_client(supabase_url, supabase_key)
    photo_dir = Path('frontend/public/business_photo')
    
    photo_urls = {}
    for photo_path in photo_dir.glob('*.jpg'):
        business_id = photo_path.stem
        with open(photo_path, 'rb') as f:
            result = supabase.storage.from_('business-photos').upload(
                f'{business_id}.jpg',
                f,
                {'content-type': 'image/jpeg'}
            )
        photo_urls[business_id] = supabase.storage.from_('business-photos').get_public_url(f'{business_id}.jpg')
    
    return photo_urls
```

### Phase 4: Insert into PostgreSQL

**Insert script** (`scripts/import_postgresql.py`):
```python
import asyncpg

async def insert_data(database_url, businesses, reviews, users, photo_urls):
    """Insert transformed data into PostgreSQL"""
    conn = await asyncpg.connect(database_url)
    
    # Insert businesses
    for business in businesses:
        business['photo_url'] = photo_urls.get(business['business_id'])
        await conn.execute("""
            INSERT INTO businesses (business_id, name, address, ...)
            VALUES ($1, $2, $3, ...)
        """, business['business_id'], business['name'], ...)
    
    # Insert users (before reviews due to foreign key)
    for user in users:
        await conn.execute("""
            INSERT INTO users (user_id, name, email, ...)
            VALUES ($1, $2, $3, ...)
        """, ...)
    
    # Insert reviews
    for review in reviews:
        await conn.execute("""
            INSERT INTO reviews (review_id, business_id, user_id, ...)
            VALUES ($1, $2, $3, ...)
        """, ...)
    
    await conn.close()
```

### Data Validation

After migration, run validation queries:
```sql
-- Count records
SELECT 'businesses' as table_name, COUNT(*) FROM businesses
UNION ALL
SELECT 'reviews', COUNT(*) FROM reviews
UNION ALL
SELECT 'users', COUNT(*) FROM users;

-- Validate foreign keys
SELECT COUNT(*) FROM reviews r 
LEFT JOIN businesses b ON r.business_id = b.business_id 
WHERE b.business_id IS NULL;  -- Should be 0

-- Validate vectors
SELECT COUNT(*) FROM reviews WHERE aspect_vector IS NULL;  -- Should be 0
SELECT COUNT(*) FROM users WHERE preference_vector IS NULL;  -- May have some NULLs for new users
```

## Code Migration Details

### Frontend Changes

**1. Package management migration**

```bash
# Remove old lock files
rm package-lock.json yarn.lock

# Install with Bun
bun install

# Verify build works
bun run build
```

**2. Configuration updates**

Convert `next.config.js` → `next.config.ts`:

```typescript
import type { NextConfig } from 'next';

const config: NextConfig = {
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '',
    NEXT_PUBLIC_GOOGLE_MAPS_API_KEY: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '',
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL || '',
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '',
  },
  images: {
    domains: [
      'your-project.supabase.co',  // Supabase Storage
    ],
  },
};

export default config;
```

**3. API client updates**

Update photo URLs:
```typescript
// Before
<img src={`/business_photo/${businessId}.jpg`} />

// After
<img src={business.photo_url} alt={business.name} />
```

Update API base URL (already using `process.env.API_URL`):
```typescript
// No changes needed - already using environment variable
const API_URL = process.env.API_URL || 'http://127.0.0.1:5000';
```

**4. Vercel configuration**

Create `vercel.json`:
```json
{
  "buildCommand": "bun run build",
  "devCommand": "bun run dev",
  "installCommand": "bun install",
  "framework": "nextjs",
  "regions": ["sfo1"]
}
```

Set environment variables in Vercel dashboard:
- `NEXT_PUBLIC_API_URL` → HF Spaces URL
- `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` → Google Maps API key
- `NEXT_PUBLIC_SUPABASE_URL` → Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` → Supabase anon key

### Backend Migration (Flask → FastAPI)

**1. Project structure**

```
backend/
├── app.py                    # FastAPI application
├── routers/
│   ├── business.py          # Business routes (was business/routes.py)
│   ├── review.py            # Review routes (was review/routes.py)
│   └── user.py              # User routes (was user/routes.py)
├── models/
│   ├── business.py          # Pydantic models
│   ├── review.py
│   └── user.py
├── ai/
│   ├── generate_vector.py   # ABSA logic (unchanged)
│   ├── fine_tuned_model/    # BERT model (committed via Git LFS)
│   ├── label_encoder.pkl
│   └── nltk_data/
├── database.py              # Database connection (async)
├── auth.py                  # JWT utilities
└── requirements.txt
```

**2. Core application setup**

`app.py`:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import business, review, user
import uvicorn

app = FastAPI(
    title="ClickBites API",
    description="ABSA Restaurant Recommendation System",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-app.vercel.app"],  # Update with actual Vercel URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(business.router, tags=["business"])
app.include_router(review.router, tags=["review"])
app.include_router(user.router, tags=["user"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model_loaded": True}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860)  # HF Spaces port
```

**3. Database connection (async)**

`database.py`:
```python
import asyncpg
from contextlib import asynccontextmanager
import os

DATABASE_URL = os.getenv("DATABASE_URL")

class Database:
    _pool = None
    
    @classmethod
    async def get_pool(cls):
        if cls._pool is None:
            cls._pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
        return cls._pool
    
    @classmethod
    async def close(cls):
        if cls._pool:
            await cls._pool.close()

@asynccontextmanager
async def get_db():
    """Dependency for database connection"""
    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        yield conn
```

**4. Pydantic models**

`models/business.py`:
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class BusinessBase(BaseModel):
    business_id: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    stars: Optional[float] = None
    categories: List[str] = []

class BusinessCreate(BusinessBase):
    aspect_scores: Optional[dict] = None

class BusinessResponse(BusinessBase):
    id: str
    review_count: int
    aspect_scores: dict
    photo_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
```

**5. Router example**

`routers/business.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from models.business import BusinessCreate, BusinessResponse
from database import get_db
from auth import get_current_user
import asyncpg

router = APIRouter(prefix="/api")

@router.post("/business", response_model=BusinessResponse)
async def register_business(
    business: BusinessCreate,
    business_pic: UploadFile = File(None),
    current_user: str = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """Register a new business"""
    try:
        # Upload photo to Supabase Storage if provided
        photo_url = None
        if business_pic:
            photo_url = await upload_photo(business_pic, business.business_id)
        
        # Insert into database
        result = await db.fetchrow("""
            INSERT INTO businesses (
                business_id, name, address, city, state, 
                postal_code, latitude, longitude, stars,
                categories, aspect_scores, photo_url
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING *
        """, business.business_id, business.name, ...)
        
        return BusinessResponse(**dict(result))
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=400, detail="Business already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/business/{business_id}", response_model=BusinessResponse)
async def get_business(
    business_id: str,
    db: asyncpg.Connection = Depends(get_db)
):
    """Get business by ID"""
    result = await db.fetchrow(
        "SELECT * FROM businesses WHERE business_id = $1",
        business_id
    )
    if not result:
        raise HTTPException(status_code=404, detail="Business not found")
    return BusinessResponse(**dict(result))
```

**6. Authentication**

`auth.py`:
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import os

JWT_SECRET = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Extract user_id from JWT token"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
```

**7. ABSA integration (minimal changes)**

The `ai/generate_vector.py` logic stays largely the same, but called from FastAPI routes:

```python
from ai.generate_vector import generate_aspect_vector

@router.post("/review")
async def create_review(
    review: ReviewCreate,
    current_user: str = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """Create a new review and generate ABSA vector"""
    # Generate aspect vector using BERT + VADER
    aspect_vector = generate_aspect_vector(review.text)
    
    # Insert review with vector
    result = await db.fetchrow("""
        INSERT INTO reviews (
            review_id, business_id, user_id, text, stars, aspect_vector
        )
        VALUES ($1, $2, $3, $4, $5, $6::vector)
        RETURNING *
    """, review.review_id, review.business_id, current_user, 
        review.text, review.stars, aspect_vector)
    
    # Update user preference vector (recalculate from all user reviews)
    await update_user_preference_vector(db, current_user)
    
    return ReviewResponse(**dict(result))
```

**8. Recommendation query with pgvector**

```python
@router.get("/recommendations/{user_id}")
async def get_recommendations(
    user_id: str,
    limit: int = 20,
    db: asyncpg.Connection = Depends(get_db)
):
    """Get personalized restaurant recommendations"""
    results = await db.fetch("""
        SELECT 
            b.business_id,
            b.name,
            b.address,
            b.city,
            b.stars,
            b.aspect_scores,
            b.photo_url,
            1 - (b.aspect_vector <=> u.preference_vector) AS similarity_score
        FROM businesses b
        CROSS JOIN users u
        WHERE u.user_id = $1
        ORDER BY b.aspect_vector <=> u.preference_vector
        LIMIT $2
    """, user_id, limit)
    
    return [dict(r) for r in results]
```

**9. Requirements file**

`requirements.txt`:
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
transformers==4.28.1
torch==2.0.1
vaderSentiment==3.3.2
spacy==3.5.3
psycopg2-binary==2.9.9
asyncpg==0.29.0
scikit-learn==1.0.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
supabase==2.3.0
Pillow==9.0.1
```

**10. Hugging Face Spaces configuration**

Create `.space` metadata file:
```yaml
title: ClickBites API
emoji: 🍔
colorFrom: orange
colorTo: red
sdk: docker
pinned: false
```

Create `Dockerfile`:
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Expose port (HF Spaces uses 7860)
EXPOSE 7860

# Run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
```

## Deployment Process

### Prerequisites

**What you need before starting:**

1. **Supabase account and project**
   - [ ] Sign up at https://supabase.com
   - [ ] Create new project (free tier)
   - [ ] Note: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `DATABASE_URL`

2. **Hugging Face account**
   - [ ] Sign up at https://huggingface.co
   - [ ] Get access token for Git LFS

3. **Vercel account**
   - [ ] Sign up at https://vercel.com
   - [ ] Connect GitHub account

4. **AI model files** (need to download)
   - [ ] `fine_tuned_model/` directory
   - [ ] `label_encoder.pkl` file
   - From: https://drive.google.com/drive/folders/1KruFCU66A7bPACEN3owDbu7JeC3wR6QY

5. **Google Maps API key**
   - [ ] Existing key or create new at console.cloud.google.com

6. **JWT secret**
   - [ ] Generate: `openssl rand -hex 32`

### Deployment Steps

#### Phase 1: Database Setup (Supabase)

**Estimated time: 30 minutes**

1. Create Supabase project:
   ```
   - Go to https://app.supabase.com
   - Click "New Project"
   - Name: "clickbites-prod"
   - Database password: (save this securely)
   - Region: Choose closest to your location
   - Wait for project creation (~2 minutes)
   ```

2. Enable pgvector extension:
   ```sql
   -- In Supabase SQL Editor
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. Create tables:
   ```sql
   -- Run the full schema from "Database (Supabase PostgreSQL)" section
   -- Copy all CREATE TABLE and CREATE INDEX statements
   ```

4. Create Supabase Storage bucket:
   ```
   - Go to Storage in Supabase dashboard
   - Click "New bucket"
   - Name: "business-photos"
   - Public bucket: Yes
   - Create bucket
   ```

5. Get connection details:
   ```
   - Go to Project Settings → Database
   - Copy Connection String (URI format)
   - Go to Project Settings → API
   - Copy URL and anon/public key
   ```

#### Phase 2: Data Migration

**Estimated time: 45 minutes**

1. Set up migration environment:
   ```bash
   cd backend
   python -m venv migration-env
   source migration-env/bin/activate  # On Windows: migration-env\Scripts\activate
   pip install asyncpg supabase-py python-dotenv
   ```

2. Create `.env` file:
   ```env
   DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_SERVICE_KEY=your_service_key_here
   ```

3. Run migration scripts (in order):
   ```bash
   # Export/transform data
   python scripts/transform_data.py
   
   # Upload photos to Supabase Storage
   python scripts/upload_photos.py
   
   # Import to PostgreSQL
   python scripts/import_postgresql.py
   ```

4. Validate migration:
   ```sql
   -- In Supabase SQL Editor
   SELECT 'businesses' as table_name, COUNT(*) FROM businesses
   UNION ALL
   SELECT 'reviews', COUNT(*) FROM reviews
   UNION ALL
   SELECT 'users', COUNT(*) FROM users;
   
   -- Check photo URLs
   SELECT COUNT(*) FROM businesses WHERE photo_url IS NOT NULL;
   ```

#### Phase 3: Backend Deployment (Hugging Face Spaces)

**Estimated time: 60 minutes**

1. Download AI model files:
   ```bash
   # Download from Google Drive link provided
   # Place in backend/ai/
   backend/ai/fine_tuned_model/  (entire directory)
   backend/ai/label_encoder.pkl
   ```

2. Create new HF Space:
   ```
   - Go to https://huggingface.co/spaces
   - Click "Create new Space"
   - Name: "clickbites-api"
   - SDK: Docker
   - Hardware: CPU basic (free)
   - Visibility: Public
   - Create Space
   ```

3. Initialize Git and push:
   ```bash
   cd backend
   git init
   git remote add space https://huggingface.co/spaces/YOUR_USERNAME/clickbites-api
   
   # Add all files
   git add .
   git commit -m "Initial commit: FastAPI backend with BERT model"
   
   # Push (Git LFS automatically handles large model files)
   git push space main
   ```

4. Set environment variables in HF Spaces:
   ```
   - Go to Space Settings → Variables and secrets
   - Add:
     DATABASE_URL = your_supabase_connection_string
     JWT_SECRET_KEY = your_generated_secret
     SUPABASE_URL = your_supabase_url
     SUPABASE_SERVICE_KEY = your_supabase_service_key
   ```

5. Wait for build and deployment:
   ```
   - HF Spaces will build Docker image (~5-10 minutes)
   - Once running, test API at: https://YOUR_USERNAME-clickbites-api.hf.space/docs
   - Verify health check: /health endpoint
   ```

#### Phase 4: Frontend Deployment (Vercel)

**Estimated time: 20 minutes**

1. Migrate to Bun locally:
   ```bash
   cd frontend
   rm package-lock.json yarn.lock
   bun install
   bun run build  # Test build works
   ```

2. Update configuration:
   ```bash
   # Rename next.config.js to next.config.ts
   # Copy content from "Frontend Changes" section
   ```

3. Create vercel.json:
   ```json
   {
     "buildCommand": "bun run build",
     "devCommand": "bun run dev",
     "installCommand": "bun install",
     "framework": "nextjs",
     "regions": ["sfo1"]
   }
   ```

4. Commit changes:
   ```bash
   git add .
   git commit -m "Migrate to Bun runtime and update config for production"
   git push origin main
   ```

5. Deploy to Vercel:
   ```
   - Go to https://vercel.com/new
   - Import GitHub repository
   - Root Directory: frontend/
   - Framework Preset: Next.js (auto-detected)
   - Override settings:
     - Build Command: bun run build
     - Install Command: bun install
   - Add environment variables:
     NEXT_PUBLIC_API_URL = https://YOUR_USERNAME-clickbites-api.hf.space
     NEXT_PUBLIC_GOOGLE_MAPS_API_KEY = your_google_maps_key
     NEXT_PUBLIC_SUPABASE_URL = your_supabase_url
     NEXT_PUBLIC_SUPABASE_ANON_KEY = your_supabase_anon_key
   - Click Deploy
   ```

6. Update CORS in backend:
   ```python
   # In backend/app.py, update allow_origins
   allow_origins=["https://your-app.vercel.app"]
   ```

7. Verify deployment:
   ```
   - Visit your Vercel URL
   - Test user login/signup
   - Test search functionality
   - Test viewing restaurant details
   - Submit a test review (ABSA processing)
   - Check recommendations
   ```

## Testing Strategy

### Unit Tests

**Backend tests** (`tests/test_api.py`):
```python
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_absa_vector_generation():
    from ai.generate_vector import generate_aspect_vector
    text = "The food was amazing but service was slow"
    vector = generate_aspect_vector(text)
    assert len(vector) == 5  # [food, service, price, ambience, misc]
    assert vector[0] > 0.5  # Food should be positive
    assert vector[1] < 0  # Service should be negative

def test_cosine_similarity():
    # Test pgvector similarity calculations
    pass
```

**Frontend tests** (`frontend/__tests__/`):
```typescript
// Component tests with React Testing Library
// API integration tests
// Image loading tests
```

### Integration Tests

**Critical user flows:**

1. **User registration and authentication:**
   - [ ] POST /api/user/register
   - [ ] POST /api/user/login
   - [ ] JWT token validation
   - [ ] Protected route access

2. **Review submission with ABSA:**
   - [ ] POST /api/review with text
   - [ ] BERT model processes text
   - [ ] Aspect vector generated correctly
   - [ ] Vector stored in database
   - [ ] User preference vector updated

3. **Restaurant recommendations:**
   - [ ] GET /api/recommendations/:user_id
   - [ ] Cosine similarity calculated in SQL
   - [ ] Results ranked correctly
   - [ ] Photo URLs accessible

4. **Business registration:**
   - [ ] POST /api/business with photo
   - [ ] Photo uploaded to Supabase Storage
   - [ ] Public URL stored in database
   - [ ] Business searchable

### End-to-End Tests

**Full user journey:**
```
1. User visits homepage
2. User signs up (new account)
3. User logs in
4. User searches for restaurants
5. User views restaurant details (photo loads from Supabase)
6. User submits review (ABSA processing triggered)
7. User views updated recommendations (based on new preference vector)
8. User logs out
```

### Performance Tests

**Benchmarks:**
- [ ] ABSA processing time: < 5 seconds per review
- [ ] Recommendation query: < 1 second
- [ ] Database queries: < 500ms
- [ ] Photo loading: < 2 seconds
- [ ] Initial page load: < 3 seconds

### Pre-Deployment Checklist

- [ ] All environment variables set correctly
- [ ] Database migrations completed successfully
- [ ] Photos accessible from Supabase Storage
- [ ] BERT model loads on HF Spaces startup
- [ ] API health check returns 200
- [ ] Frontend can reach backend API
- [ ] CORS configured correctly
- [ ] JWT authentication works
- [ ] Test user can submit review
- [ ] Test user gets recommendations

## Error Handling & Monitoring

### Backend Error Handling

**Global exception handler:**
```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error",
            "detail": str(exc) if app.debug else "An error occurred"
        }
    )

@app.exception_handler(asyncpg.PostgresError)
async def database_exception_handler(request: Request, exc: asyncpg.PostgresError):
    return JSONResponse(
        status_code=503,
        content={"message": "Database temporarily unavailable"}
    )
```

**Model loading error handling:**
```python
try:
    from ai.generate_vector import generate_aspect_vector
    MODEL_LOADED = True
except Exception as e:
    MODEL_LOADED = False
    print(f"Error loading ABSA model: {e}")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy" if MODEL_LOADED else "degraded",
        "model_loaded": MODEL_LOADED
    }
```

### Frontend Error Handling

**API error handling:**
```typescript
async function submitReview(reviewData: ReviewCreate) {
  try {
    setLoading(true);
    const response = await fetch(`${API_URL}/api/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(reviewData),
    });
    
    if (!response.ok) {
      throw new Error('Failed to submit review');
    }
    
    const data = await response.json();
    toast.success('Review submitted successfully!');
    return data;
  } catch (error) {
    toast.error('Failed to submit review. Please try again.');
    console.error(error);
  } finally {
    setLoading(false);
  }
}
```

**Image loading fallback:**
```typescript
<img 
  src={business.photo_url} 
  alt={business.name}
  onError={(e) => {
    e.currentTarget.src = '/placeholder-restaurant.jpg';
  }}
/>
```

### Rate Limiting

**Backend rate limiting:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/review")
@limiter.limit("5/hour")  # Max 5 reviews per hour per IP
async def create_review(...):
    pass
```

### Monitoring

**Free tier monitoring tools:**

1. **Hugging Face Spaces:**
   - Built-in logs viewer
   - Container metrics (CPU, memory)
   - Request logs

2. **Vercel:**
   - Real-time function logs
   - Deployment analytics
   - Web vitals monitoring

3. **Supabase:**
   - Database activity monitor
   - Table size and growth
   - Query performance stats
   - Storage usage

**Health check endpoints:**
```python
@app.get("/health")
async def health_check():
    return {"status": "healthy", "model_loaded": MODEL_LOADED}

@app.get("/health/db")
async def database_health(db: asyncpg.Connection = Depends(get_db)):
    try:
        await db.fetchval("SELECT 1")
        return {"status": "healthy"}
    except:
        return {"status": "unhealthy"}
```

### Logging

**Structured logging:**
```python
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@app.post("/api/review")
async def create_review(review: ReviewCreate, ...):
    logger.info(f"Processing review submission: user={current_user}, business={review.business_id}")
    
    try:
        aspect_vector = generate_aspect_vector(review.text)
        logger.info(f"ABSA vector generated: {aspect_vector}")
        # ...
    except Exception as e:
        logger.error(f"Error processing review: {e}", exc_info=True)
        raise
```

## Security Considerations

### Authentication & Authorization

**JWT token security:**
- Use strong secret key (32+ random bytes)
- Set reasonable expiration (24 hours)
- Include user_id in payload
- Validate on every protected route

**Password hashing:**
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

### Database Security

**SQL injection prevention:**
- Use parameterized queries (asyncpg prevents SQL injection)
- Never concatenate user input into SQL strings

**Connection security:**
- Use SSL/TLS for database connections (Supabase enforces this)
- Store connection strings in environment variables
- Use read-only credentials where possible

### API Security

**CORS configuration:**
```python
# Only allow specific frontend domain
allow_origins=["https://clickbites.vercel.app"]  # Update with actual domain
allow_credentials=True
```

**Input validation:**
```python
from pydantic import BaseModel, validator, Field

class ReviewCreate(BaseModel):
    text: str = Field(..., min_length=10, max_length=5000)
    stars: float = Field(..., ge=1, le=5)
    
    @validator('text')
    def sanitize_text(cls, v):
        # Remove any potentially harmful characters
        return v.strip()
```

**File upload security:**
```python
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

async def upload_photo(file: UploadFile, business_id: str):
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Invalid file type")
    
    # Validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large")
    
    # Upload to Supabase Storage
    # ...
```

### Environment Variables

**Never commit secrets:**
```gitignore
# .gitignore
.env
.env.local
config.py
next.config.js
```

**Use environment variables for:**
- Database connection strings
- JWT secret keys
- API keys (Google Maps, Supabase)
- Service keys

## Cost Breakdown

### Free Tier Limits

**Vercel (Frontend):**
- ✅ 100GB bandwidth per month
- ✅ Unlimited sites and deployments
- ✅ Automatic HTTPS
- ✅ Edge network (CDN)
- ⚠️ Exceeding 100GB: $40/100GB

**Hugging Face Spaces (Backend):**
- ✅ CPU Basic hardware (2 vCPU, 16GB RAM)
- ✅ 2GB persistent storage
- ✅ Always-on (no cold starts)
- ✅ Git LFS for large files
- ⚠️ Upgraded hardware: $0.03/hour (~$22/month)

**Supabase (Database + Storage):**
- ✅ 500MB database
- ✅ 1GB file storage
- ✅ 2GB bandwidth
- ✅ 7-day database backups
- ⚠️ Exceeding limits: $25/month pro plan

**Google Maps API:**
- ✅ $200 free credit per month
- ✅ ~28,000 map loads per month
- ⚠️ Exceeding credit: pay-as-you-go

### Projected Usage (Portfolio/Demo)

**Assuming:**
- 100 unique visitors per month
- 10 reviews submitted per month
- 500 API requests per day

**Estimated usage:**
- Vercel bandwidth: ~5GB/month (well under 100GB)
- Supabase database: ~50MB (well under 500MB)
- Supabase storage: 94MB photos (well under 1GB)
- Google Maps loads: ~500/month (well under 28,000)
- HF Spaces: Always free on CPU Basic

**Total cost: $0/month** ✅

### Upgrade Path (If Needed)

**If traffic grows:**

1. **First bottleneck: Vercel bandwidth (100GB)**
   - Upgrade to Pro: $20/month (1TB bandwidth)

2. **Second bottleneck: Supabase storage/database**
   - Upgrade to Pro: $25/month (8GB database, 100GB storage)

3. **Performance optimization: HF Spaces**
   - Upgrade to CPU Upgrade: ~$22/month (4 vCPU, faster inference)
   - Or migrate to dedicated VPS/cloud provider

**Estimated cost at scale:**
- 1,000 visitors/month: Still $0
- 10,000 visitors/month: ~$45/month
- 100,000 visitors/month: ~$100-200/month

## Rollback Plan

### If deployment fails:

**Database rollback:**
- Keep MongoDB backup/JSON files until migration validated
- Supabase has automatic backups (can restore to point in time)

**Backend rollback:**
- Keep Flask version in separate git branch
- Can redeploy Flask to Render if FastAPI issues

**Frontend rollback:**
- Vercel keeps deployment history (instant rollback)
- Can revert git commits and redeploy

**Photo storage rollback:**
- Keep local photos until Supabase validated
- Can re-upload if needed

### Validation checklist before going live:

- [ ] All API endpoints tested and working
- [ ] Sample review submission successful (ABSA working)
- [ ] Recommendations generated correctly
- [ ] All photos accessible
- [ ] User auth flow complete
- [ ] No console errors in browser
- [ ] Mobile responsive
- [ ] Performance acceptable (< 3s load time)

## Success Criteria

**Deployment is successful when:**

1. ✅ Frontend accessible at Vercel URL
2. ✅ Backend API responding at HF Spaces URL
3. ✅ Database queries working (PostgreSQL)
4. ✅ Photos loading from Supabase Storage
5. ✅ User can sign up and log in
6. ✅ User can submit review
7. ✅ ABSA processing generates 5D vector
8. ✅ Recommendations returned based on cosine similarity
9. ✅ All on free tier ($0/month)
10. ✅ No critical errors in logs

**Performance benchmarks:**

- Initial page load: < 3 seconds
- Review submission: < 5 seconds (ABSA processing)
- Recommendation query: < 1 second
- Photo loading: < 2 seconds

## Future Enhancements

**Post-deployment improvements** (not in scope for initial deployment):

1. **Replace JWT with Supabase Auth**
   - Built-in auth, email verification, social logins
   - Reduces custom code

2. **Add caching layer**
   - Redis for popular recommendations
   - Reduce database load

3. **Optimize BERT model**
   - Model quantization for faster inference
   - Or use smaller model (DistilBERT)

4. **Real-time features**
   - Supabase Realtime for live review updates
   - WebSocket support

5. **Analytics**
   - Track popular restaurants
   - User engagement metrics
   - A/B testing

6. **SEO optimization**
   - Server-side rendering for restaurant pages
   - Sitemap generation
   - Meta tags optimization

## Conclusion

This deployment plan migrates ClickBites from a local development environment to a production-ready system on 100% free tier infrastructure. The key migrations are:

- **MongoDB → PostgreSQL + pgvector** (better vector similarity, more robust)
- **Flask → FastAPI** (modern, async, auto-docs)
- **npm/yarn → Bun** (faster, modern tooling)
- **Local photos → Supabase Storage** (CDN-backed, scalable)
- **Local ML → Hugging Face Spaces** (always-on, designed for models)

All services are on generous free tiers, making this a zero-cost production deployment suitable for a portfolio/demo project with room to scale if needed.
