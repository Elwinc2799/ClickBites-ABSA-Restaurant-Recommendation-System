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
CREATE INDEX idx_preference_vector ON users USING ivfflat (preference_vector vector_cosine_ops) WITH (lists = 100);

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
CREATE INDEX idx_aspect_vector ON reviews USING ivfflat (aspect_vector vector_cosine_ops) WITH (lists = 100);
