from fastapi import FastAPI

app = FastAPI()
_stats = {"processed": 0, "errors": 0}

@app.get("/")
def root():
    return {"service": "AI Scoring Server", "status": "running"}

@app.get("/api/v1/health")
def health():
    return {"status": "healthy"}

@app.get("/api/v1/stats")
def stats():
    return _stats
