import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Contrato
from sqlalchemy import func

with app.app_context():
    regra = db.session.query(func.count(Contrato.id)).filter(Contrato.status == 'Cancelado por Regra').scalar()
    inad = db.session.query(func.count(Contrato.id)).filter(Contrato.status == 'Cancelado por Inadimplência').scalar()
    print(f"Cancelado por Regra: {regra}")
    print(f"Cancelado por Inadimplência: {inad}")
