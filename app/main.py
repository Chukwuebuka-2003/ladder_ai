from fastapi import FastAPI
from sqlalchemy.orm import Session
import logging
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from routers import auth, expenses, ai, chat, budget, trends

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
    "http://localhost:8501",
    "https://ladderai.streamlit.app",
    "http://127.0.0.1:8001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers with correct prefixes
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(expenses.router, prefix="/expenses", tags=["Expenses"])
app.include_router(ai.router, prefix="/ai", tags=["AI"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
app.include_router(budget.router, prefix="/budgets", tags=["Budgets"])
app.include_router(trends.router, prefix="/trends", tags=["Trends"])


# root endpoint for basic check
@app.get("/")
async def read_root():
    return {"message": "Welcome to the AI-Powered Expense Tracker API"}
