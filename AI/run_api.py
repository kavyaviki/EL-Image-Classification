# El-image-ai/run_api.py
# uvicorn entrypoint for API
import uvicorn
from fastapi import FastAPI
from app.routes.el_image import router

app = FastAPI(title="EL Image AI Classifier", version="1.0")
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("run_api:app", host="0.0.0.0", port=8001, reload=True)