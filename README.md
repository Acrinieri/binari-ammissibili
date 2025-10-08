# FastAPI + React Starter

Starter template for projects that pair a FastAPI backend with a React frontend.

## Stack

- **FastAPI** backend with SQLAlchemy ORM and SQLite for quick prototyping.
- **React** frontend bootstrapped with Create React App.
- CORS is pre-configured so the React dev server can call the API during development.

## Getting Started

1. **Clone the template**  
   ```bash
   git clone <your-new-repo-url> my-app
   cd my-app
   ```

2. **Backend**  
   ```bash
   python -m venv .venv
   .venv\Scripts\activate    # Windows
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
   The API runs on `http://127.0.0.1:8000`. A sample `/health` endpoint and order routes are included.

3. **Frontend**  
   ```bash
   cd frontend-react
   npm install
   npm start
   ```
   The React app runs on `http://localhost:3000` and communicates with the API.

## Project Structure

```
app/
  main.py          # FastAPI application setup + CORS
  routes/          # Example order routes
  database.py      # SQLAlchemy engine/session helpers
  models.py        # SQLAlchemy models
  schemas.py       # Pydantic schemas
frontend-react/
  src/             # React components (App.js consumes the API)
requirements.txt   # Python dependencies
```

## Adapting the Template

- Replace the example order models/routes with your own domain logic.
- Update `frontend-react/src/App.js` to reflect your UI needs.
- Adjust dependencies in `requirements.txt` and `frontend-react/package.json` as you grow.

## Creating a New Project from This Template

Once this repository is on GitHub, use the **Use this template** button (or clone it) to kick off future projects with the same structure.
