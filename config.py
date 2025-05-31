import os
from dotenv import load_dotenv

load_dotenv()  # Carga las variables del archivo .env

TRELLO_API_KEY = os.getenv('TRELLO_API_KEY')
TRELLO_API_TOKEN = os.getenv('TRELLO_API_TOKEN')