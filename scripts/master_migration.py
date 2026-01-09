
import sys
import os
from dotenv import load_dotenv
from sqlalchemy import text

# ==============================================================================
# SCRIPT DE MIGRAÇÃO MESTRE - SISTEMA BREE
# ==============================================================================
# Este script consolida todas as correções de banco de dados necessárias para
# atualizar um ambiente legado (com "Cliente Morto") para a nova versão (V3).
#
# O QUE ELE FAZ:
# 1. Migra 'Cliente Morto' -> 'Cancelado por Inadimplência'.
# 2. Corrige contratos com status 'Erro ao consultar'.
# 3. Enforça a regra: 'Em atraso' > 60 dias -> 'Cancelado por Inadimplência'.
# ==============================================================================

# 1. Carrega ambiente e setup
# 1. Carrega ambiente e setup
if getattr(sys, 'frozen', False):
    basedir = os.path.dirname(sys.executable)
else:
    basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(os.path.join(basedir, ".env"))
sys.path.append(basedir)

from app import app, db
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_master_migration():
    with app.app_context():
        logging.info("INICIANDO MIGRAÇÃO MESTRE DO SISTEMA BREE...")
        
        # ---------------------------------------------------------
        # PASSO 1: Migrar 'Cliente Morto'
        # ---------------------------------------------------------
        logging.info(">>> PASSO 1: Migrando 'Cliente Morto'...")
        sql_mortos = text("UPDATE contratos SET status = 'Cancelado por Inadimplência' WHERE status = 'Cliente Morto'")
        res_mortos = db.session.execute(sql_mortos)
        logging.info(f"   LINHAS AFETADAS: {res_mortos.rowcount}")

        # ---------------------------------------------------------
        # PASSO 2: Resolver 'Erro ao consultar'
        # ---------------------------------------------------------
        logging.info(">>> PASSO 2: Resolvendo status 'Erro ao consultar'...")
        # 2a. Se tiver > 60 dias, é Cancelado
        sql_erro_canc = text("UPDATE contratos SET status = 'Cancelado por Inadimplência' WHERE status = 'Erro ao consultar' AND dias_atraso > 60")
        res_erro_canc = db.session.execute(sql_erro_canc)
        logging.info(f"   ERROS -> CANCELADOS (>60d): {res_erro_canc.rowcount}")
        
        # 2b. O resto vira 'Em atraso' para reprocessamento
        sql_erro_reset = text("UPDATE contratos SET status = 'Em atraso' WHERE status = 'Erro ao consultar'")
        res_erro_reset = db.session.execute(sql_erro_reset)
        logging.info(f"   ERROS -> EM ATRASO (Reset): {res_erro_reset.rowcount}")

        # ---------------------------------------------------------
        # PASSO 3: Enforce Regra de 60 Dias
        # ---------------------------------------------------------
        logging.info(">>> PASSO 3: Aplicando regra de corte (>60 dias) em atrasados antigos...")
        sql_regra = text("UPDATE contratos SET status = 'Cancelado por Inadimplência' WHERE status = 'Em atraso' AND dias_atraso > 60")
        res_regra = db.session.execute(sql_regra)
        logging.info(f"   ATRASADOS ANCIÕES -> CANCELADOS: {res_regra.rowcount}")

        # ---------------------------------------------------------
        # COMMIT FINAL
        # ---------------------------------------------------------
        db.session.commit()
        logging.info("="*60)
        logging.info("MIGRAÇÃO CONCLUÍDA COM SUCESSO.")
        logging.info("O sistema agora está limpo e atualizado.")
        logging.info("="*60)

if __name__ == "__main__":
    try:
        run_master_migration()
    except Exception as e:
        logging.error(f"FALHA FATAL NA MIGRAÇÃO: {e}")
