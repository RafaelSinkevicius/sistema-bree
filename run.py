# Carrega variáveis de ambiente ANTES de qualquer importação da app
import sys
import os
from dotenv import load_dotenv

if getattr(sys, 'frozen', False):
    # Se estiver rodando como EXE (PyInstaller)
    base_path = os.path.dirname(sys.executable)
else:
    # Se estiver rodando como script normal
    base_path = os.path.dirname(os.path.abspath(__file__))

env_path = os.path.join(base_path, ".env")
load_dotenv(env_path)

from app import app

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
