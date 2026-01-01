from fastapi import FastAPI
from app.api.price import router as price_router

app = FastAPI(
    title="Price History Service",
    version="1.0.0"
)

app.include_router(price_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
