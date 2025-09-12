from fastapi import FastAPI
from sqlalchemy.orm import Session
import logging
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware # Import CORSMiddleware

# Import routers
from routers import auth, expenses, ai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    yield
    logger.info("Application shutting down...")

# Initialize FastAPI
app = FastAPI(
    lifespan=lifespan,
    title="AI-Powered Expense Tracker API",
    description="This API provides core expense tracking functionalities augmented with AI-driven insights and categorization using Gemini and Groq.",
    version="1.0.0",
    contact={
        "name": "Chukwuebuka Ezeokeke",
        "url": "https://github.com/Chukwuebuka-2003",
        "email": "ebulamicheal@gmail.com",
    }
)

# CORS Configuration
origins = [
    "http://localhost:8501",  # For Streamlit development server
    # Add any other origins here, e.g., "https://your-frontend-domain.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,           # List of origins allowed to connect
    allow_credentials=True,        # Allow cookies to be sent with requests
    allow_methods=["*"],           # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],           # Allow all headers
)


# Include routers
app.include_router(auth.router)
app.include_router(expenses.router)
app.include_router(ai.router)

# root endpoint for basic check
@app.get("/")
async def read_root():
    return {"message": "Welcome to the AI-Powered Expense Tracker API"}
