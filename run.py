import uvicorn

# to activate env
# venv\Scripts\activate 

# to start the server
# uvicorn app.main:app --reload

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )