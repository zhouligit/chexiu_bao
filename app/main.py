from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import get_settings
from app.core.exceptions import AppError
from app.core.response import error
from app.database import SessionLocal
from app.services.auth_service import SeedService

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    uploads = Path(settings.storage_local_path)
    uploads.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        SeedService.ensure_demo_data(db)
    except Exception:
        pass
    finally:
        db.close()

    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.mount("/uploads", StaticFiles(directory=settings.storage_local_path), name="uploads")


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(status_code=200, content=error(exc.code, exc.message))


@app.get("/health")
def health():
    return {"status": "ok"}
