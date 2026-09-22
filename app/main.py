from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="Voltage Chain Server",
    version="1.0.0",
    description="FastAPI ML inference server"
)

# include routes
app.include_router(router)


@app.get("/")
async def root():
    return {
        "message": "Server is running 🚀"
    }