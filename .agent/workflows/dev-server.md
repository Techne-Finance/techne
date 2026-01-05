---
description: Run Techne Finance locally for development
---

# Start Techne Finance Dev Server

// turbo-all

## Backend (FastAPI):
```bash
cd C:\Users\Dell\.gemini\antigravity\scratch\techne-finance\backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Frontend (Static server):
```bash
cd C:\Users\Dell\.gemini\antigravity\scratch\techne-finance\frontend
python -m http.server 8080
```

## Access:
- Frontend: http://localhost:8080
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
