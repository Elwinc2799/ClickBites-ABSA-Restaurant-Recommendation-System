#!/usr/bin/env python3
"""
Import sample data from data/ folder directly into Supabase via REST API.

Requirements:
    pip install requests bcrypt

Run from repo root:
    python scripts/import_supabase.py
"""
import json
import sys
import time
import requests
import bcrypt
from pathlib import Path

# ── Credentials ───────────────────────────────────────────────────────────────
SUPABASE_URL = "https://ogiacbcmiboycerigvsd.supabase.co"
SUPABASE_SERVICE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9naWFjYmNtaWJveWNlcmlndnNkIiwicm9sZSI"
    "6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTM3MzU0MCwiZXhwIjoyMDkwOTQ5NTQwfQ"
    ".pqAeXlg7TgL8hupvEqFe9cQyl0wZXGz9ehqIuzjVv0c"
)

DATA_DIR = Path(__file__).parent.parent / "data"
BATCH_SIZE = 200
REST_BASE = f"{SUPABASE_URL}/rest/v1"
HEADERS = {
    "apikey": SUPABASE_SERVICE_KEY,
    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=minimal",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_jsonl(filepath: Path) -> list:
    records = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def vector_to_str(v) -> str:
    if not v:
        v = [0.0] * 5
    return f"[{','.join(str(float(x)) for x in v)}]"


def hash_pw(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def post_batch(table: str, records: list) -> tuple[int, int]:
    """POST a batch with merge-duplicates. Returns (ok_count, error_count)."""
    url = f"{REST_BASE}/{table}"
    r = requests.post(url, headers=HEADERS, json=records, timeout=30)
    if r.status_code in (200, 201):
        return len(records), 0
    # 409 = conflict handled by Prefer header on success; anything else is an error
    print(f"\n  HTTP {r.status_code}: {r.text[:200]}", file=sys.stderr)
    return 0, len(records)


def batch_import(table: str, records: list):
    total = len(records)
    ok = 0
    err = 0
    for i in range(0, total, BATCH_SIZE):
        chunk = records[i:i + BATCH_SIZE]
        n_ok, n_err = post_batch(table, chunk)
        ok += n_ok
        err += n_err
        print(f"  {min(ok + err, total)}/{total}", end="\r")
    print(f"  {ok}/{total} imported, {err} errors")


# ── Transform functions ───────────────────────────────────────────────────────

def transform_business(raw: dict) -> dict:
    cats = raw.get("categories", "")
    categories = [c.strip() for c in cats.split(",") if c.strip()] if isinstance(cats, str) else (cats or [])
    v = raw.get("vector") or [0, 0, 0, 0, 0]
    return {
        "business_id": raw["business_id"],
        "name": raw.get("name"),
        "address": raw.get("address"),
        "city": raw.get("city"),
        "state": raw.get("state"),
        "postal_code": raw.get("postal_code"),
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
        "stars": raw.get("stars"),
        "review_count": raw.get("review_count", 0),
        "categories": categories,
        "aspect_scores": {"food": float(v[0]), "service": float(v[1]),
                          "price": float(v[2]), "ambience": float(v[3]), "misc": float(v[4])},
        "photo_url": None,
    }


def transform_user(raw: dict) -> dict:
    password = raw.get("password", "Password123!")
    v = raw.get("vector") or [0.333] * 5
    return {
        "user_id": raw["user_id"],
        "name": raw.get("name"),
        "email": raw.get("email"),
        "password_hash": hash_pw(password),
        "preference_vector": vector_to_str(v),
        "has_business_id": None,
    }


def transform_review(raw: dict) -> dict:
    v = raw.get("vector") or [0, 0, 0, 0, 0]
    created_at = raw.get("date") or raw.get("created_at")
    record = {
        "review_id": raw["review_id"],
        "business_id": raw["business_id"],
        "user_id": raw["user_id"],
        "text": raw.get("text"),
        "stars": raw.get("stars"),
        "aspect_vector": vector_to_str(v),
    }
    if created_at:
        record["created_at"] = created_at.replace(" ", "T") if " " in str(created_at) else created_at
    return record


# ── Main ──────────────────────────────────────────────────────────────────────

def row_count(table: str) -> int:
    r = requests.get(f"{REST_BASE}/{table}?select=*", headers={
        **HEADERS, "Prefer": "count=exact", "Range": "0-0"
    }, timeout=10)
    cr = r.headers.get("Content-Range", "")
    return int(cr.split("/")[-1]) if "/" in cr else 0


def main():
    print("Connecting to Supabase REST API...")
    try:
        requests.get(f"{REST_BASE}/businesses?limit=1", headers=HEADERS, timeout=10).raise_for_status()
    except Exception as e:
        print(f"ERROR: Cannot connect: {e}")
        sys.exit(1)

    # ── Businesses ────────────────────────────────────────────────────────────
    existing = row_count("businesses")
    print(f"\nBusinesses in DB: {existing}")
    if existing == 0:
        raw = load_jsonl(DATA_DIR / "business.json")
        businesses = [transform_business(b) for b in raw]
        print(f"Importing {len(businesses)} businesses...")
        batch_import("businesses", businesses)
    else:
        print(f"  Skipping (already imported)")
        businesses = load_jsonl(DATA_DIR / "business.json")

    # ── Users ─────────────────────────────────────────────────────────────────
    existing = row_count("users")
    print(f"\nUsers in DB: {existing}")
    if existing == 0:
        raw_users = load_jsonl(DATA_DIR / "user.json")
        print(f"Hashing {len(raw_users)} passwords (this takes ~30s)...")
        users = [transform_user(u) for u in raw_users]
        print(f"Importing {len(users)} users...")
        batch_import("users", users)
    else:
        print(f"  Skipping (already imported)")
        raw_users = load_jsonl(DATA_DIR / "user.json")
        users = raw_users

    # ── Reviews ───────────────────────────────────────────────────────────────
    existing = row_count("reviews")
    print(f"\nReviews in DB: {existing}")
    if existing == 0:
        biz_ids = {b["business_id"] for b in (businesses if isinstance(businesses[0], dict) and "business_id" in businesses[0] else [])}
        user_ids = {u.get("user_id") or u["user_id"] for u in users}
        raw_reviews = load_jsonl(DATA_DIR / "review.json")
        reviews = [transform_review(r) for r in raw_reviews
                   if r["business_id"] in biz_ids and r["user_id"] in user_ids]
        skipped = len(raw_reviews) - len(reviews)
        if skipped:
            print(f"  Skipping {skipped} reviews with missing references")
        print(f"Importing {len(reviews)} reviews...")
        batch_import("reviews", reviews)
    else:
        print(f"  Skipping (already imported)")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n── Final counts ──")
    for table in ["businesses", "users", "reviews"]:
        print(f"  {table}: {row_count(table)}")

    print("\nImport complete!")
    print("Frontend: https://frontend-eight-mu-58.vercel.app")
    print("API:      https://elwinc2799-clickbites-api.hf.space")


if __name__ == "__main__":
    main()
