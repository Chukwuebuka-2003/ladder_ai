import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database URL for NeonDB (PostgreSQL connection string)
DATABASE_URL = os.getenv('DATABASE_URL')


PRIVATE_KEY = os.getenv('PRIVATE_KEY')

PUBLIC_KEY = os.getenv('PUBLIC_KEY')

JWT_ALGORITHM = 'ES256'

# API Keys for Gemini and Groq
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GROQ_API_KEY   = os.getenv('GROQ_API_KEY')
