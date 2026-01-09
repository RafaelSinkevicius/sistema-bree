"""
================================================================================
AUTOMAÇÃO BREE - SISTEMA DE VERIFICAÇÃO DE CONTRATOS AMIL
================================================================================
Versão: 3.0 - Blindada e Resiliente
Data: 2026-01-06

DESCRIÇÃO:
Sistema automatizado para verificação de status de contratos no portal Amil,
com lógica inteligente de checagem baseada em D+3, tratamento de contratos
cancelados, mortos, em atraso e proteções contra falhas de rede.

REGRAS DE NEGÓCIO:
1. STATUS DOS CONTRATOS:
   - Cancelado por Inadimplência: fatura com "multa por rescisão contratual"
   - Cancelado por Regra: cancelamento por outras regras do sistema
   - Cliente Morto: 63+ dias em atraso sem multa contratual
   - Em atraso: fatura vencida sem pagamento
   - Pago: D+3 passou, verificado, mensalidade do mês vigente paga
   - Em dia: ainda não atingiu D+3

2. PRIORIDADE DE CHECAGEM:
   - Contratos em atraso: checados diariamente
   - Contratos em dia/pagos: checados após D+3
   - Contratos cancelados: checados a cada 15 dias (Tentativa de recuperação)
   - Clientes mortos: checados a cada 15 dias

3. Proteções:
   - Retry infinito em caso de queda de internet
   - Watchdog baseado em heartbeat (não mata processo longo se estiver fluindo)
   - Recuperação de sessão automática
================================================================================
"""

import sys
import os

# Adiciona o diretório pai (raiz do projeto) ao path para importar 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Contrato, AcaoCobranca

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from datetime import datetime, date, timedelta, timezone
import time
import logging
import threading
import pytz
import threading
import pytz
import re
import socket
from logging.handlers import TimedRotatingFileHandler
from selenium.common.exceptions import InvalidSessionIdException

# ============================================================================
# CONFIGURAÇÕES GLOBAIS
# ============================================================================

from dotenv import load_dotenv

# Carrega ambiente com suporte a PyInstaller
if getattr(sys, 'frozen', False):
    basedir = os.path.dirname(sys.executable)
else:
    basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(os.path.join(basedir, ".env"))

fuso_brasilia = timezone(timedelta(hours=-3))
AMIL_USER = os.getenv("AMIL_USER")
AMIL_PASSWORD = os.getenv("AMIL_PASSWORD")
# DIAS_VERIFICACAO_MORTOS = 15
DIAS_D3 = 3
INTERVALO_EXECUCAO = 300  # 5 minutos

# ============================================================================
# CONFIGURAÇÃO DE LOGGING
# ============================================================================

log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

log_filename = os.path.join(
    log_dir, 
    f"log_{datetime.now(fuso_brasilia).strftime('%Y-%m-%d_%H-%M-%S')}.log"
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Remove handlers existentes para evitar duplicação
logger.handlers.clear()

# Configuração com Rotação Diária (Midnight)
file_handler = TimedRotatingFileHandler(
    log_filename, 
    when="midnight", 
    interval=1, 
    backupCount=30,  # Mantém 30 dias de logs
    encoding='utf-8'
)
file_handler.suffix = "%Y-%m-%d.log"  # Formato do arquivo rotacionado
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

def log_debug(msg):
    """Wrapper para logs de debug detalhados"""
    logger.info(f"[DEBUG] {msg}")  # Usando INFO para aparecer no console por enquanto

def log_trace(msg):
    """Wrapper para logs de rastreamento extremo"""
    # logger.debug(f"[TRACE] {msg}") 
    pass

# ============================================================================
# FUNÇÕES AUXILIARES
# ============================================================================

def parse_date(date_str):
    """Converte string de data no formato DD/MM/YYYY para objeto date."""
    try:
        if not date_str or not date_str.strip():
            return None
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
    except Exception as e:
        # log_debug(f"Falha ao parsear data '{date_str}': {e}")
        return None


def parse_float(valor_str):
    """Converte string de valor brasileiro (R$ 1.234,56) para float."""
    try:
        cleaned = re.sub(r"[^\d,\.]", "", valor_str)
        
        if cleaned.count(",") == 1 and cleaned.count(".") == 0:
            cleaned = cleaned.replace(",", ".")
        elif cleaned.count(",") > 1 and cleaned.count(".") == 0:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        
        return float(cleaned)
    except:
        return 0.0


def calcular_data_d3(data_vigencia: date, hoje: date):
    """
    Calcula a data de D+3 (3 dias após o vencimento do mês corrente).
    """
    if not data_vigencia:
        return hoje, False

    dia_vencimento = data_vigencia.day
    
    # Calcula vencimento do mês atual
    try:
        vencimento_mes_atual = data_vigencia.replace(
            year=hoje.year, 
            month=hoje.month
        )
    except ValueError:
        # Trata casos onde o dia não existe no mês atual
        if hoje.month == 2:
            try:
                vencimento_mes_atual = date(hoje.year, 2, 29)
            except ValueError:
                vencimento_mes_atual = date(hoje.year, 2, 28)
        elif hoje.month in [4, 6, 9, 11] and dia_vencimento == 31:
            vencimento_mes_atual = date(hoje.year, hoje.month, 30)
        else:
            vencimento_mes_atual = date(hoje.year, hoje.month, dia_vencimento)

    data_d3_atual = vencimento_mes_atual + timedelta(days=DIAS_D3)
    # log_debug(f"Calculando D+3. Vigência: {data_vigencia}, Hoje: {hoje}. Vencimento Mês Atual: {vencimento_mes_atual}, D+3 Atual: {data_d3_atual}")
    
    # CORREÇÃO CRÍTICA: Para vigências de fim de mês (28-31)
    if dia_vencimento >= 28:
        # Calcula mês anterior
        if hoje.month == 1:
            mes_anterior = 12
            ano_anterior = hoje.year - 1
        else:
            mes_anterior = hoje.month - 1
            ano_anterior = hoje.year
        
        # Calcula vencimento do mês anterior
        try:
            vencimento_mes_anterior = date(ano_anterior, mes_anterior, dia_vencimento)
        except ValueError:
            if mes_anterior == 2:
                try:
                    vencimento_mes_anterior = date(ano_anterior, 2, 29)
                except ValueError:
                    vencimento_mes_anterior = date(ano_anterior, 2, 28)
            elif mes_anterior in [4, 6, 9, 11] and dia_vencimento == 31:
                vencimento_mes_anterior = date(ano_anterior, mes_anterior, 30)
            else:
                vencimento_mes_anterior = date(ano_anterior, mes_anterior, dia_vencimento)
        
        data_d3_anterior = vencimento_mes_anterior + timedelta(days=DIAS_D3)
        
        if data_d3_anterior.month == hoje.month:
            pode_checar = hoje >= data_d3_anterior
            return data_d3_anterior, pode_checar
    
    if data_d3_atual.month != hoje.month:
        dias_desde_vencimento = (hoje - vencimento_mes_atual).days
        pode_checar = dias_desde_vencimento >= DIAS_D3
    else:
        pode_checar = hoje >= data_d3_atual
    
    return data_d3_atual, pode_checar


def determinar_status_faturas(invoices, data_ref, data_vigencia=None, ja_passou_d3=False):
    """Determina o status do contrato baseado nas faturas."""
    # Verifica multa por rescisão contratual
    for inv in invoices:
        ciclo = inv.get("ciclo", "").lower()
        if "multa por rescisão contratual" in ciclo:
            log_debug(f"Multa rescisória encontrada na fatura ref {inv.get('referencia')}")
            return "Cancelado por Inadimplência"
    
    # Verifica faturas vencidas não pagas
    for inv in invoices:
        vencimento = inv.get("vencimento")
        pagamento = inv.get("pagamento")
        if (vencimento and 
            vencimento <= data_ref and 
            (not pagamento or str(pagamento).strip() == "")):
            log_debug(f"Fatura em atraso encontrada: Ref {inv.get('referencia')}, Venc {vencimento}, Valor {inv.get('valor')}")
            return "Em atraso"
    
    # Se já passou D+3, verifica se mensalidade do mês vigente está paga
    if ja_passou_d3 and data_vigencia:
        mes_ref = data_ref.month
        ano_ref = data_ref.year
        
        for inv in invoices:
            referencia = inv.get("referencia", "")
            if referencia:
                try:
                    partes = referencia.split("/")
                    if len(partes) >= 2:
                        mes_fatura = int(partes[0])
                        ano_fatura = int(partes[1])
                        
                        if mes_fatura == mes_ref and ano_fatura == ano_ref:
                            if inv.get("pagamento") and str(inv.get("pagamento", "")).strip():
                                log_debug(f"Pagamento do mês vigente ({mes_ref}/{ano_ref}) confirmado.")
                                return "Pago"
                except:
                    pass
    
    return "Em dia"


def watchdog_timeout():
    """DEPRECATED: Função antiga de watchdog."""
    pass


# ============================================================================
# CLASSE PRINCIPAL DE AUTOMAÇÃO
# ============================================================================

class AutomacaoBree:
    """
    Classe principal para automação de verificação de contratos.
    
    Gerencia:
    - Login e navegação no portal Amil
    - Consulta de faturas e Atualização de status
    - Resiliência de Rede e Watchdog inteligente
    """
    
    def __init__(self):
        """Inicializa o driver Selenium e configurações."""
        self.driver = None
        self.wait = None
        self.sisamil_handle = None
        
        # Variáveis de controle de execução
        self.last_activity = time.time()
        self.running = True
        self.watchdog_thread = None
        
        logging.info("Automação Bree inicializada com proteções ativas.")

    def _init_driver(self):
        """Inicializa ou reinicializa o driver do Chrome."""
        try:
            # Se tiver driver antigo ou com sessao invalida, mata ele
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            self.driver = None  # Garante limpeza da referencia

            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), 
                options=chrome_options
            )
            self.wait = WebDriverWait(self.driver, 30)
            logging.info("Driver Chrome inicializado com sucesso.")
            
        except Exception as e:
            logging.error(f"Erro ao inicializar driver: {e}")
            raise

    # ========================================================================
    # UTILITÁRIOS DE REDE E WATCHDOG
    # ========================================================================

    def check_internet_connection(self):
        """Verifica conexão com Google DNS."""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            log_debug("Falha na conexão com 8.8.8.8 (Google DNS)")
            return False

    def update_heartbeat(self):
        """Atualiza o sinal de vida do bot."""
        self.last_activity = time.time()

    def watchdog_monitor(self):
        """Monitora se o bot travou (sem heartbeat por 5 min)."""
        TIMEOUT_SEGURANCA = 300  # 5 minutos sem processar nada
        
        while self.running:
            time.sleep(10)
            elapsed = time.time() - self.last_activity
            
            if elapsed > TIMEOUT_SEGURANCA:
                logging.error(f"[WATCHDOG] Processo travado por {elapsed:.0f}s. Reiniciando forçadamente...")
                os._exit(1)  # Mata o processo brutalmente para o Windows reiniciar

    def aguardar_internet(self):
        """Loop de espera por conexão."""
        if self.check_internet_connection():
            return
            
        logging.warning("Sem conexão com a internet. Entrando em modo de espera...")
        while not self.check_internet_connection():
            time.sleep(60)
            logging.info("Aguardando retorno da internet...")
        
        logging.info("Conexão restabelecida!")
        time.sleep(5)

    # ========================================================================
    # NAVEGAÇÃO E LOGIN
    # ========================================================================
    
    def login_e_navegar_sisamil(self):
        """
        Realiza login com retry infinito.
        """
        tentativa = 0
        backoff = 60
        
        while True:
            try:
                self.aguardar_internet()
                self._init_driver()
                
                logging.info(f"Iniciando tentativa de login #{tentativa + 1}...")
                log_debug(f"Navegando para URL de login...")
                self.driver.get("https://portalcorretor.amil.com.br/portal/web/servicos/usuario/corretor/login")
                
                log_debug("Preenchendo credenciais...")
                self.wait.until(EC.presence_of_element_located((By.ID, "login"))).send_keys(AMIL_USER)
                self.wait.until(EC.presence_of_element_located((By.ID, "senha"))).send_keys(AMIL_PASSWORD)
                self.wait.until(EC.element_to_be_clickable((By.ID, "efetuarLogin"))).click()
                
                log_debug("Aguardando redirecionamento pós-login...")
                self.wait.until(EC.url_changes("https://portalcorretor.amil.com.br/portal/web/servicos/usuario/corretor/login"))
                time.sleep(3)
                
                if "login" in self.driver.current_url:
                    raise Exception("Falha no login: Login/Senha incorretos ou erro no site.")

                # Gestão Comercial
                log_debug("Clicando em 'Gestão comercial'...")
                botao_gc = self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Gestão comercial")))
                self.driver.execute_script("arguments[0].click();", botao_gc)
                
                # Troca de aba
                log_debug("Aguardando nova janela/aba...")
                self.wait.until(EC.number_of_windows_to_be(2))
                self.driver.switch_to.window(self.driver.window_handles[1])
                self.sisamil_handle = self.driver.current_window_handle
                log_debug(f"Janela trocada. Título: {self.driver.title}")
                
                # Validação final
                self.wait.until(EC.presence_of_element_located((By.ID, "mostraMenu")))
                
                logging.info("SisAmil conectado com sucesso.")
                self.update_heartbeat()
                return
                
            except InvalidSessionIdException:
                logging.error("Sessão inválida detectada no login! Forçando reinício do driver...")
                self.driver = None # Força recriação na proxima iteracao
                tentativa += 1
                time.sleep(5) # Espera curta para retry rapido

            except Exception as e:
                logging.error(f"Erro no login: {e}", exc_info=True)
                try:
                    self.driver.quit()
                except:
                    pass
                
                tentativa += 1
                tempo_espera = min(backoff * tentativa, 3600)
                logging.info(f"Tentando novamente em {tempo_espera} segundos...")
                time.sleep(tempo_espera)

    def reset_para_proxima_consulta(self):
        """Reseta a tela do SisAmil."""
        try:
            self.update_heartbeat()
            self.driver.get("https://portalcorretor.amil.com.br/portal/web/servicos/usuario/sisamil/acesso/token?uri=/corporativo/ace/token.asp")
            time.sleep(1.5)
        except Exception as e:
            logging.error(f"Erro ao resetar tela: {e}")
            raise

    # ========================================================================
    # EXTRAÇÃO E CONSULTA
    # ========================================================================
    
    def navegar_para_consultar_faturas(self):
        try:
            self.driver.switch_to.default_content()
            self.wait.until(EC.element_to_be_clickable((By.ID, "mostraMenu"))).click()
            time.sleep(1)
            
            self.driver.switch_to.default_content()
            self.driver.switch_to.frame("menu")
            
            log_debug("Navegando no Menu: Portal Cliente Empresa...")
            self.driver.execute_script("arguments[0].click();", self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Portal Cliente Empresa"))))
            log_debug("Navegando no Menu: Gestão Financeira...")
            self.driver.execute_script("arguments[0].click();", self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Gestão Financeira e Demonstrativos"))))
            log_debug("Navegando no Menu: Consultar Faturas...")
            self.driver.execute_script("arguments[0].click();", self.wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Consultar Faturas Emitidas"))))
        except Exception as e:
            logging.error(f"Erro navegação menu: {e}")
            raise

    def extrair_faturas(self):
        try:
            tabela = self.driver.find_element(By.ID, "tbemitida_1")
            linhas = tabela.find_elements(By.TAG_NAME, "tr")[1:]
            faturas = []
            
            for linha in linhas:
                cells = linha.find_elements(By.TAG_NAME, "td")
                if len(cells) < 7: continue
                
                faturas.append({
                    "ciclo": cells[1].get_attribute("textContent").strip().lower(),
                    "referencia": cells[2].get_attribute("textContent").strip(),
                    "vencimento": parse_date(cells[3].get_attribute("textContent").replace("\xa0", "").strip()),
                    "pagamento": parse_date(cells[4].get_attribute("textContent").replace("\xa0", "").strip()),
                    "valor": parse_float(cells[5].get_attribute("textContent").strip().replace("R$", "")),
                    "dias_atraso": int(cells[6].get_attribute("textContent").strip()) if cells[6].get_attribute("textContent").strip().isdigit() else 0,
                })
            log_debug(f"Extraídas {len(faturas)} faturas da tabela.")
            return faturas
        except Exception:
            return []

    def consultar_faturas(self, contrato: str, data_checagem: date, data_vigencia: date = None):
        try:
            self.update_heartbeat()
            self.navegar_para_consultar_faturas()
            
            self.driver.switch_to.default_content()
            self.driver.switch_to.frame("principal")
            
            log_debug(f"Consultando contrato: {contrato}")
            campo_contrato = self.wait.until(EC.presence_of_element_located((By.ID, "num_contrato")))
            contrato_str = str(contrato).strip()
            
            # Preenchimento robusto via JS
            self.driver.execute_script('''
                arguments[0].value = arguments[1];
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            ''', campo_contrato, contrato_str)
            time.sleep(0.5)
            
            self.wait.until(EC.presence_of_element_located((By.ID, "dt_ini_ref"))).send_keys("01/2000")
            self.wait.until(EC.presence_of_element_located((By.ID, "dt_fim_ref"))).send_keys(data_checagem.strftime("%m/%Y"))
            
            self.driver.switch_to.default_content()
            self.driver.switch_to.frame("toolbar")
            self.wait.until(EC.element_to_be_clickable((By.ID, "btn_acao_continuar"))).click()
            time.sleep(3)
            
            # Tratamento de Alertas
            try:
                alert = self.driver.switch_to.alert
                text = alert.text
                alert.accept()
                if "nenhum registro" in text.lower():
                    # Contrato existe mas sem faturas -> Em dia
                    log_debug("Alerta Amil: Nenhum registro encontrado. Considerando 'Em dia'.")
                    return {"valor_parcela": 0.0, "parcelas": 0, "status": "Em dia", "mes_cancelamento": None, "dias_atraso": 0}
                log_debug(f"Alerta Amil inesperado: {text}")
                raise Exception(f"Alert: {text}")
            except Exception as e:
                if "Alert" in str(e): raise
            
            self.driver.switch_to.default_content()
            self.driver.switch_to.frame("principal")
            invoices = self.extrair_faturas()
            
            # Lógica de Status
            log_debug("Iniciando análise de status das faturas extraídas...")
            has_multa = any("multa por rescisão" in i["ciclo"] for i in invoices)
            mens_invoices = [i for i in invoices if "multa por rescisão" not in i["ciclo"]]
            _, pode_checar_d3 = calcular_data_d3(data_vigencia, data_checagem) if data_vigencia else (None, False)
            
            if has_multa:
                status = "Cancelado por Inadimplência"
                multa = next((i for i in invoices if "multa por rescisão" in i["ciclo"]), None)
                mes_cancelamento = multa["referencia"] if multa else None
                dias_atraso = 0
                parcelas = 0
                valor_parcela = 0.0
                log_debug(f"Status definido: {status} (Multa encontrada em {mes_cancelamento})")
            else:
                status = determinar_status_faturas(invoices, data_checagem, data_vigencia, pode_checar_d3)
                mes_cancelamento = None
                
                if status == "Em atraso":
                     overdue = [i for i in mens_invoices if not i["pagamento"] and i["vencimento"] and i["vencimento"] <= data_checagem]
                     if overdue:
                         first = sorted(overdue, key=lambda x: x["vencimento"])[0]
                         try: parcelas = sorted(mens_invoices, key=lambda x: x["vencimento"]).index(first) + 1
                         except: parcelas = 1
                         valor_parcela = first["valor"]
                         dias_atraso = first["dias_atraso"]
                         log_debug(f"Status: Em atraso. Fatura mais antiga: {first['vencimento']}, Dias atraso: {dias_atraso}")
                     else:
                         parcelas = 0
                         valor_parcela = 0.0
                         dias_atraso = 0
                         log_debug("Status: Em atraso, mas não encontrei a fatura exata na lista filtrada. Zerando métricas.")
                else:
                    parcelas = 0
                    valor_parcela = 0.0
                    dias_atraso = 0
                    log_debug(f"Status definido: {status}")
            
            return {
                "valor_parcela": valor_parcela,
                "parcelas": parcelas,
                "status": status,
                "mes_cancelamento": mes_cancelamento,
                "dias_atraso": dias_atraso
            }
            
        except Exception as e:
            logging.error(f"Erro consulta contrato {contrato}: {e}", exc_info=True)
            raise

    # ========================================================================
    # ATUALIZAÇÃO E EXECUÇÃO
    # ========================================================================
    
    def _verificar_contrato_safe(self, contrato, hoje, tipo="", max_retries=2):
        """Wrapper com retry local."""
        for i in range(max_retries + 1):
            try:
                return self._verificar_contrato_impl(contrato, hoje, tipo)
            except InvalidSessionIdException:
                logging.error(f"Sessão morreu durante contrato {contrato.contrato}. Resetando driver.")
                self.driver = None
                try: self.login_e_navegar_sisamil()
                except: pass
            except Exception as e:
                logging.warning(f"Erro contrato {contrato.contrato} (Tentativa {i+1}): {e}")
                if i < max_retries:
                    try: self.reset_para_proxima_consulta()
                    except: pass
                else:
                    return False

    def _verificar_contrato_impl(self, contrato, hoje, tipo=""):
        contrato_bruto = re.sub(r"\D", "", (contrato.contrato or ""))
        if not contrato_bruto: return False
        
        logging.info(f"[{tipo}] Verificando {contrato.contrato}...")
        res = self.consultar_faturas(contrato_bruto, hoje, contrato.data_vigencia)
        
        contrato.status = res["status"]
        contrato.valor_parcela = res["valor_parcela"]
        contrato.parcela_atual = res["parcelas"]
        contrato.dias_atraso = res["dias_atraso"]
        contrato.data_checagem = hoje
        
        if res["mes_cancelamento"]:
            try: contrato.mes_cancelamento = datetime.strptime(res["mes_cancelamento"], "%m/%Y").date().replace(day=1)
            except: pass
        else:
            contrato.mes_cancelamento = None
            
        # NOVA REGRA: 61+ DIAS = CANCELADO POR INADIMPLÊNCIA (AUTOMATICAMENTE)
        if contrato.status == "Em atraso" and contrato.dias_atraso > 60:
            log_debug(f"Contrato {contrato.contrato} CANCELADO POR INADIMPLÊNCIA (Atraso {contrato.dias_atraso}d > 60d)")
            contrato.status = "Cancelado por Inadimplência"
            
        db.session.commit()
        
        if res["status"] == "Em atraso":
            self._criar_acao(contrato)
            
        self.reset_para_proxima_consulta()
        return True

    def _criar_acao(self, contrato):
        try:
            if not AcaoCobranca.query.filter_by(contrato_id=contrato.id, dia_atraso=contrato.dias_atraso).first():
                db.session.add(AcaoCobranca(
                    contrato_id=contrato.id, tipo="SMS", 
                    mensagem=f"Cobrança {contrato.contrato} atraso {contrato.dias_atraso}d",
                    parcela=contrato.parcela_atual, dia_atraso=contrato.dias_atraso,
                    enviada_em=datetime.now(pytz.timezone("America/Sao_Paulo")),
                    status_envio="Enviado"
                ))
                db.session.commit()
        except: pass

    def atualizar_banco(self):
        with app.app_context():
            db.session.remove()
            hoje = datetime.now(pytz.timezone("America/Sao_Paulo")).date()
            
            logging.info("🔎 Levantando contratos para verificação...")
            
            # 1. EM ATRASO
            candidatos_atraso = Contrato.query.filter(Contrato.status == "Em atraso", Contrato.data_checagem != hoje).all()
            
            # 2. ATIVOS (D+3)
            # Filtra em memória (lógica python de D+3)
            raw_ativos = Contrato.query.filter(Contrato.status.in_(["Em dia", "Pago"])).all()
            candidatos_ativos = []
            for c in raw_ativos:
                d3, pode = calcular_data_d3(c.data_vigencia, hoje)
                if pode and (not c.data_checagem or c.data_checagem < d3):
                    candidatos_ativos.append(c)
            
            # 3. MORTOS (REMOVIDO - CLIENTES MORTOS NÃO EXISTEM MAIS)
            # Todo contrato morto anterior deve ter sido migrado para "Cancelado por Inadimplência"
            # Cancelados não são verificados automaticamente.
            
            total_previsao = len(candidatos_atraso) + len(candidatos_ativos)
            
            logging.info("="*50)
            logging.info(f"📊 PREVISÃO DE EXECUÇÃO: {total_previsao} contratos na fila.")
            logging.info(f"   ➤ Atrasados: {len(candidatos_atraso)}")
            logging.info(f"   ➤ Ativos (D+3): {len(candidatos_ativos)}")
            logging.info("="*50)
            
            if total_previsao == 0:
                self._dormir(hoje)
                return

            c = 0
            
            # PROCESSAMENTO
            for contrato in candidatos_atraso:
                self.update_heartbeat()
                if self._verificar_contrato_safe(contrato, hoje, "ATRASO"): c += 1
            
            for contrato in candidatos_ativos:
                self.update_heartbeat()
                if self._verificar_contrato_safe(contrato, hoje, "ATIVO"): c += 1
            
            logging.info(f"Ciclo concluído. {c} contratos verificados com sucesso.")

    def _deve_checar_espacado(self, contrato, hoje):
        """DEPRECATED: Função de checagem de mortos."""
        return False

    def _log_previsao(self, hoje):
        # Log simplificado para cleaner code
        logging.info("Iniciando novo ciclo de verificação...")

    def _dormir(self, hoje):
        """
        Antiga função que dormia até 00:05.
        Agora apenas finaliza o ciclo para que o loop principal aguarde o intervalo padrão.
        """
        logging.info("Ciclo de verificação diária concluído. Nenhuma pendência encontrada.")
        # Não força mais a espera até 00:05, apenas retorna para o loop de 5min
        pass

    def run(self):
        self.watchdog_thread = threading.Thread(target=self.watchdog_monitor, daemon=True)
        self.watchdog_thread.start()
        
        try:
            self.login_e_navegar_sisamil()
            while True:
                try:
                    self.update_heartbeat()
                    self.atualizar_banco()
                except Exception as e:
                    logging.error(f"Erro ciclo: {e}")
                    try: self.login_e_navegar_sisamil()
                    except: pass
                
                logging.info(f"Aguardando {INTERVALO_EXECUCAO}s...")
                for _ in range(int(INTERVALO_EXECUCAO/10)):
                    time.sleep(10)
                    self.update_heartbeat()
                    
        except KeyboardInterrupt:
            self.running = False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Automacao Bree')
    parser.add_argument('--loop', action='store_true', help='Executa em loop infinito com intervalos (modo serviço)')
    args = parser.parse_args()

    try:
        bot = AutomacaoBree()
        if args.loop:
            logging.info("Modo Loop (--loop) ativado. Execução contínua.")
            bot.run()
        else:
            logging.info("Modo Padrão (Single Run). Executando um ciclo e encerrando.")
            try:
                bot.login_e_navegar_sisamil()
                bot.atualizar_banco()
            finally:
                if bot.driver: bot.driver.quit()
            
    except Exception as e:
        # Se explodir no init, tenta logar e sai
        with open("logs/fatal.txt", "a") as f: f.write(str(e))
        sys.exit(1)
