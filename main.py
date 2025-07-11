"""
Main server file for the Document Analysis Agent
"""
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

# Import the existing app from ai_agents
from backend.api.ai_agents import app

# Serve static files for frontend
frontend_dir = Path(__file__).parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

# Serve frontend for any unmatched routes (SPA support)
@app.get("/{path:path}")
async def serve_frontend(path: str):
    """Serve frontend files for single-page application"""
    frontend_path = Path(__file__).parent / "frontend"
    
    # Check if file exists
    file_path = frontend_path / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(file_path)
    
    # Return index.html for SPA routes
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    
    # Return 404 if no frontend
    return {"error": "Frontend not found"}

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
