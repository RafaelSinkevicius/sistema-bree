
import sys
import os
from dotenv import load_dotenv
from sqlalchemy import text

# Carrega ambiente
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(basedir, ".env"))

sys.path.append(basedir)

from app import app, db

def update_delayed():
    with app.app_context():
        print("Atualizando contratos 'Em atraso' com > 60 dias...")
        
        sql = text("UPDATE contratos SET status = 'Cancelado por Inadimplência' WHERE status = 'Em atraso' AND dias_atraso > 60")
        result = db.session.execute(sql)
        db.session.commit()
        
        print(f"Contratos atualizados: {result.rowcount}")

if __name__ == "__main__":
    try:
        update_delayed()
    except Exception as e:
        print(f"Erro: {e}")
