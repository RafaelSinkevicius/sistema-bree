import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from app import app, db, Contrato, Vendedor
from datetime import datetime
from sqlalchemy.exc import IntegrityError

# Lê a planilha Excel
df = pd.read_excel('planilha.xlsx')

with app.app_context():
    for index, row in df.iterrows():
        try:
            # Processa o vendedor
            nome_vendedor = row['VENDEDOR'].strip()
            vendedor = Vendedor.query.filter_by(nome=nome_vendedor).first()
            if not vendedor:
                vendedor = Vendedor(nome=nome_vendedor, cpf_cnpj='00000000000', celular='', email='')
                db.session.add(vendedor)
                db.session.commit()

            # Trata o campo de Mês de Cancelamento
            mes_cancelamento = pd.to_datetime(row['Mês de Cancelamento (se aplicável)'], errors='coerce')
            mes_cancelamento = None if pd.isna(mes_cancelamento) else mes_cancelamento

            # Cria o contrato
            contrato = Contrato(
                proposta=row['PROPOSTA'],
                data_checagem=pd.to_datetime(row['DATA DE CHECAGEM'], errors='coerce'),
                razao_social=row['RAZÃO SOCIAL/NOME'],
                cnpj_cpf=row['CNPJ/CPF'],
                celular=row['CELULAR'],
                email=row['E-MAIL'],
                atividade_economica=row['ATIVIDADE ECONÔMICA'],
                cidade=row['CIDADE'],
                nome_plano=row['NOME DO PLANO'],
                data_vigencia=pd.to_datetime(row['DATA DE VIGÊNCIA'], errors='coerce'),
                vidas=int(row['VIDAS']) if pd.notna(row['VIDAS']) else None,
                valor_parcela=float(row['VALOR DA PARCELA']) if pd.notna(row['VALOR DA PARCELA']) else None,
                parcela_atual=int(row['PARCELA ATUAL']) if pd.notna(row['PARCELA ATUAL']) else None,
                status=row['STATUS'],
                mes_cancelamento=mes_cancelamento,
                verificado=(row['VERIFICADO?'].strip().lower() == 'sim') if pd.notna(row['VERIFICADO?']) else False,
                contrato=row['CONTRATO'],
                vendedor_id=vendedor.id
            )
            db.session.add(contrato)
            db.session.commit()
            print(f"Contrato {row['CONTRATO']} importado com sucesso!")
        except IntegrityError as ie:
            db.session.rollback()
            print(f"Contrato {row['CONTRATO']} já existe. Pulado.")
        except Exception as e:
            db.session.rollback()
            print(f"Erro ao importar contrato {row['CONTRATO']}: {e}")

print("Processo de importação concluído!")

