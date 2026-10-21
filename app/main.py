from fastapi import FastAPI

app = FastAPI(
    title="Image Relevance & Auto-Tagging Engine",
    description="API for image understanding and semantic content matching.",
    version="0.1.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}
