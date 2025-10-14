from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, SessionLocal, engine
from .data_loader import ensure_tracks_seeded
from .routes.admin_auth import router as admin_auth_router
from .routes.admin_config import router as admin_config_router
from .routes.admin_tracks import router as admin_tracks_router
from .routes.tracks import router as tracks_router
from .security import require_admin_token

app = FastAPI(title="Binari Ammissibili API")


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        ensure_tracks_seeded(session)

# Allow the React dev server to talk to the API during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://rfi.b4service.it",
        "https://api.rfi.b4service.it",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(tracks_router)
app.include_router(admin_auth_router)
admin_dependencies = [Depends(require_admin_token)]
app.include_router(admin_tracks_router, dependencies=admin_dependencies)
app.include_router(admin_config_router, dependencies=admin_dependencies)

