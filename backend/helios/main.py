from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import audit, fix, route, sessions, verify
from .db import init_db
from .errors import HeliosError, helios_error_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Helios", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(HeliosError, helios_error_handler)

app.include_router(sessions.router)
app.include_router(audit.router)
app.include_router(fix.router)
app.include_router(verify.router)
app.include_router(route.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
