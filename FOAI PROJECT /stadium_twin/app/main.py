from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
import os
from .db import engine, Base
from .auth import router as auth_router, get_current_user
from .api_twin import router as twin_router
from .api_sim import router as sim_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FlowGuard")

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

# Serve HTML files with no-cache so browser always gets the latest version
@app.get("/static/{filename:path}")
async def serve_static(filename: str):
    filepath = os.path.join(static_dir, filename)
    if not os.path.exists(filepath):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".html", ".htm"):
        return FileResponse(
            filepath,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )
    return FileResponse(filepath)

app.include_router(auth_router)
app.include_router(twin_router)
app.include_router(sim_router)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    token = request.cookies.get("access_token")
    if token:
        return RedirectResponse(url="/static/dashboard.html")
    return RedirectResponse(url="/static/login.html")

@app.get("/api/me")
def get_me(current_user=Depends(get_current_user)):
    return {"username": current_user.username, "role": current_user.role}
