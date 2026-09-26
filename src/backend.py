import os
from asyncio import to_thread
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from sqlmodel import Session
import uvicorn

from .models import create_db_and_tables, init_users, engine
from .routers import auth as auth, files as files, qa as qa

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await to_thread(create_db_and_tables)
    with Session(engine) as session:
        await to_thread(init_users, session)
    yield

app = FastAPI(title="PPCL code analysis API", version="0.3.1", lifespan=lifespan)

app.include_router(auth.router)
app.include_router(files.router)
app.include_router(qa.router)


@app.get("/")
async def root():
    return {
        "name": app.title,
        "status": "running",
        "health": "/health",
        "docs": "/docs",
        "frontend": "http://127.0.0.1:8501",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


def main() -> None:
    host = os.environ.get("API_HOST", "127.0.0.1")
    port = int(os.environ.get("API_PORT", "8000"))
    uvicorn.run("src.backend:app", host=host, port=port)


if __name__ == "__main__":
    main()
