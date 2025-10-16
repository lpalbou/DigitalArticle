lsof -ti:8000 | xargs kill -9 2>/dev/null || true && cd /Users/albou/projects/reverse-notebook/backend && python -m uvicorn app.main:app --reload --port 8000
