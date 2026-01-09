
import sys
import os
from dotenv import load_dotenv
from sqlalchemy import func

# Carrega ambiente
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(basedir, ".env"))

sys.path.append(basedir)

from app import app, db, Contrato

def audit_statuses():
    with app.app_context(), open("audit_result.txt", "w", encoding="utf-8") as f:
        # Busca totais
        total_registros = Contrato.query.count()
        
        # Agrupa por status e conta
        resultados = db.session.query(Contrato.status, func.count(Contrato.status)).group_by(Contrato.status).all()
        
        f.write("\n" + "="*50 + "\n")
        f.write(f"AUDITORIA DE STATUS (Total DB: {total_registros})\n")
        f.write("="*50 + "\n")
        
        display_sum = 0
        for status, count in resultados:
            f.write(f"Status: '{status}' | Qtd: {count}\n")
            display_sum += count
            
        f.write("-" * 50 + "\n")
        f.write(f"Soma dos grupos: {display_sum}\n")
        f.write(f"Diferença (Total - Soma): {total_registros - display_sum}\n")
        f.write("="*50 + "\n")

if __name__ == "__main__":
    audit_statuses()
