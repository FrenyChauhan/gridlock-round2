# Free Deployment on Render.com

## Backend
- New Web Service → connect GitHub repo
- Root directory: backend/
- Build: pip install -r requirements.txt
- Start: uvicorn main:app --host 0.0.0.0 --port $PORT
- Add env vars: ANTHROPIC_API_KEY, SECRET_KEY

## Frontend
- New Static Site → connect GitHub repo  
- Root directory: frontend/
- Build: npm install && npm run build
- Publish: dist/
- Add env var: VITE_API_URL=https://your-backend.onrender.com
