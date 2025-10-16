lsof -ti:5173 | xargs kill -9 2>/dev/null || true && cd /Users/albou/projects/reverse-notebook/frontend/ && npm run dev
