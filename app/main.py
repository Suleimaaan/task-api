from fastapi import FastAPI

from app.routers import projects, tasks, users

app = FastAPI(title="Task Manager API", version="1.0.0")

app.include_router(users.router)
app.include_router(projects.router)
app.include_router(tasks.router)


@app.get("/health", tags=["service"])
def health():
    return {"status": "ok"}
