---
title: ClickBites API
emoji: 🍽️
colorFrom: orange
colorTo: red
sdk: docker
pinned: false
---

# ClickBites API

FastAPI backend for the ClickBites restaurant recommendation system using Aspect-Based Sentiment Analysis (ABSA).

## Endpoints

- `GET /health` - Health check
- `POST /api/signup` - User registration
- `POST /api/login` - User login
- `GET /api/results` - Search restaurants
- `GET /api/business/{id}` - Get business details
- `POST /api/business/{id}/review` - Submit review (triggers ABSA)
