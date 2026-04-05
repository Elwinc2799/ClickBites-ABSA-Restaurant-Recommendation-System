"""
Upload business photos from frontend/public/business_photo/ to Supabase Storage.
Updates businesses.json with photo URLs after upload.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY')
BUCKET = 'business-photos'


def upload_photos() -> dict:
    """Upload all business photos to Supabase Storage"""
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    photo_dir = Path('frontend/public/business_photo')
    if not photo_dir.exists():
        print(f"Photo directory not found: {photo_dir}")
        print("Skipping photo upload.")
        return {}

    photo_urls = {}
    successful = 0
    failed = 0
    skipped = 0

    photos = list(photo_dir.glob('*.jpg'))
    print(f"Found {len(photos)} photos in {photo_dir}")

    for photo_path in sorted(photos):
        business_id = photo_path.stem

        try:
            with open(photo_path, 'rb') as f:
                file_data = f.read()

            # Try upload (skip if already exists)
            try:
                supabase.storage.from_(BUCKET).upload(
                    f'{business_id}.jpg',
                    file_data,
                    {'content-type': 'image/jpeg', 'upsert': 'false'}
                )
                successful += 1
            except Exception as e:
                if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                    skipped += 1
                else:
                    raise e

            # Get public URL
            public_url = supabase.storage.from_(BUCKET).get_public_url(f'{business_id}.jpg')
            photo_urls[business_id] = public_url

            if (successful + skipped) % 10 == 0:
                print(f"  Processed {successful + skipped}/{len(photos)} photos...")

        except Exception as e:
            print(f"  Failed {business_id}.jpg: {e}")
            failed += 1

    print(f"\nUpload complete!")
    print(f"  Uploaded: {successful}")
    print(f"  Skipped (already exists): {skipped}")
    print(f"  Failed: {failed}")

    # Save mapping
    output_path = Path('scripts/transformed_data/photo_urls.json')
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(photo_urls, f, indent=2)

    print(f"  URL mapping saved to {output_path}")
    return photo_urls


if __name__ == '__main__':
    upload_photos()
