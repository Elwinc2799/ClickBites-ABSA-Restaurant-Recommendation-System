# ClickBites Production Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy ClickBites ABSA Restaurant Recommendation System to production on 100% free tier infrastructure

**Architecture:** Three-tier architecture with Vercel (Next.js + Bun), Hugging Face Spaces (FastAPI + BERT), and Supabase (PostgreSQL + pgvector + Storage)

**Tech Stack:** FastAPI, asyncpg, PostgreSQL/pgvector, Supabase, Bun, Next.js 15, Docker, Hugging Face Spaces

---

## File Structure Overview

### New Files to Create

**Migration Scripts:**
- `scripts/transform_data.py` - Transform MongoDB JSON → PostgreSQL format
- `scripts/upload_photos.py` - Upload photos to Supabase Storage
- `scripts/import_postgresql.py` - Import data into PostgreSQL
- `scripts/.env.example` - Example environment variables

**Backend (FastAPI):**
- `backend_fastapi/app.py` - Main FastAPI application
- `backend_fastapi/database.py` - Async database connection pool
- `backend_fastapi/auth.py` - JWT authentication utilities
- `backend_fastapi/routers/business.py` - Business endpoints
- `backend_fastapi/routers/review.py` - Review endpoints
- `backend_fastapi/routers/user.py` - User endpoints
- `backend_fastapi/models/business.py` - Pydantic models for business
- `backend_fastapi/models/review.py` - Pydantic models for review
- `backend_fastapi/models/user.py` - Pydantic models for user
- `backend_fastapi/requirements.txt` - Python dependencies
- `backend_fastapi/Dockerfile` - Docker configuration for HF Spaces
- `backend_fastapi/.space` - HF Spaces metadata
- `backend_fastapi/.gitignore` - Git ignore file

**Frontend Updates:**
- Modify: `frontend/next.config.js` → `frontend/next.config.ts`
- Create: `frontend/vercel.json` - Vercel configuration
- Modify: `frontend/.gitignore` - Add business_photo directory
- Create: `frontend/public/placeholder-restaurant.jpg` - Fallback image

### Files to Modify

**Frontend:**
- `frontend/package.json` - Already compatible with Bun
- All component files using photo URLs (grep for `/business_photo/`)

**Backend:**
- Copy `backend/ai/` directory to `backend_fastapi/ai/` (AI logic reused)

---

## Phase 1: Prerequisites & Account Setup

### Task 1: Create Supabase Project

**Goal:** Set up Supabase project and get credentials

- [ ] **Step 1: Sign up for Supabase**

Visit: https://supabase.com
Click "Start your project"
Create account (GitHub OAuth recommended)

- [ ] **Step 2: Create new project**

Project name: `clickbites-prod`
Database password: Generate strong password, save securely
Region: Choose closest to your location (e.g., US West)
Wait for project creation (~2 minutes)

- [ ] **Step 3: Collect credentials**

Go to Project Settings → API
Copy and save:
- Project URL: `https://xxx.supabase.co`
- Project API keys → anon/public key
- Project API keys → service_role key (keep secret)

Go to Project Settings → Database
Copy Connection string (URI mode):
`postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres`

- [ ] **Step 4: Create credentials file**

Create a file outside the repo to store credentials:
```bash
# ~/clickbites-credentials.txt
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJxxx...
SUPABASE_SERVICE_KEY=eyJxxx...
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
```

- [ ] **Step 5: Verify credentials work**

Test connection:
```bash
psql "postgresql://postgres:password@db.xxx.supabase.co:5432/postgres"
```

Expected: Connected to PostgreSQL prompt

---

### Task 2: Set Up Other Accounts

**Goal:** Create accounts for Vercel, Hugging Face, generate JWT secret

- [ ] **Step 1: Create Vercel account**

Visit: https://vercel.com
Sign up with GitHub
Connect your GitHub account to Vercel

- [ ] **Step 2: Create Hugging Face account**

Visit: https://huggingface.co
Sign up
Go to Settings → Access Tokens
Create new token: "clickbites-deployment" (Write access)
Save token securely

- [ ] **Step 3: Generate JWT secret**

```bash
openssl rand -hex 32
```

Save output to credentials file:
```bash
# Add to ~/clickbites-credentials.txt
JWT_SECRET_KEY=<generated-32-byte-hex-string>
```

- [ ] **Step 4: Download AI model files**

Visit: https://drive.google.com/drive/folders/1KruFCU66A7bPACEN3owDbu7JeC3wR6QY
Download:
- `fine_tuned_model/` (entire directory)
- `label_encoder.pkl` file

Save to a temporary location (will be copied later)

- [ ] **Step 5: Verify Google Maps API key**

Check existing key or create new one at: https://console.cloud.google.com
Ensure Maps JavaScript API is enabled
Save key to credentials file:
```bash
# Add to ~/clickbites-credentials.txt
GOOGLE_MAPS_API_KEY=<your-api-key>
```

---

## Phase 2: Database Setup

### Task 3: Create PostgreSQL Schema

**Goal:** Set up database tables with pgvector extension

**Files:**
- Create: `scripts/schema.sql`

- [ ] **Step 1: Create schema SQL file**

```sql
-- scripts/schema.sql
-- Enable pgvector extension for vector similarity
CREATE EXTENSION IF NOT EXISTS vector;

-- Businesses table
CREATE TABLE businesses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  business_id VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(500) NOT NULL,
  address TEXT,
  city VARCHAR(255),
  state VARCHAR(50),
  postal_code VARCHAR(20),
  latitude DECIMAL(10, 8),
  longitude DECIMAL(11, 8),
  stars DECIMAL(2, 1),
  review_count INTEGER DEFAULT 0,
  categories TEXT[],
  aspect_scores JSONB,
  photo_url TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_business_id ON businesses(business_id);
CREATE INDEX idx_city ON businesses(city);
CREATE INDEX idx_categories ON businesses USING GIN(categories);

-- Users table (must be before reviews due to foreign key)
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  preference_vector VECTOR(5),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_id ON users(user_id);
CREATE INDEX idx_email ON users(email);
CREATE INDEX idx_preference_vector ON users USING ivfflat (preference_vector vector_cosine_ops);

-- Reviews table
CREATE TABLE reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  review_id VARCHAR(255) UNIQUE NOT NULL,
  business_id VARCHAR(255) REFERENCES businesses(business_id) ON DELETE CASCADE,
  user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  stars DECIMAL(2, 1),
  aspect_vector VECTOR(5),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_review_business ON reviews(business_id);
CREATE INDEX idx_review_user ON reviews(user_id);
CREATE INDEX idx_aspect_vector ON reviews USING ivfflat (aspect_vector vector_cosine_ops);
```

- [ ] **Step 2: Execute schema in Supabase**

Go to Supabase Dashboard → SQL Editor
Copy entire content of `scripts/schema.sql`
Paste and click "Run"

Expected: "Success. No rows returned"

- [ ] **Step 3: Verify tables created**

Run in SQL Editor:
```sql
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;
```

Expected output:
```
businesses
reviews
users
```

- [ ] **Step 4: Verify pgvector extension**

Run in SQL Editor:
```sql
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

Expected: `vector | 0.6.0` (or similar version)

- [ ] **Step 5: Commit schema file**

```bash
git add scripts/schema.sql
git commit -m "feat: add PostgreSQL schema with pgvector"
```

---

### Task 4: Create Supabase Storage Bucket

**Goal:** Set up public storage bucket for business photos

- [ ] **Step 1: Navigate to Storage**

In Supabase Dashboard → Storage

- [ ] **Step 2: Create new bucket**

Click "New bucket"
Name: `business-photos`
Public bucket: ✅ Yes (check the box)
File size limit: 5 MB
Allowed MIME types: image/jpeg, image/jpg, image/png
Click "Create bucket"

- [ ] **Step 3: Verify bucket created**

Should see "business-photos" in bucket list
Click on it - should be empty

- [ ] **Step 4: Test bucket with sample upload**

Click "Upload file"
Upload any JPG image as test
Get URL and verify it's publicly accessible in browser

- [ ] **Step 5: Document bucket configuration**

Create: `scripts/supabase-setup.md`

```markdown
# Supabase Setup Notes

## Storage Bucket
- Name: `business-photos`
- Public: Yes
- URL pattern: `https://xxx.supabase.co/storage/v1/object/public/business-photos/{filename}`

## Database
- Tables: businesses, users, reviews
- Extensions: pgvector
```

Commit:
```bash
git add scripts/supabase-setup.md
git commit -m "docs: add Supabase setup documentation"
```

---

## Phase 3: Data Migration Scripts

### Task 5: Create Data Transformation Script

**Goal:** Transform MongoDB JSON data to PostgreSQL format

**Files:**
- Create: `scripts/transform_data.py`

- [ ] **Step 1: Create transform_data.py skeleton**

```python
# scripts/transform_data.py
"""
Transform MongoDB JSON data to PostgreSQL-compatible format.
Reads data/business.json, data/review.json, data/user.json
Outputs transformed data ready for PostgreSQL import.
"""
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any

def load_json_data() -> tuple:
    """Load JSON data files"""
    business_path = Path('data/business.json')
    review_path = Path('data/review.json')
    user_path = Path('data/user.json')
    
    with open(business_path) as f:
        businesses = json.load(f)
    
    with open(review_path) as f:
        reviews = json.load(f)
    
    with open(user_path) as f:
        users = json.load(f)
    
    return businesses, reviews, users

def transform_business(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Transform business document from MongoDB to PostgreSQL format"""
    return {
        'business_id': doc.get('business_id'),
        'name': doc.get('name'),
        'address': doc.get('address'),
        'city': doc.get('city'),
        'state': doc.get('state'),
        'postal_code': doc.get('postal_code'),
        'latitude': doc.get('latitude'),
        'longitude': doc.get('longitude'),
        'stars': doc.get('stars'),
        'review_count': doc.get('review_count', 0),
        'categories': doc.get('categories', []),
        'aspect_scores': doc.get('aspect_scores', {}),
        'photo_url': None  # Will be set after photo upload
    }

def transform_user(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Transform user document from MongoDB to PostgreSQL format"""
    return {
        'user_id': doc.get('user_id'),
        'name': doc.get('name'),
        'email': doc.get('email'),
        'password_hash': doc.get('password'),  # Already hashed
        'preference_vector': doc.get('preference_vector')  # May be None
    }

def transform_review(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Transform review document from MongoDB to PostgreSQL format"""
    aspect_vector = doc.get('aspect_vector', [0, 0, 0, 0, 0])
    
    # Ensure aspect_vector is list of 5 floats
    if not isinstance(aspect_vector, list) or len(aspect_vector) != 5:
        aspect_vector = [0.0, 0.0, 0.0, 0.0, 0.0]
    
    return {
        'review_id': doc.get('review_id'),
        'business_id': doc.get('business_id'),
        'user_id': doc.get('user_id'),
        'text': doc.get('text'),
        'stars': doc.get('stars'),
        'aspect_vector': aspect_vector
    }

def main():
    """Main transformation function"""
    print("Loading JSON data...")
    businesses, reviews, users = load_json_data()
    
    print(f"Loaded {len(businesses)} businesses")
    print(f"Loaded {len(reviews)} reviews")
    print(f"Loaded {len(users)} users")
    
    # Transform data
    print("\nTransforming data...")
    transformed_businesses = [transform_business(b) for b in businesses]
    transformed_users = [transform_user(u) for u in users]
    transformed_reviews = [transform_review(r) for r in reviews]
    
    # Save transformed data
    output_dir = Path('scripts/transformed_data')
    output_dir.mkdir(exist_ok=True)
    
    with open(output_dir / 'businesses.json', 'w') as f:
        json.dump(transformed_businesses, f, indent=2)
    
    with open(output_dir / 'users.json', 'w') as f:
        json.dump(transformed_users, f, indent=2)
    
    with open(output_dir / 'reviews.json', 'w') as f:
        json.dump(transformed_reviews, f, indent=2)
    
    print(f"\nTransformation complete!")
    print(f"Output saved to {output_dir}")
    print(f"- businesses.json: {len(transformed_businesses)} records")
    print(f"- users.json: {len(transformed_users)} records")
    print(f"- reviews.json: {len(transformed_reviews)} records")

if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Test transform script**

```bash
cd /Users/elwin/Developer/ClickBites-ABSA-Restaurant-Recommendation-System
python scripts/transform_data.py
```

Expected output:
```
Loading JSON data...
Loaded X businesses
Loaded Y reviews
Loaded Z users

Transforming data...
Transformation complete!
Output saved to scripts/transformed_data
```

- [ ] **Step 3: Verify transformed data**

```bash
ls scripts/transformed_data/
cat scripts/transformed_data/businesses.json | head -20
```

Expected: JSON files with transformed data

- [ ] **Step 4: Add to gitignore**

Add to `scripts/.gitignore`:
```
transformed_data/
.env
__pycache__/
```

- [ ] **Step 5: Commit script**

```bash
git add scripts/transform_data.py scripts/.gitignore
git commit -m "feat: add data transformation script for PostgreSQL migration"
```

---

### Task 6: Create Photo Upload Script

**Goal:** Upload business photos to Supabase Storage

**Files:**
- Create: `scripts/upload_photos.py`
- Create: `scripts/.env.example`

- [ ] **Step 1: Create .env.example**

```bash
# scripts/.env.example
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=your_service_key_here
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
```

- [ ] **Step 2: Create upload_photos.py**

```python
# scripts/upload_photos.py
"""
Upload business photos from frontend/public/business_photo/ to Supabase Storage.
Returns mapping of business_id → photo URL.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import json

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

def upload_photos() -> dict:
    """Upload all business photos to Supabase Storage"""
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    photo_dir = Path('frontend/public/business_photo')
    if not photo_dir.exists():
        print(f"Photo directory not found: {photo_dir}")
        return {}
    
    photo_urls = {}
    successful = 0
    failed = 0
    
    print(f"Uploading photos from {photo_dir}...")
    
    for photo_path in sorted(photo_dir.glob('*.jpg')):
        business_id = photo_path.stem
        
        try:
            with open(photo_path, 'rb') as f:
                file_data = f.read()
            
            # Upload to Supabase Storage
            result = supabase.storage.from_('business-photos').upload(
                f'{business_id}.jpg',
                file_data,
                {'content-type': 'image/jpeg'}
            )
            
            # Get public URL
            public_url = supabase.storage.from_('business-photos').get_public_url(f'{business_id}.jpg')
            photo_urls[business_id] = public_url
            successful += 1
            
            if successful % 10 == 0:
                print(f"  Uploaded {successful} photos...")
                
        except Exception as e:
            print(f"  Failed to upload {business_id}.jpg: {e}")
            failed += 1
    
    print(f"\nUpload complete!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    
    # Save mapping to file
    output_path = Path('scripts/transformed_data/photo_urls.json')
    with open(output_path, 'w') as f:
        json.dump(photo_urls, f, indent=2)
    
    print(f"  Photo URL mapping saved to {output_path}")
    
    return photo_urls

if __name__ == '__main__':
    upload_photos()
```

- [ ] **Step 3: Create scripts/.env file**

```bash
cd scripts
cp .env.example .env
# Edit .env with actual credentials from ~/clickbites-credentials.txt
```

- [ ] **Step 4: Install dependencies**

```bash
cd scripts
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install supabase python-dotenv asyncpg
```

- [ ] **Step 5: Test photo upload**

```bash
python upload_photos.py
```

Expected output:
```
Uploading photos from frontend/public/business_photo...
  Uploaded 10 photos...
  Uploaded 20 photos...
...
Upload complete!
  Successful: X
  Failed: 0
  Photo URL mapping saved to scripts/transformed_data/photo_urls.json
```

- [ ] **Step 6: Verify photos accessible**

Open a photo URL from `photo_urls.json` in browser
Should display the photo

- [ ] **Step 7: Commit script**

```bash
git add scripts/upload_photos.py scripts/.env.example
git commit -m "feat: add photo upload script for Supabase Storage"
```

---

### Task 7: Create PostgreSQL Import Script

**Goal:** Import transformed data into PostgreSQL

**Files:**
- Create: `scripts/import_postgresql.py`

- [ ] **Step 1: Create import_postgresql.py**

```python
# scripts/import_postgresql.py
"""
Import transformed data into PostgreSQL (Supabase).
Imports businesses, users, and reviews in correct order.
"""
import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import asyncpg

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

async def import_businesses(conn, businesses: list, photo_urls: dict):
    """Import businesses with photo URLs"""
    print(f"Importing {len(businesses)} businesses...")
    
    inserted = 0
    for business in businesses:
        business_id = business['business_id']
        photo_url = photo_urls.get(business_id)
        
        try:
            await conn.execute("""
                INSERT INTO businesses (
                    business_id, name, address, city, state, postal_code,
                    latitude, longitude, stars, review_count, categories,
                    aspect_scores, photo_url
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                ON CONFLICT (business_id) DO NOTHING
            """,
                business['business_id'],
                business['name'],
                business['address'],
                business['city'],
                business['state'],
                business['postal_code'],
                business['latitude'],
                business['longitude'],
                business['stars'],
                business['review_count'],
                business['categories'],
                json.dumps(business['aspect_scores']),
                photo_url
            )
            inserted += 1
            
            if inserted % 100 == 0:
                print(f"  Inserted {inserted} businesses...")
                
        except Exception as e:
            print(f"  Error inserting business {business_id}: {e}")
    
    print(f"  Businesses imported: {inserted}")

async def import_users(conn, users: list):
    """Import users"""
    print(f"Importing {len(users)} users...")
    
    inserted = 0
    for user in users:
        try:
            # Convert preference_vector to proper format
            pref_vector = user.get('preference_vector')
            if pref_vector and isinstance(pref_vector, list):
                pref_vector_str = f"[{','.join(str(v) for v in pref_vector)}]"
            else:
                pref_vector_str = None
            
            await conn.execute("""
                INSERT INTO users (
                    user_id, name, email, password_hash, preference_vector
                )
                VALUES ($1, $2, $3, $4, $5::vector)
                ON CONFLICT (user_id) DO NOTHING
            """,
                user['user_id'],
                user['name'],
                user['email'],
                user['password_hash'],
                pref_vector_str
            )
            inserted += 1
            
            if inserted % 100 == 0:
                print(f"  Inserted {inserted} users...")
                
        except Exception as e:
            print(f"  Error inserting user {user.get('user_id')}: {e}")
    
    print(f"  Users imported: {inserted}")

async def import_reviews(conn, reviews: list):
    """Import reviews"""
    print(f"Importing {len(reviews)} reviews...")
    
    inserted = 0
    for review in reviews:
        try:
            # Convert aspect_vector to proper format
            aspect_vector = review['aspect_vector']
            vector_str = f"[{','.join(str(v) for v in aspect_vector)}]"
            
            await conn.execute("""
                INSERT INTO reviews (
                    review_id, business_id, user_id, text, stars, aspect_vector
                )
                VALUES ($1, $2, $3, $4, $5, $6::vector)
                ON CONFLICT (review_id) DO NOTHING
            """,
                review['review_id'],
                review['business_id'],
                review['user_id'],
                review['text'],
                review['stars'],
                vector_str
            )
            inserted += 1
            
            if inserted % 100 == 0:
                print(f"  Inserted {inserted} reviews...")
                
        except Exception as e:
            print(f"  Error inserting review {review.get('review_id')}: {e}")
    
    print(f"  Reviews imported: {inserted}")

async def verify_import(conn):
    """Verify data was imported correctly"""
    print("\nVerifying import...")
    
    # Count records
    business_count = await conn.fetchval("SELECT COUNT(*) FROM businesses")
    user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
    review_count = await conn.fetchval("SELECT COUNT(*) FROM reviews")
    
    print(f"  Businesses: {business_count}")
    print(f"  Users: {user_count}")
    print(f"  Reviews: {review_count}")
    
    # Check for orphaned reviews
    orphaned = await conn.fetchval("""
        SELECT COUNT(*) FROM reviews r
        LEFT JOIN businesses b ON r.business_id = b.business_id
        WHERE b.business_id IS NULL
    """)
    
    if orphaned > 0:
        print(f"  WARNING: {orphaned} orphaned reviews (business not found)")
    else:
        print(f"  ✓ All reviews have valid business references")
    
    # Check for null vectors
    null_vectors = await conn.fetchval("""
        SELECT COUNT(*) FROM reviews WHERE aspect_vector IS NULL
    """)
    
    if null_vectors > 0:
        print(f"  WARNING: {null_vectors} reviews with NULL aspect_vector")
    else:
        print(f"  ✓ All reviews have aspect vectors")

async def main():
    """Main import function"""
    # Load transformed data
    data_dir = Path('scripts/transformed_data')
    
    with open(data_dir / 'businesses.json') as f:
        businesses = json.load(f)
    
    with open(data_dir / 'users.json') as f:
        users = json.load(f)
    
    with open(data_dir / 'reviews.json') as f:
        reviews = json.load(f)
    
    with open(data_dir / 'photo_urls.json') as f:
        photo_urls = json.load(f)
    
    print("Connecting to PostgreSQL...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Import in correct order (users and businesses before reviews)
        await import_businesses(conn, businesses, photo_urls)
        await import_users(conn, users)
        await import_reviews(conn, reviews)
        
        # Verify
        await verify_import(conn)
        
        print("\n✓ Import complete!")
        
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
```

- [ ] **Step 2: Test import script**

```bash
cd scripts
source venv/bin/activate
python import_postgresql.py
```

Expected output:
```
Connecting to PostgreSQL...
Importing X businesses...
  Inserted 100 businesses...
  ...
  Businesses imported: X
Importing Y users...
  Users imported: Y
Importing Z reviews...
  Reviews imported: Z

Verifying import...
  Businesses: X
  Users: Y
  Reviews: Z
  ✓ All reviews have valid business references
  ✓ All reviews have aspect vectors

✓ Import complete!
```

- [ ] **Step 3: Verify in Supabase dashboard**

Go to Supabase Dashboard → Table Editor
Check businesses, users, reviews tables
Should see data populated

- [ ] **Step 4: Test vector similarity query**

In Supabase SQL Editor:
```sql
SELECT business_id, name, aspect_scores
FROM businesses
LIMIT 5;
```

Expected: Returns business data with aspect_scores

- [ ] **Step 5: Commit script**

```bash
git add scripts/import_postgresql.py
git commit -m "feat: add PostgreSQL import script for data migration"
```

---

## Phase 4: Backend Migration (Flask → FastAPI)

### Task 8: Set Up FastAPI Project Structure

**Goal:** Create new FastAPI project structure

- [ ] **Step 1: Create backend_fastapi directory**

```bash
mkdir backend_fastapi
cd backend_fastapi
mkdir -p routers models ai
touch __init__.py routers/__init__.py models/__init__.py
```

- [ ] **Step 2: Copy AI logic from old backend**

```bash
cp -r ../backend/ai/* ai/
# Note: Model files (fine_tuned_model/, label_encoder.pkl) will be added later
```

- [ ] **Step 3: Create requirements.txt**

```txt
# backend_fastapi/requirements.txt
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
python-dotenv==1.0.0
```

- [ ] **Step 4: Create .gitignore**

```
# backend_fastapi/.gitignore
__pycache__/
*.pyc
.env
.venv
venv/
ai/fine_tuned_model/
ai/label_encoder.pkl
.DS_Store
```

- [ ] **Step 5: Create .env.example**

```bash
# backend_fastapi/.env.example
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
JWT_SECRET_KEY=your_generated_jwt_secret_here
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=your_service_key_here
```

- [ ] **Step 6: Commit project structure**

```bash
git add backend_fastapi/
git commit -m "feat: initialize FastAPI project structure"
```

---

### Task 9: Implement Database Connection

**Goal:** Create async database connection pool

**Files:**
- Create: `backend_fastapi/database.py`

- [ ] **Step 1: Write database.py**

```python
# backend_fastapi/database.py
"""
Async PostgreSQL connection pool using asyncpg.
Provides dependency injection for FastAPI routes.
"""
import os
import asyncpg
from contextlib import asynccontextmanager
from typing import AsyncGenerator

DATABASE_URL = os.getenv("DATABASE_URL")

class Database:
    """Singleton database connection pool"""
    _pool: asyncpg.Pool = None
    
    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        """Get or create connection pool"""
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
        """Close connection pool"""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None

@asynccontextmanager
async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    Dependency for database connection.
    Usage in FastAPI routes: db: asyncpg.Connection = Depends(get_db)
    """
    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        yield conn
```

- [ ] **Step 2: Create test file**

```python
# backend_fastapi/test_database.py
"""Test database connection"""
import asyncio
import os
from dotenv import load_dotenv
from database import Database

load_dotenv()

async def test_connection():
    """Test database connection"""
    print("Testing database connection...")
    
    pool = await Database.get_pool()
    async with pool.acquire() as conn:
        # Test query
        result = await conn.fetchval("SELECT 1")
        print(f"Connection successful! Test query result: {result}")
        
        # Check tables
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        print(f"\nTables found: {len(tables)}")
        for table in tables:
            print(f"  - {table['table_name']}")
    
    await Database.close()
    print("\n✓ Database test complete!")

if __name__ == '__main__':
    asyncio.run(test_connection())
```

- [ ] **Step 3: Create .env file**

```bash
cd backend_fastapi
cp .env.example .env
# Edit .env with actual credentials from ~/clickbites-credentials.txt
```

- [ ] **Step 4: Test database connection**

```bash
cd backend_fastapi
python test_database.py
```

Expected output:
```
Testing database connection...
Connection successful! Test query result: 1

Tables found: 3
  - businesses
  - reviews
  - users

✓ Database test complete!
```

- [ ] **Step 5: Commit database module**

```bash
git add backend_fastapi/database.py backend_fastapi/.env.example
git commit -m "feat: add async database connection pool"
```

---

### Task 10: Implement Authentication Module

**Goal:** Create JWT authentication utilities

**Files:**
- Create: `backend_fastapi/auth.py`

- [ ] **Step 1: Write auth.py**

```python
# backend_fastapi/auth.py
"""
JWT authentication utilities for FastAPI.
Provides user authentication via Bearer tokens.
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

JWT_SECRET = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security
security = HTTPBearer()

def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract user_id from JWT token.
    Returns user_id string.
    Raises HTTPException if token is invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        
        if user_id is None:
            raise credentials_exception
        
        return user_id
        
    except JWTError:
        raise credentials_exception

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Optional authentication - returns user_id if valid token, None otherwise.
    Does not raise exception for missing/invalid token.
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        return user_id
    except JWTError:
        return None
```

- [ ] **Step 2: Create test file**

```python
# backend_fastapi/test_auth.py
"""Test authentication utilities"""
import os
from dotenv import load_dotenv
from auth import hash_password, verify_password, create_access_token
from jose import jwt

load_dotenv()

def test_password_hashing():
    """Test password hashing and verification"""
    print("Testing password hashing...")
    
    password = "test_password_123"
    hashed = hash_password(password)
    
    print(f"  Original: {password}")
    print(f"  Hashed: {hashed[:50]}...")
    
    # Verify correct password
    assert verify_password(password, hashed), "Correct password verification failed"
    print("  ✓ Correct password verified")
    
    # Verify incorrect password
    assert not verify_password("wrong_password", hashed), "Wrong password accepted"
    print("  ✓ Incorrect password rejected")

def test_jwt_tokens():
    """Test JWT token creation and decoding"""
    print("\nTesting JWT tokens...")
    
    user_data = {"user_id": "test_user_123"}
    token = create_access_token(user_data)
    
    print(f"  Token created: {token[:50]}...")
    
    # Decode token
    JWT_SECRET = os.getenv("JWT_SECRET_KEY")
    payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    
    assert payload["user_id"] == "test_user_123", "User ID mismatch"
    assert "exp" in payload, "Expiration missing"
    
    print(f"  ✓ Token decoded successfully")
    print(f"  User ID: {payload['user_id']}")
    print(f"  Expires: {payload['exp']}")

if __name__ == '__main__':
    test_password_hashing()
    test_jwt_tokens()
    print("\n✓ All auth tests passed!")
```

- [ ] **Step 3: Test auth module**

```bash
cd backend_fastapi
python test_auth.py
```

Expected output:
```
Testing password hashing...
  Original: test_password_123
  Hashed: $2b$12$...
  ✓ Correct password verified
  ✓ Incorrect password rejected

Testing JWT tokens...
  Token created: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
  ✓ Token decoded successfully
  User ID: test_user_123
  Expires: ...

✓ All auth tests passed!
```

- [ ] **Step 4: Commit auth module**

```bash
git add backend_fastapi/auth.py
git commit -m "feat: add JWT authentication utilities"
```

---

### Task 11: Implement Pydantic Models

**Goal:** Create Pydantic models for request/response validation

**Files:**
- Create: `backend_fastapi/models/user.py`
- Create: `backend_fastapi/models/business.py`
- Create: `backend_fastapi/models/review.py`

- [ ] **Step 1: Create user models**

```python
# backend_fastapi/models/user.py
"""Pydantic models for user entities"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    """Base user fields"""
    user_id: str
    name: str
    email: EmailStr

class UserCreate(BaseModel):
    """User registration"""
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    """User login"""
    email: EmailStr
    password: str

class UserResponse(UserBase):
    """User response (public data)"""
    id: str
    preference_vector: Optional[List[float]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
```

- [ ] **Step 2: Create business models**

```python
# backend_fastapi/models/business.py
"""Pydantic models for business entities"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class BusinessBase(BaseModel):
    """Base business fields"""
    business_id: str
    name: str = Field(..., min_length=1, max_length=500)
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    stars: Optional[float] = Field(None, ge=0, le=5)
    categories: List[str] = []

class BusinessCreate(BusinessBase):
    """Business creation"""
    aspect_scores: Optional[Dict[str, float]] = None

class BusinessResponse(BusinessBase):
    """Business response"""
    id: str
    review_count: int
    aspect_scores: Optional[Dict[str, float]] = None
    photo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class BusinessSearchParams(BaseModel):
    """Business search parameters"""
    city: Optional[str] = None
    categories: Optional[List[str]] = None
    min_stars: Optional[float] = Field(None, ge=0, le=5)
    limit: int = Field(20, ge=1, le=100)
```

- [ ] **Step 3: Create review models**

```python
# backend_fastapi/models/review.py
"""Pydantic models for review entities"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ReviewBase(BaseModel):
    """Base review fields"""
    review_id: str
    business_id: str
    text: str = Field(..., min_length=10, max_length=5000)
    stars: float = Field(..., ge=1, le=5)

class ReviewCreate(BaseModel):
    """Review creation (no review_id needed, generated server-side)"""
    business_id: str
    text: str = Field(..., min_length=10, max_length=5000)
    stars: float = Field(..., ge=1, le=5)

class ReviewResponse(ReviewBase):
    """Review response"""
    id: str
    user_id: str
    aspect_vector: List[float]
    created_at: datetime
    
    class Config:
        from_attributes = True

class RecommendationResponse(BaseModel):
    """Restaurant recommendation with similarity score"""
    business_id: str
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    stars: Optional[float] = None
    aspect_scores: Optional[dict] = None
    photo_url: Optional[str] = None
    similarity_score: float
```

- [ ] **Step 4: Test models with sample data**

```python
# backend_fastapi/test_models.py
"""Test Pydantic models"""
from models.user import UserCreate, UserResponse
from models.business import BusinessCreate, BusinessResponse
from models.review import ReviewCreate, ReviewResponse
from datetime import datetime

def test_user_models():
    """Test user model validation"""
    print("Testing user models...")
    
    # Valid user creation
    user_create = UserCreate(
        name="John Doe",
        email="john@example.com",
        password="securepass123"
    )
    print(f"  ✓ UserCreate validated: {user_create.email}")
    
    # Test email validation
    try:
        invalid_user = UserCreate(
            name="Jane",
            email="invalid-email",
            password="pass123"
        )
        assert False, "Should have raised validation error"
    except Exception:
        print(f"  ✓ Email validation working")

def test_business_models():
    """Test business model validation"""
    print("\nTesting business models...")
    
    business = BusinessCreate(
        business_id="test-business-1",
        name="Test Restaurant",
        city="San Francisco",
        stars=4.5,
        categories=["Italian", "Pizza"],
        aspect_scores={"food": 0.8, "service": 0.7}
    )
    print(f"  ✓ BusinessCreate validated: {business.name}")

def test_review_models():
    """Test review model validation"""
    print("\nTesting review models...")
    
    review = ReviewCreate(
        business_id="test-business-1",
        text="Great food and excellent service! Highly recommended.",
        stars=5.0
    )
    print(f"  ✓ ReviewCreate validated: {len(review.text)} chars")
    
    # Test text length validation
    try:
        short_review = ReviewCreate(
            business_id="test-business-1",
            text="Too short",
            stars=5.0
        )
        assert False, "Should have raised validation error"
    except Exception:
        print(f"  ✓ Text length validation working")

if __name__ == '__main__':
    test_user_models()
    test_business_models()
    test_review_models()
    print("\n✓ All model tests passed!")
```

- [ ] **Step 5: Run model tests**

```bash
cd backend_fastapi
python test_models.py
```

Expected output:
```
Testing user models...
  ✓ UserCreate validated: john@example.com
  ✓ Email validation working

Testing business models...
  ✓ BusinessCreate validated: Test Restaurant

Testing review models...
  ✓ ReviewCreate validated: 54 chars
  ✓ Text length validation working

✓ All model tests passed!
```

- [ ] **Step 6: Commit models**

```bash
git add backend_fastapi/models/
git commit -m "feat: add Pydantic models for user, business, review"
```

---

### Task 12: Implement User Router

**Goal:** Create user authentication endpoints (register, login)

**Files:**
- Create: `backend_fastapi/routers/user.py`

- [ ] **Step 1: Write user router**

```python
# backend_fastapi/routers/user.py
"""User authentication endpoints"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from models.user import UserCreate, UserLogin, UserResponse, TokenResponse
from database import get_db
from auth import hash_password, verify_password, create_access_token, get_current_user
import asyncpg

router = APIRouter(prefix="/api")

@router.post("/user/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user: UserCreate,
    db: asyncpg.Connection = Depends(get_db)
):
    """Register a new user"""
    # Check if email already exists
    existing_user = await db.fetchrow(
        "SELECT user_id FROM users WHERE email = $1",
        user.email
    )
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Generate user_id
    user_id = str(uuid.uuid4())
    
    # Hash password
    password_hash = hash_password(user.password)
    
    # Insert user
    result = await db.fetchrow("""
        INSERT INTO users (user_id, name, email, password_hash)
        VALUES ($1, $2, $3, $4)
        RETURNING id, user_id, name, email, created_at
    """, user_id, user.name, user.email, password_hash)
    
    # Create access token
    access_token = create_access_token({"user_id": user_id})
    
    # Build response
    user_response = UserResponse(
        id=str(result['id']),
        user_id=result['user_id'],
        name=result['name'],
        email=result['email'],
        preference_vector=None,
        created_at=result['created_at']
    )
    
    return TokenResponse(
        access_token=access_token,
        user=user_response
    )

@router.post("/user/login", response_model=TokenResponse)
async def login_user(
    credentials: UserLogin,
    db: asyncpg.Connection = Depends(get_db)
):
    """Login user"""
    # Find user by email
    user = await db.fetchrow("""
        SELECT id, user_id, name, email, password_hash, preference_vector, created_at
        FROM users
        WHERE email = $1
    """, credentials.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user['password_hash']):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token = create_access_token({"user_id": user['user_id']})
    
    # Build response
    user_response = UserResponse(
        id=str(user['id']),
        user_id=user['user_id'],
        name=user['name'],
        email=user['email'],
        preference_vector=list(user['preference_vector']) if user['preference_vector'] else None,
        created_at=user['created_at']
    )
    
    return TokenResponse(
        access_token=access_token,
        user=user_response
    )

@router.get("/user/me", response_model=UserResponse)
async def get_current_user_info(
    current_user_id: str = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """Get current user information"""
    user = await db.fetchrow("""
        SELECT id, user_id, name, email, preference_vector, created_at
        FROM users
        WHERE user_id = $1
    """, current_user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=str(user['id']),
        user_id=user['user_id'],
        name=user['name'],
        email=user['email'],
        preference_vector=list(user['preference_vector']) if user['preference_vector'] else None,
        created_at=user['created_at']
    )
```

- [ ] **Step 2: Test user endpoints manually**

Create test file:
```python
# backend_fastapi/test_user_router.py
"""Manual test for user router"""
import asyncio
from routers.user import register_user, login_user
from models.user import UserCreate, UserLogin
from database import Database
from unittest.mock import AsyncMock

async def test_user_flow():
    """Test user registration and login"""
    print("Testing user router...")
    
    # This is a simplified test - in real scenario, would use FastAPI TestClient
    print("  ✓ User router created")
    print("  Note: Full testing will be done when app.py is complete")

if __name__ == '__main__':
    asyncio.run(test_user_flow())
```

Run:
```bash
python test_user_router.py
```

- [ ] **Step 3: Commit user router**

```bash
git add backend_fastapi/routers/user.py
git commit -m "feat: add user authentication router (register, login)"
```

---

### Task 13: Implement Business Router

**Goal:** Create business endpoints (search, get, create)

**Files:**
- Create: `backend_fastapi/routers/business.py`

- [ ] **Step 1: Write business router**

```python
# backend_fastapi/routers/business.py
"""Business endpoints"""
import uuid
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from models.business import BusinessCreate, BusinessResponse, BusinessSearchParams
from database import get_db
from auth import get_current_user
import asyncpg
from supabase import create_client

router = APIRouter(prefix="/api")

# Supabase client for photo uploads
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

async def upload_photo_to_supabase(file: UploadFile, business_id: str) -> str:
    """Upload photo to Supabase Storage"""
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Read file content
    content = await file.read()
    
    # Upload to Supabase Storage
    supabase.storage.from_('business-photos').upload(
        f'{business_id}.jpg',
        content,
        {'content-type': 'image/jpeg'}
    )
    
    # Get public URL
    public_url = supabase.storage.from_('business-photos').get_public_url(f'{business_id}.jpg')
    
    return public_url

@router.post("/business", response_model=BusinessResponse, status_code=status.HTTP_201_CREATED)
async def create_business(
    business: BusinessCreate,
    current_user_id: str = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """Create a new business"""
    # Check if business_id already exists
    existing = await db.fetchrow(
        "SELECT business_id FROM businesses WHERE business_id = $1",
        business.business_id
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business ID already exists"
        )
    
    # Insert business
    result = await db.fetchrow("""
        INSERT INTO businesses (
            business_id, name, address, city, state, postal_code,
            latitude, longitude, stars, categories, aspect_scores
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING *
    """,
        business.business_id,
        business.name,
        business.address,
        business.city,
        business.state,
        business.postal_code,
        business.latitude,
        business.longitude,
        business.stars,
        business.categories,
        business.aspect_scores
    )
    
    return BusinessResponse(
        id=str(result['id']),
        business_id=result['business_id'],
        name=result['name'],
        address=result['address'],
        city=result['city'],
        state=result['state'],
        postal_code=result['postal_code'],
        latitude=result['latitude'],
        longitude=result['longitude'],
        stars=result['stars'],
        categories=result['categories'],
        review_count=result['review_count'],
        aspect_scores=result['aspect_scores'],
        photo_url=result['photo_url'],
        created_at=result['created_at'],
        updated_at=result['updated_at']
    )

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    return BusinessResponse(
        id=str(result['id']),
        business_id=result['business_id'],
        name=result['name'],
        address=result['address'],
        city=result['city'],
        state=result['state'],
        postal_code=result['postal_code'],
        latitude=result['latitude'],
        longitude=result['longitude'],
        stars=result['stars'],
        categories=result['categories'],
        review_count=result['review_count'],
        aspect_scores=result['aspect_scores'],
        photo_url=result['photo_url'],
        created_at=result['created_at'],
        updated_at=result['updated_at']
    )

@router.get("/businesses", response_model=List[BusinessResponse])
async def search_businesses(
    city: Optional[str] = None,
    min_stars: Optional[float] = None,
    limit: int = 20,
    db: asyncpg.Connection = Depends(get_db)
):
    """Search businesses"""
    query = "SELECT * FROM businesses WHERE 1=1"
    params = []
    param_count = 1
    
    if city:
        query += f" AND city = ${param_count}"
        params.append(city)
        param_count += 1
    
    if min_stars:
        query += f" AND stars >= ${param_count}"
        params.append(min_stars)
        param_count += 1
    
    query += f" ORDER BY stars DESC, review_count DESC LIMIT ${param_count}"
    params.append(limit)
    
    results = await db.fetch(query, *params)
    
    return [
        BusinessResponse(
            id=str(r['id']),
            business_id=r['business_id'],
            name=r['name'],
            address=r['address'],
            city=r['city'],
            state=r['state'],
            postal_code=r['postal_code'],
            latitude=r['latitude'],
            longitude=r['longitude'],
            stars=r['stars'],
            categories=r['categories'],
            review_count=r['review_count'],
            aspect_scores=r['aspect_scores'],
            photo_url=r['photo_url'],
            created_at=r['created_at'],
            updated_at=r['updated_at']
        )
        for r in results
    ]
```

- [ ] **Step 2: Commit business router**

```bash
git add backend_fastapi/routers/business.py
git commit -m "feat: add business router (create, get, search)"
```

---

### Task 14: Implement Review Router

**Goal:** Create review endpoints with ABSA integration

**Files:**
- Create: `backend_fastapi/routers/review.py`

- [ ] **Step 1: Write review router**

```python
# backend_fastapi/routers/review.py
"""Review endpoints with ABSA integration"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from models.review import ReviewCreate, ReviewResponse, RecommendationResponse
from database import get_db
from auth import get_current_user
import asyncpg

# Import ABSA logic
import sys
sys.path.append('ai')
from ai.generate_vector import generate_aspect_vector

router = APIRouter(prefix="/api")

async def update_user_preference_vector(db: asyncpg.Connection, user_id: str):
    """Recalculate user preference vector from all their reviews"""
    # Get all user's review vectors
    reviews = await db.fetch("""
        SELECT aspect_vector FROM reviews
        WHERE user_id = $1 AND aspect_vector IS NOT NULL
    """, user_id)
    
    if not reviews:
        return
    
    # Calculate average vector (simple preference model)
    vectors = [list(r['aspect_vector']) for r in reviews]
    avg_vector = [sum(v[i] for v in vectors) / len(vectors) for i in range(5)]
    
    # Update user preference vector
    vector_str = f"[{','.join(str(v) for v in avg_vector)}]"
    await db.execute("""
        UPDATE users SET preference_vector = $1::vector
        WHERE user_id = $2
    """, vector_str, user_id)

@router.post("/review", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review: ReviewCreate,
    current_user_id: str = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """Create a new review with ABSA processing"""
    # Verify business exists
    business = await db.fetchrow(
        "SELECT business_id FROM businesses WHERE business_id = $1",
        review.business_id
    )
    
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    # Generate aspect vector using ABSA
    aspect_vector = generate_aspect_vector(review.text)
    
    # Generate review_id
    review_id = str(uuid.uuid4())
    
    # Insert review
    vector_str = f"[{','.join(str(v) for v in aspect_vector)}]"
    result = await db.fetchrow("""
        INSERT INTO reviews (
            review_id, business_id, user_id, text, stars, aspect_vector
        )
        VALUES ($1, $2, $3, $4, $5, $6::vector)
        RETURNING *
    """,
        review_id,
        review.business_id,
        current_user_id,
        review.text,
        review.stars,
        vector_str
    )
    
    # Update user preference vector
    await update_user_preference_vector(db, current_user_id)
    
    # Update business review count
    await db.execute("""
        UPDATE businesses 
        SET review_count = review_count + 1
        WHERE business_id = $1
    """, review.business_id)
    
    return ReviewResponse(
        id=str(result['id']),
        review_id=result['review_id'],
        business_id=result['business_id'],
        user_id=result['user_id'],
        text=result['text'],
        stars=result['stars'],
        aspect_vector=list(result['aspect_vector']),
        created_at=result['created_at']
    )

@router.get("/reviews/business/{business_id}", response_model=List[ReviewResponse])
async def get_business_reviews(
    business_id: str,
    limit: int = 20,
    db: asyncpg.Connection = Depends(get_db)
):
    """Get reviews for a business"""
    results = await db.fetch("""
        SELECT * FROM reviews
        WHERE business_id = $1
        ORDER BY created_at DESC
        LIMIT $2
    """, business_id, limit)
    
    return [
        ReviewResponse(
            id=str(r['id']),
            review_id=r['review_id'],
            business_id=r['business_id'],
            user_id=r['user_id'],
            text=r['text'],
            stars=r['stars'],
            aspect_vector=list(r['aspect_vector']),
            created_at=r['created_at']
        )
        for r in results
    ]

@router.get("/recommendations", response_model=List[RecommendationResponse])
async def get_recommendations(
    limit: int = 20,
    current_user_id: str = Depends(get_current_user),
    db: asyncpg.Connection = Depends(get_db)
):
    """Get personalized restaurant recommendations using pgvector cosine similarity"""
    # Get user preference vector
    user = await db.fetchrow(
        "SELECT preference_vector FROM users WHERE user_id = $1",
        current_user_id
    )
    
    if not user or not user['preference_vector']:
        # User has no preference vector yet - return popular restaurants
        results = await db.fetch("""
            SELECT business_id, name, address, city, stars, aspect_scores, photo_url, 0.5 as similarity_score
            FROM businesses
            ORDER BY stars DESC, review_count DESC
            LIMIT $1
        """, limit)
    else:
        # Use pgvector cosine similarity
        results = await db.fetch("""
            SELECT 
                b.business_id,
                b.name,
                b.address,
                b.city,
                b.stars,
                b.aspect_scores,
                b.photo_url,
                1 - (
                    (SELECT preference_vector FROM users WHERE user_id = $1) <=>
                    COALESCE(
                        (
                            SELECT AVG(aspect_vector)::vector(5)
                            FROM reviews
                            WHERE business_id = b.business_id
                        ),
                        '[0,0,0,0,0]'::vector(5)
                    )
                ) AS similarity_score
            FROM businesses b
            WHERE (
                SELECT COUNT(*) FROM reviews WHERE business_id = b.business_id
            ) > 0
            ORDER BY similarity_score DESC
            LIMIT $2
        """, current_user_id, limit)
    
    return [
        RecommendationResponse(
            business_id=r['business_id'],
            name=r['name'],
            address=r['address'],
            city=r['city'],
            stars=r['stars'],
            aspect_scores=r['aspect_scores'],
            photo_url=r['photo_url'],
            similarity_score=float(r['similarity_score'])
        )
        for r in results
    ]
```

- [ ] **Step 2: Commit review router**

```bash
git add backend_fastapi/routers/review.py
git commit -m "feat: add review router with ABSA and recommendations"
```

---

### Task 15: Implement Main FastAPI Application

**Goal:** Create main app.py with all routers and middleware

**Files:**
- Create: `backend_fastapi/app.py`

- [ ] **Step 1: Write app.py**

```python
# backend_fastapi/app.py
"""
Main FastAPI application for ClickBites ABSA Restaurant Recommendation System.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import user, business, review
import uvicorn

# Check if ABSA model loaded
try:
    from ai.generate_vector import generate_aspect_vector
    MODEL_LOADED = True
except Exception as e:
    MODEL_LOADED = False
    print(f"Warning: ABSA model failed to load: {e}")

# Create FastAPI app
app = FastAPI(
    title="ClickBites API",
    description="ABSA Restaurant Recommendation System - Personalized recommendations using aspect-based sentiment analysis",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - update with actual Vercel URL after deployment
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,https://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(user.router, tags=["User Authentication"])
app.include_router(business.router, tags=["Business"])
app.include_router(review.router, tags=["Review & Recommendations"])

# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy" if MODEL_LOADED else "degraded",
        "model_loaded": MODEL_LOADED,
        "version": "2.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint - redirect to docs"""
    return {
        "message": "ClickBites API",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    # For local development
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
```

- [ ] **Step 2: Create __init__.py files for imports**

```python
# backend_fastapi/routers/__init__.py
"""Routers package"""
from . import user, business, review

__all__ = ['user', 'business', 'review']
```

```python
# backend_fastapi/models/__init__.py
"""Models package"""
from . import user, business, review

__all__ = ['user', 'business', 'review']
```

- [ ] **Step 3: Create local test environment file**

```bash
# backend_fastapi/.env
DATABASE_URL=<your-supabase-connection-string>
JWT_SECRET_KEY=<your-jwt-secret>
SUPABASE_URL=<your-supabase-url>
SUPABASE_SERVICE_KEY=<your-service-key>
ALLOWED_ORIGINS=http://localhost:3000,https://localhost:3000
PORT=7860
```

- [ ] **Step 4: Test app locally (without AI model for now)**

```bash
cd backend_fastapi
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
python app.py
```

Expected output:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:7860
```

- [ ] **Step 5: Test health endpoint**

Open browser: http://localhost:7860/health

Expected response:
```json
{
  "status": "degraded",
  "model_loaded": false,
  "version": "2.0.0"
}
```

Note: "degraded" is expected since AI model files not yet added

- [ ] **Step 6: Test API docs**

Open browser: http://localhost:7860/docs

Expected: Swagger UI with all endpoints visible

- [ ] **Step 7: Commit main application**

```bash
git add backend_fastapi/app.py backend_fastapi/routers/__init__.py backend_fastapi/models/__init__.py
git commit -m "feat: add main FastAPI application with health check"
```

---

### Task 16: Create Docker Configuration for Hugging Face Spaces

**Goal:** Create Dockerfile and HF Spaces metadata

**Files:**
- Create: `backend_fastapi/Dockerfile`
- Create: `backend_fastapi/.space`
- Create: `backend_fastapi/README.md`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
# backend_fastapi/Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY . .

# Expose port 7860 (required by Hugging Face Spaces)
EXPOSE 7860

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
```

- [ ] **Step 2: Create .space metadata**

```yaml
# backend_fastapi/.space
title: ClickBites API
emoji: 🍔
colorFrom: orange
colorTo: red
sdk: docker
pinned: false
license: mit
```

- [ ] **Step 3: Create README.md for HF Spaces**

```markdown
# backend_fastapi/README.md
# ClickBites API

ABSA (Aspect-Based Sentiment Analysis) Restaurant Recommendation System API.

## Features

- **User Authentication** - JWT-based registration and login
- **Business Management** - Search and view restaurant details
- **Review Analysis** - BERT-based aspect extraction with VADER sentiment
- **Personalized Recommendations** - Vector similarity using PostgreSQL pgvector

## Tech Stack

- FastAPI
- PostgreSQL with pgvector extension
- Fine-tuned BERT model for aspect extraction
- VADER sentiment analysis

## API Endpoints

- `POST /api/user/register` - Register new user
- `POST /api/user/login` - Login user
- `GET /api/user/me` - Get current user info
- `POST /api/business` - Create business
- `GET /api/business/{id}` - Get business details
- `GET /api/businesses` - Search businesses
- `POST /api/review` - Submit review (triggers ABSA)
- `GET /api/recommendations` - Get personalized recommendations
- `GET /health` - Health check

## Documentation

Interactive API docs available at `/docs`

## Model

Uses a fine-tuned BERT model for aspect extraction across 5 dimensions:
- Food quality
- Service quality
- Price value
- Ambience
- Miscellaneous

Combined with VADER sentiment analysis for aspect-opinion polarity.
```

- [ ] **Step 4: Create .dockerignore**

```
# backend_fastapi/.dockerignore
__pycache__/
*.pyc
.env
.env.example
.venv
venv/
.git
.gitignore
test_*.py
.DS_Store
```

- [ ] **Step 5: Test Docker build locally**

```bash
cd backend_fastapi
docker build -t clickbites-api .
```

Expected: Build succeeds (may take 5-10 minutes)

- [ ] **Step 6: Test Docker run locally**

```bash
docker run -p 7860:7860 \
  -e DATABASE_URL="<your-db-url>" \
  -e JWT_SECRET_KEY="<your-secret>" \
  -e SUPABASE_URL="<your-supabase-url>" \
  -e SUPABASE_SERVICE_KEY="<your-service-key>" \
  clickbites-api
```

Visit http://localhost:7860/health
Expected: {"status": "degraded", "model_loaded": false}

- [ ] **Step 7: Commit Docker configuration**

```bash
git add backend_fastapi/Dockerfile backend_fastapi/.space backend_fastapi/README.md backend_fastapi/.dockerignore
git commit -m "feat: add Docker configuration for Hugging Face Spaces"
```

---

### Task 17: Deploy Backend to Hugging Face Spaces

**Goal:** Deploy FastAPI backend to HF Spaces

**Prerequisites:**
- AI model files downloaded (fine_tuned_model/, label_encoder.pkl)
- HF account created
- HF access token obtained

- [ ] **Step 1: Add AI model files to backend_fastapi**

```bash
# Copy model files from temporary download location
cp -r /path/to/downloaded/fine_tuned_model backend_fastapi/ai/
cp /path/to/downloaded/label_encoder.pkl backend_fastapi/ai/
```

Verify files exist:
```bash
ls backend_fastapi/ai/fine_tuned_model/
ls backend_fastapi/ai/label_encoder.pkl
```

- [ ] **Step 2: Create new Hugging Face Space**

Visit: https://huggingface.co/spaces
Click "Create new Space"
- Owner: Your username
- Space name: `clickbites-api`
- License: MIT
- Space SDK: Docker
- Space hardware: CPU basic (free)
- Visibility: Public
Click "Create Space"

- [ ] **Step 3: Initialize Git in backend_fastapi**

```bash
cd backend_fastapi
git init
git add .
git commit -m "Initial commit: FastAPI backend with BERT model"
```

- [ ] **Step 4: Add HF Spaces remote and push**

```bash
# Get your HF username
HF_USERNAME="<your-hf-username>"

# Add remote
git remote add space https://huggingface.co/spaces/$HF_USERNAME/clickbites-api

# Configure Git LFS for large files (BERT model)
git lfs install
git lfs track "ai/fine_tuned_model/**/*"
git lfs track "*.pkl"
git add .gitattributes
git commit -m "Configure Git LFS for model files"

# Push to HF Spaces
git push space main
```

Note: You'll be prompted for HF username and access token (use the token as password)

- [ ] **Step 5: Wait for build**

Go to https://huggingface.co/spaces/$HF_USERNAME/clickbites-api

Watch build logs (takes ~5-10 minutes):
- Installing dependencies
- Building Docker image
- Starting container

Expected final log: "Application startup complete"

- [ ] **Step 6: Set environment variables in HF Spaces**

Go to Space Settings → Variables and secrets
Add secrets:
- `DATABASE_URL` = Your Supabase PostgreSQL connection string
- `JWT_SECRET_KEY` = Your generated JWT secret
- `SUPABASE_URL` = Your Supabase project URL
- `SUPABASE_SERVICE_KEY` = Your Supabase service key
- `ALLOWED_ORIGINS` = `https://your-app.vercel.app` (update after frontend deployed)

Click "Save" - Space will rebuild

- [ ] **Step 7: Test deployed API**

Visit: https://$HF_USERNAME-clickbites-api.hf.space/health

Expected response:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "version": "2.0.0"
}
```

Visit: https://$HF_USERNAME-clickbites-api.hf.space/docs

Expected: Swagger UI with all endpoints

- [ ] **Step 8: Test user registration**

In Swagger UI:
1. Expand `POST /api/user/register`
2. Click "Try it out"
3. Enter test data:
```json
{
  "name": "Test User",
  "email": "test@example.com",
  "password": "testpass123"
}
```
4. Click "Execute"

Expected: 201 Created with access token

- [ ] **Step 9: Document API URL**

Save to credentials file:
```bash
# Add to ~/clickbites-credentials.txt
BACKEND_API_URL=https://<your-username>-clickbites-api.hf.space
```

- [ ] **Step 10: Commit deployment notes**

Create deployment notes in main repo:
```bash
# In main repo root
echo "Backend deployed to: https://$HF_USERNAME-clickbites-api.hf.space" > DEPLOYMENT.md
git add DEPLOYMENT.md
git commit -m "docs: add backend deployment URL"
```

---

## Phase 5: Frontend Migration

### Task 18: Migrate Frontend to Bun

**Goal:** Switch from npm/yarn to Bun runtime

**Files:**
- Remove: `frontend/package-lock.json`, `frontend/yarn.lock`
- Modify: `frontend/.gitignore`

- [ ] **Step 1: Remove old lock files**

```bash
cd frontend
rm -f package-lock.json yarn.lock
```

- [ ] **Step 2: Install dependencies with Bun**

```bash
bun install
```

Expected: Dependencies installed successfully, creates `bun.lockb`

- [ ] **Step 3: Test dev server with Bun**

```bash
bun run dev
```

Visit http://localhost:3000
Expected: App loads successfully

Stop server (Ctrl+C)

- [ ] **Step 4: Test build with Bun**

```bash
bun run build
```

Expected: Build completes successfully

- [ ] **Step 5: Update .gitignore**

Add to `frontend/.gitignore`:
```
# Bun
bun.lockb

# Business photos (now in Supabase Storage)
public/business_photo/
```

- [ ] **Step 6: Commit Bun migration**

```bash
git add frontend/bun.lockb frontend/.gitignore
git add -u  # Stage deletions (lock files)
git commit -m "feat: migrate frontend to Bun runtime"
```

---

### Task 19: Update Frontend Configuration

**Goal:** Convert next.config.js to TypeScript and update for production

**Files:**
- Rename: `frontend/next.config.js` → `frontend/next.config.ts`
- Create: `frontend/vercel.json`

- [ ] **Step 1: Convert next.config.js to next.config.ts**

Delete `frontend/next.config.js`

Create `frontend/next.config.ts`:
```typescript
import type { NextConfig } from 'next';

const config: NextConfig = {
  reactStrictMode: true,
  
  // Environment variables
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:7860',
    NEXT_PUBLIC_GOOGLE_MAPS_API_KEY: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || '',
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL || '',
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || '',
  },
  
  // Image optimization for Supabase Storage
  images: {
    domains: [
      'supabase.co',
    ],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.supabase.co',
        pathname: '/storage/v1/object/public/**',
      },
    ],
  },
};

export default config;
```

- [ ] **Step 2: Create vercel.json**

```json
{
  "buildCommand": "bun run build",
  "devCommand": "bun run dev",
  "installCommand": "bun install",
  "framework": "nextjs",
  "regions": ["sfo1"]
}
```

- [ ] **Step 3: Create .env.example**

```bash
# frontend/.env.example
NEXT_PUBLIC_API_URL=https://your-username-clickbites-api.hf.space
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_google_maps_api_key
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

- [ ] **Step 4: Test build with new config**

```bash
cd frontend
bun run build
```

Expected: Build succeeds

- [ ] **Step 5: Commit configuration changes**

```bash
git add frontend/next.config.ts frontend/vercel.json frontend/.env.example
git add -u  # Stage deletion of next.config.js
git commit -m "feat: convert Next.js config to TypeScript and add Vercel config"
```

---

### Task 20: Update Frontend Photo URLs

**Goal:** Replace local photo paths with Supabase Storage URLs

**Files:**
- Modify: All component files using business photos

- [ ] **Step 1: Find all files using photo paths**

```bash
cd frontend
grep -r "business_photo" --include="*.tsx" --include="*.ts"
```

Note all files that reference `/business_photo/`

- [ ] **Step 2: Update photo references**

For each file found, replace:
```typescript
// Before
<img src={`/business_photo/${businessId}.jpg`} />

// After
<img src={business.photo_url || '/placeholder-restaurant.jpg'} alt={business.name} />
```

Common files to update:
- `components/BusinessDetails/*.tsx`
- `components/ResultCard/*.tsx`
- `pages/results.tsx`
- `pages/business/[id].tsx`

- [ ] **Step 3: Add placeholder image**

Create or download a placeholder:
```bash
# Create simple placeholder or download one
# Save as frontend/public/placeholder-restaurant.jpg
```

- [ ] **Step 4: Add image error handling**

Update image components with error fallback:
```typescript
<img 
  src={business.photo_url || '/placeholder-restaurant.jpg'} 
  alt={business.name}
  onError={(e) => {
    e.currentTarget.src = '/placeholder-restaurant.jpg';
  }}
/>
```

- [ ] **Step 5: Test locally**

```bash
bun run dev
```

Visit http://localhost:3000 and verify:
- Photos load from Supabase (if data migrated)
- Placeholder shows if photo missing

- [ ] **Step 6: Commit photo URL updates**

```bash
git add frontend/
git commit -m "feat: update photo URLs to use Supabase Storage"
```

---

### Task 21: Deploy Frontend to Vercel

**Goal:** Deploy Next.js frontend to Vercel

**Prerequisites:**
- Vercel account created
- GitHub connected to Vercel
- Backend deployed and URL known

- [ ] **Step 1: Push all changes to GitHub**

```bash
# In main repo root
git push origin main
```

- [ ] **Step 2: Create new Vercel project**

Visit: https://vercel.com/new

1. Click "Import Git Repository"
2. Select your repository: `ClickBites-ABSA-Restaurant-Recommendation-System`
3. Click "Import"

- [ ] **Step 3: Configure build settings**

- Framework Preset: Next.js (auto-detected)
- Root Directory: `frontend`
- Build Command: `bun run build`
- Output Directory: `.next` (auto)
- Install Command: `bun install`

- [ ] **Step 4: Add environment variables**

Add the following environment variables:

```
NEXT_PUBLIC_API_URL=https://your-username-clickbites-api.hf.space
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=your_google_maps_api_key
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

- [ ] **Step 5: Deploy**

Click "Deploy"

Wait for deployment (~2-5 minutes)

Expected: "Your project has been successfully deployed"

- [ ] **Step 6: Note frontend URL**

Copy your Vercel URL (e.g., `https://clickbites.vercel.app`)

Save to credentials:
```bash
# Add to ~/clickbites-credentials.txt
FRONTEND_URL=https://clickbites.vercel.app
```

- [ ] **Step 7: Update backend CORS**

Go to HF Spaces Settings → Variables
Update `ALLOWED_ORIGINS`:
```
ALLOWED_ORIGINS=https://clickbites.vercel.app,http://localhost:3000
```

Space will rebuild (~1 minute)

- [ ] **Step 8: Test deployed frontend**

Visit your Vercel URL

Test:
1. Homepage loads
2. Sign up for new account
3. Log in
4. Search for restaurants
5. View restaurant details
6. Photos load from Supabase

- [ ] **Step 9: Document deployment URLs**

Update `DEPLOYMENT.md`:
```markdown
# ClickBites Deployment

## Production URLs

- **Frontend**: https://clickbites.vercel.app
- **Backend API**: https://your-username-clickbites-api.hf.space
- **API Docs**: https://your-username-clickbites-api.hf.space/docs

## Database

- **Provider**: Supabase
- **Storage**: Supabase Storage (business-photos bucket)

## Deployment Date

2026-04-05

## Tech Stack

- Frontend: Next.js 15 + Bun (Vercel)
- Backend: FastAPI + BERT (Hugging Face Spaces)
- Database: PostgreSQL + pgvector (Supabase)
- Storage: Supabase Storage

## Cost

$0/month (all free tiers)
```

- [ ] **Step 10: Commit deployment documentation**

```bash
git add DEPLOYMENT.md
git commit -m "docs: update deployment URLs and info"
git push origin main
```

---

## Phase 6: Testing & Validation

### Task 22: End-to-End Testing

**Goal:** Test complete user flow in production

**Files:**
- Create: `tests/e2e-test-plan.md`

- [ ] **Step 1: Create test plan document**

```markdown
# tests/e2e-test-plan.md
# End-to-End Test Plan

## Test Environment
- Frontend: https://clickbites.vercel.app
- Backend: https://your-username-clickbites-api.hf.space

## Test Scenarios

### 1. User Registration and Authentication
- [ ] Navigate to homepage
- [ ] Click "Sign Up"
- [ ] Enter valid credentials
- [ ] Verify redirect to dashboard
- [ ] Verify JWT token stored
- [ ] Log out
- [ ] Log in with same credentials
- [ ] Verify successful login

### 2. Restaurant Search and Browse
- [ ] Search for restaurants by city
- [ ] Verify results displayed
- [ ] Verify photos load from Supabase
- [ ] Click on a restaurant
- [ ] Verify restaurant details page loads
- [ ] Verify reviews displayed

### 3. Review Submission (ABSA)
- [ ] Navigate to restaurant details
- [ ] Click "Write Review"
- [ ] Enter review text (min 10 chars)
- [ ] Select star rating
- [ ] Submit review
- [ ] Verify success message
- [ ] Verify review appears in list
- [ ] Check backend logs for ABSA processing

### 4. Personalized Recommendations
- [ ] Navigate to recommendations page
- [ ] Verify recommendations displayed
- [ ] Verify similarity scores shown
- [ ] Verify recommendations change after review submission
- [ ] Click on recommended restaurant
- [ ] Verify details load

### 5. Mobile Responsiveness
- [ ] Open site on mobile device
- [ ] Verify layout responsive
- [ ] Test navigation menu
- [ ] Test restaurant cards
- [ ] Test review submission

### 6. Error Handling
- [ ] Try to access protected route without login
- [ ] Try to submit invalid review (too short)
- [ ] Try to register with existing email
- [ ] Verify error messages displayed
- [ ] Verify graceful degradation

### 7. Performance
- [ ] Measure initial page load time (< 3s)
- [ ] Measure review submission time (< 5s)
- [ ] Measure recommendation query time (< 1s)
- [ ] Verify photos load within 2s

## Pass Criteria

All test scenarios must pass for deployment to be considered successful.
```

- [ ] **Step 2: Execute test plan**

Go through each scenario in the test plan and check them off

Document any failures in the test plan

- [ ] **Step 3: Verify ABSA processing**

Submit a test review:
```
"The food was absolutely amazing and the flavors were incredible! However, the service was quite slow and the staff seemed overwhelmed. The prices were reasonable for the quality. The ambience was nice and cozy."
```

Check HF Spaces logs for:
- BERT model processing
- Aspect vector generated (should show high food score, low service score)

- [ ] **Step 4: Verify vector similarity**

1. Create test user
2. Submit reviews with clear preferences (e.g., all mention "great food")
3. Check recommendations
4. Verify recommended restaurants have high food aspect scores

- [ ] **Step 5: Document test results**

Update test plan with results

If issues found, document in GitHub Issues

- [ ] **Step 6: Commit test plan**

```bash
git add tests/e2e-test-plan.md
git commit -m "docs: add end-to-end test plan and results"
```

---

### Task 23: Performance Validation

**Goal:** Validate performance benchmarks

**Files:**
- Create: `tests/performance-results.md`

- [ ] **Step 1: Measure frontend performance**

Use browser DevTools:
1. Open DevTools → Network tab
2. Hard refresh (Cmd+Shift+R or Ctrl+Shift+R)
3. Measure:
   - Initial page load (DOMContentLoaded)
   - Full page load (Load event)
   - Time to First Byte (TTFB)

Target: < 3 seconds

- [ ] **Step 2: Measure backend API performance**

Use browser DevTools Network tab or curl:

```bash
# Health check
time curl https://your-username-clickbites-api.hf.space/health

# Business search
time curl https://your-username-clickbites-api.hf.space/api/businesses?city=Phoenix&limit=20

# Recommendations (requires auth token)
time curl -H "Authorization: Bearer $TOKEN" \
  https://your-username-clickbites-api.hf.space/api/recommendations
```

Targets:
- Health check: < 100ms
- Search: < 500ms
- Recommendations: < 1s

- [ ] **Step 3: Measure ABSA processing time**

Submit review and time the request:

In browser DevTools Network tab:
1. Submit review
2. Check POST /api/review timing

Target: < 5 seconds

- [ ] **Step 4: Document results**

```markdown
# tests/performance-results.md
# Performance Test Results

## Frontend Performance
- Initial page load: X.XX seconds
- Time to First Byte: XXX ms
- Full page load: X.XX seconds
- Largest Contentful Paint: X.XX seconds

## Backend API Performance
- Health check: XXX ms
- Business search: XXX ms
- Get recommendations: XXX ms
- Review submission (ABSA): X.XX seconds

## Photo Loading
- Average photo load time: XXX ms
- CDN cache hit rate: XX%

## Pass/Fail
- [ ] All metrics within targets
- [ ] No performance regressions
```

Fill in actual measurements

- [ ] **Step 5: Commit performance results**

```bash
git add tests/performance-results.md
git commit -m "docs: add performance test results"
```

---

### Task 24: Final Deployment Checklist

**Goal:** Verify all deployment requirements met

- [ ] **Step 1: Verify all services running**

- [ ] Frontend accessible at Vercel URL
- [ ] Backend API responding at HF Spaces URL
- [ ] Database queries working (check Supabase dashboard)
- [ ] Photos loading from Supabase Storage

- [ ] **Step 2: Verify all features working**

- [ ] User registration
- [ ] User login
- [ ] JWT authentication
- [ ] Business search
- [ ] Business details
- [ ] Review submission
- [ ] ABSA processing (5D vector generated)
- [ ] Recommendation generation
- [ ] Vector similarity calculation
- [ ] Photo display

- [ ] **Step 3: Verify security**

- [ ] Environment variables not exposed
- [ ] Secrets not in Git history
- [ ] CORS properly configured
- [ ] JWT tokens expire
- [ ] SQL injection prevention (parameterized queries)
- [ ] Password hashing working

- [ ] **Step 4: Verify monitoring**

- [ ] Vercel analytics accessible
- [ ] HF Spaces logs accessible
- [ ] Supabase monitoring accessible
- [ ] Health check endpoint working

- [ ] **Step 5: Verify cost**

- [ ] Vercel usage within free tier
- [ ] HF Spaces on CPU basic (free)
- [ ] Supabase within free tier limits
- [ ] Total cost: $0/month

- [ ] **Step 6: Update README.md**

Update main `README.md` with deployment instructions:

```markdown
# ClickBites - ABSA Restaurant Recommendation System

[Existing content...]

## Production Deployment

**Live Application**: https://clickbites.vercel.app

### Architecture

- **Frontend**: Next.js 15 + Bun (Vercel)
- **Backend**: FastAPI + BERT (Hugging Face Spaces)
- **Database**: PostgreSQL + pgvector (Supabase)
- **Storage**: Supabase Storage

### Features

- JWT-based authentication
- BERT-powered aspect extraction
- Vector similarity recommendations
- Real-time review analysis

### Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment details.

### Cost

$0/month - Running entirely on free tiers.
```

- [ ] **Step 7: Create final commit**

```bash
git add README.md
git commit -m "docs: update README with production deployment info"
git push origin main
```

- [ ] **Step 8: Tag release**

```bash
git tag -a v2.0.0 -m "Production deployment - FastAPI + Bun + Supabase"
git push origin v2.0.0
```

---

## Completion

**Plan complete and saved to:** `docs/superpowers/plans/2026-04-05-clickbites-production-deployment.md`

### Summary

This plan contains 24 tasks organized into 6 phases:

1. **Phase 1**: Prerequisites & Account Setup (Tasks 1-2)
2. **Phase 2**: Database Setup (Tasks 3-4)
3. **Phase 3**: Data Migration Scripts (Tasks 5-7)
4. **Phase 4**: Backend Migration (Tasks 8-17)
5. **Phase 5**: Frontend Migration (Tasks 18-21)
6. **Phase 6**: Testing & Validation (Tasks 22-24)

### Estimated Time

- Phase 1-2: 1 hour
- Phase 3: 1.5 hours
- Phase 4: 4 hours
- Phase 5: 1.5 hours
- Phase 6: 1 hour

**Total**: ~9 hours of focused work

### Execution Options

**Option 1: Subagent-Driven Development (Recommended)**
- Dispatch fresh subagent per task
- Review between tasks
- Fast iteration with built-in checkpoints
- Best for large multi-phase projects like this

**Option 2: Inline Execution**
- Execute tasks in this session
- Batch execution with manual checkpoints
- Good for linear, sequential work

Which approach would you like to use?

