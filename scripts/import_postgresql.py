"""
Import transformed data into PostgreSQL (Supabase).
Run after transform_data.py and upload_photos.py.
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
    print(f"Importing {len(businesses)} businesses...")
    inserted = 0
    errors = 0

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
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, $13)
                ON CONFLICT (business_id) DO NOTHING
            """,
                business['business_id'],
                business['name'],
                business.get('address'),
                business.get('city'),
                business.get('state'),
                business.get('postal_code'),
                business.get('latitude'),
                business.get('longitude'),
                business.get('stars'),
                business.get('review_count', 0),
                business.get('categories', []),
                json.dumps(business.get('aspect_scores', {})),
                photo_url
            )
            inserted += 1
            if inserted % 100 == 0:
                print(f"  {inserted} businesses inserted...")

        except Exception as e:
            print(f"  Error inserting business {business_id}: {e}")
            errors += 1

    print(f"  Done: {inserted} inserted, {errors} errors")


async def import_users(conn, users: list):
    print(f"Importing {len(users)} users...")
    inserted = 0
    errors = 0

    for user in users:
        try:
            pref_vector = user.get('preference_vector')
            pref_vector_str = None
            if pref_vector and isinstance(pref_vector, list) and len(pref_vector) == 5:
                pref_vector_str = f"[{','.join(str(float(v)) for v in pref_vector)}]"

            await conn.execute("""
                INSERT INTO users (user_id, name, email, password_hash, preference_vector)
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
                print(f"  {inserted} users inserted...")

        except Exception as e:
            print(f"  Error inserting user {user.get('user_id')}: {e}")
            errors += 1

    print(f"  Done: {inserted} inserted, {errors} errors")


async def import_reviews(conn, reviews: list):
    print(f"Importing {len(reviews)} reviews...")
    inserted = 0
    errors = 0

    for review in reviews:
        try:
            aspect_vector = review.get('aspect_vector', [0, 0, 0, 0, 0])
            vector_str = f"[{','.join(str(float(v)) for v in aspect_vector)}]"

            await conn.execute("""
                INSERT INTO reviews (review_id, business_id, user_id, text, stars, aspect_vector)
                VALUES ($1, $2, $3, $4, $5, $6::vector)
                ON CONFLICT (review_id) DO NOTHING
            """,
                review['review_id'],
                review['business_id'],
                review['user_id'],
                review['text'],
                review.get('stars'),
                vector_str
            )
            inserted += 1
            if inserted % 100 == 0:
                print(f"  {inserted} reviews inserted...")

        except Exception as e:
            print(f"  Error inserting review {review.get('review_id')}: {e}")
            errors += 1

    print(f"  Done: {inserted} inserted, {errors} errors")


async def verify_import(conn):
    print("\nVerifying import...")

    business_count = await conn.fetchval("SELECT COUNT(*) FROM businesses")
    user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
    review_count = await conn.fetchval("SELECT COUNT(*) FROM reviews")

    print(f"  Businesses: {business_count}")
    print(f"  Users:      {user_count}")
    print(f"  Reviews:    {review_count}")

    orphaned = await conn.fetchval("""
        SELECT COUNT(*) FROM reviews r
        LEFT JOIN businesses b ON r.business_id = b.business_id
        WHERE b.business_id IS NULL
    """)
    if orphaned > 0:
        print(f"  WARNING: {orphaned} orphaned reviews")
    else:
        print(f"  All reviews have valid business references")

    null_vectors = await conn.fetchval("SELECT COUNT(*) FROM reviews WHERE aspect_vector IS NULL")
    if null_vectors > 0:
        print(f"  WARNING: {null_vectors} reviews with NULL aspect_vector")
    else:
        print(f"  All reviews have aspect vectors")


async def main():
    data_dir = Path('scripts/transformed_data')

    if not data_dir.exists():
        print("ERROR: Run transform_data.py first")
        return

    print("Loading transformed data...")
    with open(data_dir / 'businesses.json') as f:
        businesses = json.load(f)
    with open(data_dir / 'users.json') as f:
        users = json.load(f)
    with open(data_dir / 'reviews.json') as f:
        reviews = json.load(f)

    photo_urls_path = data_dir / 'photo_urls.json'
    photo_urls = {}
    if photo_urls_path.exists():
        with open(photo_urls_path) as f:
            photo_urls = json.load(f)
    else:
        print("Note: photo_urls.json not found, skipping photo URLs")

    print(f"Connecting to PostgreSQL...")
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        await import_businesses(conn, businesses, photo_urls)
        await import_users(conn, users)
        await import_reviews(conn, reviews)
        await verify_import(conn)
        print("\nImport complete!")
    finally:
        await conn.close()


if __name__ == '__main__':
    asyncio.run(main())
