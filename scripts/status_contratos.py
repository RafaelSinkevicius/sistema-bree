import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Contrato

with app.app_context():
    total_contratos = Contrato.query.count()
    ativos = Contrato.query.filter(Contrato.status.in_(["Em dia", "Pago"])).count()
    atrasados = Contrato.query.filter_by(status="Em atraso").count()
    cancelados_1 = Contrato.query.filter_by(status="Cancelado por Inadimplência").count()
    cancelados_2 = Contrato.query.filter_by(status="Cancelado por Regra").count()

    print("===== STATUS DOS CONTRATOS =====")
    print(f"Total de contratos: {total_contratos}")
    print(f"Ativos (Em dia ou Pago): {ativos}")
    print(f"Em atraso: {atrasados}")
    print(f"Cancelados 1 (Inadimplência): {cancelados_1}")
    print(f"Cancelados 2 (Regra): {cancelados_2}")