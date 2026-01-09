
import sys
import os
from dotenv import load_dotenv
from sqlalchemy import text

# Carrega ambiente
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(basedir, ".env"))

sys.path.append(basedir)

from app import app, db

def force_migrate():
    with app.app_context():
        print("Iniciando migração forçada via SQL...")
        
        sql = text("UPDATE contratos SET status = 'Cancelado por Inadimplência' WHERE status = 'Cliente Morto'")
        result = db.session.execute(sql)
        db.session.commit()
        
        print(f"Linhas afetadas: {result.rowcount}")
        print("Migração concluída.")

if __name__ == "__main__":
    try:
        force_migrate()
    except Exception as e:
        print(f"Erro: {e}")
