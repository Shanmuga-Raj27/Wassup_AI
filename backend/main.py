import uvicorn
from fastapi import FastAPI

app = FastAPI(
    title="Web Agent API",
    description="Backend API for Web Agent",
    version="0.1.0",
)


@app.get("/")
def root():
    return {"message": "Web Agent Backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
  