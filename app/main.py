from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.price import router as price_router

app = FastAPI(
    title="Price History Service",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(price_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
