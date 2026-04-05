"""
Transform MongoDB JSON data to PostgreSQL-compatible format.
Reads data/business.json, data/review.json, data/user.json
Outputs transformed data ready for PostgreSQL import.
"""
import json
from pathlib import Path
from typing import Dict, Any


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
    categories = doc.get('categories', [])
    if isinstance(categories, str):
        categories = [c.strip() for c in categories.split(',') if c.strip()]

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
        'categories': categories,
        'aspect_scores': doc.get('aspect_scores', {}),
        'photo_url': None  # Set after photo upload
    }


def transform_user(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Transform user document from MongoDB to PostgreSQL format"""
    return {
        'user_id': doc.get('user_id'),
        'name': doc.get('name'),
        'email': doc.get('email'),
        'password_hash': doc.get('password'),  # Already hashed
        'preference_vector': doc.get('preference_vector')
    }


def transform_review(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Transform review document from MongoDB to PostgreSQL format"""
    aspect_vector = doc.get('aspect_vector', [0, 0, 0, 0, 0])

    if not isinstance(aspect_vector, list) or len(aspect_vector) != 5:
        aspect_vector = [0.0, 0.0, 0.0, 0.0, 0.0]

    return {
        'review_id': doc.get('review_id'),
        'business_id': doc.get('business_id'),
        'user_id': doc.get('user_id'),
        'text': doc.get('text'),
        'stars': doc.get('stars'),
        'aspect_vector': [float(v) for v in aspect_vector]
    }


def main():
    print("Loading JSON data...")
    businesses, reviews, users = load_json_data()

    print(f"Loaded {len(businesses)} businesses")
    print(f"Loaded {len(reviews)} reviews")
    print(f"Loaded {len(users)} users")

    print("\nTransforming data...")
    transformed_businesses = [transform_business(b) for b in businesses]
    transformed_users = [transform_user(u) for u in users]
    transformed_reviews = [transform_review(r) for r in reviews]

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
    print(f"  businesses.json: {len(transformed_businesses)} records")
    print(f"  users.json:      {len(transformed_users)} records")
    print(f"  reviews.json:    {len(transformed_reviews)} records")


if __name__ == '__main__':
    main()
