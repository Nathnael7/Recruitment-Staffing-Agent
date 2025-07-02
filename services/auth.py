import os
from dotenv import load_dotenv
import google.generativeai as genai
from google.oauth2.service_account import Credentials
from config.settings import CREDENTIALS_FILE, SCOPES

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

def get_google_credentials():
    return Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=SCOPES
    )
