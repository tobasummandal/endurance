from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import audit, demo, fix, live, route, sessions, verify
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

API_PREFIX = "/api"
app.include_router(sessions.router, prefix=API_PREFIX)
app.include_router(audit.router, prefix=API_PREFIX)
app.include_router(fix.router, prefix=API_PREFIX)
app.include_router(verify.router, prefix=API_PREFIX)
app.include_router(route.router, prefix=API_PREFIX)
app.include_router(live.router, prefix=API_PREFIX)
app.include_router(demo.router, prefix=API_PREFIX)


@app.get("/health")
def health() -> dict:
    return {"ok": True}


# Static frontend — must be mounted LAST so /api/* and /health win route precedence.
# Layout:
#   /web/index.html  → marketing landing (current handcrafted page) served at "/"
#   /web/out/        → Next.js reviewer app (basePath="/app") served at "/app"
WEB_DIR = Path(__file__).resolve().parent.parent.parent / "web"
NEXT_OUT = WEB_DIR / "out"
if NEXT_OUT.is_dir():
    app.mount("/app", StaticFiles(directory=NEXT_OUT, html=True), name="reviewer")
if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
