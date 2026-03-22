import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    PORT = int(os.getenv("PORT", 8000))
    DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
config = Config()
