import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import init_db
from app.routes import auth, chat, cv, learning

init_db()

app = FastAPI(title="AI Smart Career Analyzer API")
log = logging.getLogger("uvicorn.error")


# Added BEFORE CORS so CORS stays the outermost layer: an unexpected crash then still
# returns JSON with CORS headers. Without this the browser hides the real error and the
# frontend only shows "Cannot reach the server".
@app.middleware("http")
async def catch_unexpected_errors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception:
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500,
                            content={"detail": "Server error. Check the backend terminal for details."})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "AI Smart Career Analyzer is running!"}


app.include_router(auth.router)
app.include_router(cv.router)
app.include_router(learning.router)
app.include_router(chat.router)
