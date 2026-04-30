.PHONY: run-backend run-frontend test-backend

run-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

run-frontend:
	cd frontend && NEXT_BACKEND_URL=http://localhost:8000 npm run dev

test-backend:
	cd backend && PYTHONPATH=. pytest -q
