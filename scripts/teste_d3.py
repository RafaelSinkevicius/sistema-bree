"""
TESTE PRÁTICO EM PRODUÇÃO: Simula datas e testa lógica D+3 completa
Permite testar sem esperar o dia certo, configurando contratos reais
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date, timedelta, datetime
from app import app, db, Contrato
from scripts.automacao import calcular_data_d3, DIAS_D3

class TesteD3Producao:
    """Classe para testar D+3 em produção com simulação de datas."""
    
    def __init__(self):
        self.contratos_backup = []  # Guarda dados originais para restaurar
        
    def configurar_contrato_teste(self, contrato_id, vigencia_dia, data_hoje_simulada, data_checagem_antiga=None):
        """
        Configura um contrato para teste.
        
        Args:
            contrato_id: ID do contrato no banco
            vigencia_dia: Dia da vigência (ex: 30 para dia 30)
            data_hoje_simulada: Data que queremos simular como "hoje"
            data_checagem_antiga: Data da última checagem (padrão: 5 dias do mês anterior)
        """
        with app.app_context():
            contrato = Contrato.query.get(contrato_id)
            if not contrato:
                print(f"[X] Contrato ID {contrato_id} não encontrado!")
                return False
            
            # Backup dos dados originais
            self.contratos_backup.append({
                'id': contrato.id,
                'data_vigencia_original': contrato.data_vigencia,
                'data_checagem_original': contrato.data_checagem,
                'status_original': contrato.status
            })
            
            # Calcula vigência do mês anterior à data simulada
            if data_hoje_simulada.month == 1:
                mes_vigencia = 12
                ano_vigencia = data_hoje_simulada.year - 1
            else:
                mes_vigencia = data_hoje_simulada.month - 1
                ano_vigencia = data_hoje_simulada.year
            
            # Configura vigência
            try:
                vigencia_teste = date(ano_vigencia, mes_vigencia, vigencia_dia)
            except ValueError:
                # Se dia não existe (ex: 31 em fevereiro), usa 28
                vigencia_teste = date(ano_vigencia, mes_vigencia, 28)
            
            # Configura data_checagem (padrão: 5 dias do mês anterior)
            if data_checagem_antiga is None:
                data_checagem_antiga = date(ano_vigencia, mes_vigencia, 5)
            
            # Atualiza contrato
            contrato.data_vigencia = vigencia_teste
            contrato.data_checagem = data_checagem_antiga
            contrato.status = "Em dia"
            
            db.session.commit()
            
            print(f"[OK] Contrato {contrato.contrato} (ID {contrato.id}) configurado:")
            print(f"     Vigência: {vigencia_teste}")
            print(f"     Última checagem: {data_checagem_antiga}")
            print(f"     Status: Em dia")
            return True
    
    def testar_lógica_completa(self, data_hoje_simulada):
        """
        Testa a lógica completa de _processar_contratos_ativos
        sem realmente verificar no portal.
        
        Args:
            data_hoje_simulada: Data que queremos simular como "hoje"
        """
        with app.app_context():
            print("\n" + "=" * 70)
            print(f"TESTANDO LÓGICA COMPLETA - Data simulada: {data_hoje_simulada}")
            print("=" * 70)
            
            # Busca contratos ativos (mesma query da automação)
            contratos_ativos = Contrato.query.filter(
                Contrato.status.in_(["Em dia", "Pago"])
            ).order_by(Contrato.data_checagem.asc()).all()
            
            print(f"\nTotal de contratos ativos no banco: {len(contratos_ativos)}")
            print()
            
            contratos_para_verificar = []
            contratos_nao_verificar = []
            
            for contrato in contratos_ativos:
                if not contrato.data_vigencia:
                    continue
                
                # Usa a mesma lógica da automação
                data_d3, pode_checar = calcular_data_d3(contrato.data_vigencia, data_hoje_simulada)
                
                if not pode_checar:
                    contratos_nao_verificar.append({
                        'contrato': contrato,
                        'motivo': f"Ainda não chegou D+3 (D+3 = {data_d3})"
                    })
                    continue
                
                # Verifica se já foi checado neste ciclo
                ja_checou_neste_ciclo = (
                    contrato.data_checagem is not None and 
                    contrato.data_checagem >= data_d3
                )
                
                if ja_checou_neste_ciclo:
                    contratos_nao_verificar.append({
                        'contrato': contrato,
                        'motivo': f"Já checou neste ciclo (checagem {contrato.data_checagem} >= D+3 {data_d3})"
                    })
                else:
                    contratos_para_verificar.append({
                        'contrato': contrato,
                        'data_d3': data_d3,
                        'data_checagem': contrato.data_checagem
                    })
            
            # Mostra resultados
            print(f"CONTRATOS QUE SERIAM VERIFICADOS: {len(contratos_para_verificar)}")
            print("-" * 70)
            
            if contratos_para_verificar:
                for item in contratos_para_verificar[:10]:  # Mostra até 10
                    c = item['contrato']
                    print(f"  [VERIFICAR] Contrato {c.contrato} (ID {c.id})")
                    print(f"             Vigência: {c.data_vigencia.day} (dia {c.data_vigencia.day})")
                    print(f"             D+3 calculado: {item['data_d3']}")
                    print(f"             Última checagem: {item['data_checagem']}")
                    print()
                
                if len(contratos_para_verificar) > 10:
                    print(f"  ... e mais {len(contratos_para_verificar) - 10} contratos")
                    print()
            
            # Verifica especificamente contratos fim de mês
            print("\nCONTRATOS FIM DE MÊS (28-31) QUE SERIAM VERIFICADOS:")
            print("-" * 70)
            
            fim_mes_verificar = [
                item for item in contratos_para_verificar 
                if item['contrato'].data_vigencia and item['contrato'].data_vigencia.day >= 28
            ]
            
            if fim_mes_verificar:
                for item in fim_mes_verificar:
                    c = item['contrato']
                    print(f"  [OK] Contrato {c.contrato} (ID {c.id})")
                    print(f"       Vigência: {c.data_vigencia} (dia {c.data_vigencia.day})")
                    print(f"       D+3: {item['data_d3']} (mês {item['data_d3'].month})")
                    print(f"       Última checagem: {item['data_checagem']}")
                    
                    # Verifica se D+3 está correto
                    if item['data_d3'].month == data_hoje_simulada.month:
                        print(f"       [CORRETO] D+3 cai no mês atual ({data_hoje_simulada.month})")
                    else:
                        print(f"       [ATENCAO] D+3 cai em {item['data_d3'].month}, mês atual é {data_hoje_simulada.month}")
                    print()
            else:
                print("  Nenhum contrato fim de mês seria verificado.")
            
            print(f"\nTotal: {len(contratos_para_verificar)} contratos seriam verificados")
            print(f"Total fim de mês: {len(fim_mes_verificar)} contratos")
            
            return contratos_para_verificar
    
    def restaurar_dados_originais(self):
        """Restaura os dados originais dos contratos modificados."""
        with app.app_context():
            if not self.contratos_backup:
                print("[!] Nenhum backup para restaurar.")
                return
            
            print("\n" + "=" * 70)
            print("RESTAURANDO DADOS ORIGINAIS")
            print("=" * 70)
            
            for backup in self.contratos_backup:
                contrato = Contrato.query.get(backup['id'])
                if contrato:
                    contrato.data_vigencia = backup['data_vigencia_original']
                    contrato.data_checagem = backup['data_checagem_original']
                    contrato.status = backup['status_original']
                    print(f"[OK] Contrato ID {backup['id']} restaurado")
            
            db.session.commit()
            self.contratos_backup = []
            print("\n[OK] Todos os dados foram restaurados!")
    
    def testar_lista_contratos(self, contratos_lista, data_hoje_simulada, vigencia_dia=30):
        """
        Testa uma lista específica de contratos e gera log em TXT.
        
        Args:
            contratos_lista: Lista de números de contrato
            data_hoje_simulada: Data que queremos simular como "hoje"
            vigencia_dia: Dia da vigência para configurar (padrão: 30)
        """
        # Nome do arquivo de log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"teste_d3_contratos_{timestamp}.txt"
        
        # Função para escrever no log e no console
        log_lines = []
        
        def log(msg):
            log_lines.append(msg)
            print(msg)
        
        log("=" * 80)
        log("TESTE D+3 - LISTA ESPECÍFICA DE CONTRATOS")
        log("=" * 80)
        log(f"Data simulada (hoje): {data_hoje_simulada}")
        log(f"Vigência configurada: dia {vigencia_dia}")
        log(f"Total de contratos na lista: {len(contratos_lista)}")
        log("")
        
        with app.app_context():
            contratos_encontrados = []
            contratos_nao_encontrados = []
            
            # Busca contratos no banco
            log("Buscando contratos no banco...")
            for num_contrato in contratos_lista:
                contrato = Contrato.query.filter_by(contrato=num_contrato).first()
                if contrato:
                    contratos_encontrados.append(contrato)
                    # Backup
                    self.contratos_backup.append({
                        'id': contrato.id,
                        'contrato': contrato.contrato,
                        'data_vigencia_original': contrato.data_vigencia,
                        'data_checagem_original': contrato.data_checagem,
                        'status_original': contrato.status
                    })
                else:
                    contratos_nao_encontrados.append(num_contrato)
            
            log(f"Contratos encontrados: {len(contratos_encontrados)}")
            log(f"Contratos NAO encontrados: {len(contratos_nao_encontrados)}")
            if contratos_nao_encontrados:
                log(f"Contratos não encontrados (primeiros 20): {', '.join(contratos_nao_encontrados[:20])}")
            log("")
            
            # Configura contratos para teste
            log("=" * 80)
            log("CONFIGURANDO CONTRATOS PARA TESTE")
            log("=" * 80)
            
            # Calcula vigência do mês anterior
            if data_hoje_simulada.month == 1:
                mes_vigencia = 12
                ano_vigencia = data_hoje_simulada.year - 1
            else:
                mes_vigencia = data_hoje_simulada.month - 1
                ano_vigencia = data_hoje_simulada.year
            
            try:
                vigencia_teste = date(ano_vigencia, mes_vigencia, vigencia_dia)
            except ValueError:
                vigencia_teste = date(ano_vigencia, mes_vigencia, 28)
            
            data_checagem_antiga = date(ano_vigencia, mes_vigencia, 5)
            
            for contrato in contratos_encontrados:
                contrato.data_vigencia = vigencia_teste
                contrato.data_checagem = data_checagem_antiga
                contrato.status = "Em dia"
            
            db.session.commit()
            log(f"Configurados {len(contratos_encontrados)} contratos:")
            log(f"  Vigência: {vigencia_teste}")
            log(f"  Última checagem: {data_checagem_antiga}")
            log("")
            
            # Testa a lógica
            log("=" * 80)
            log("TESTANDO LÓGICA D+3")
            log("=" * 80)
            
            resultados = {
                'seriam_verificados': [],
                'nao_seriam_verificados': [],
                'erros': []
            }
            
            for contrato in contratos_encontrados:
                try:
                    data_d3, pode_checar = calcular_data_d3(contrato.data_vigencia, data_hoje_simulada)
                    
                    if not pode_checar:
                        resultados['nao_seriam_verificados'].append({
                            'contrato': contrato.contrato,
                            'id': contrato.id,
                            'motivo': f"Ainda não chegou D+3 (D+3 = {data_d3})"
                        })
                        continue
                    
                    # Verifica se já foi checado neste ciclo
                    ja_checou_neste_ciclo = (
                        contrato.data_checagem is not None and 
                        contrato.data_checagem >= data_d3
                    )
                    
                    if ja_checou_neste_ciclo:
                        resultados['nao_seriam_verificados'].append({
                            'contrato': contrato.contrato,
                            'id': contrato.id,
                            'motivo': f"Já checou neste ciclo (checagem {contrato.data_checagem} >= D+3 {data_d3})"
                        })
                    else:
                        resultados['seriam_verificados'].append({
                            'contrato': contrato.contrato,
                            'id': contrato.id,
                            'data_d3': data_d3,
                            'data_checagem': contrato.data_checagem,
                            'vigencia_dia': contrato.data_vigencia.day if contrato.data_vigencia else None
                        })
                except Exception as e:
                    resultados['erros'].append({
                        'contrato': contrato.contrato,
                        'id': contrato.id,
                        'erro': str(e)
                    })
            
            # Gera relatório
            log("")
            log("=" * 80)
            log("RESULTADOS DO TESTE")
            log("=" * 80)
            log(f"Total de contratos testados: {len(contratos_encontrados)}")
            log(f"Contratos que SERIAM verificados: {len(resultados['seriam_verificados'])}")
            log(f"Contratos que NAO seriam verificados: {len(resultados['nao_seriam_verificados'])}")
            log(f"Erros: {len(resultados['erros'])}")
            log("")
            
            # Detalhes dos que seriam verificados
            if resultados['seriam_verificados']:
                log("-" * 80)
                log("CONTRATOS QUE SERIAM VERIFICADOS:")
                log("-" * 80)
                
                # Agrupa por D+3
                por_d3 = {}
                for item in resultados['seriam_verificados']:
                    d3_str = str(item['data_d3'])
                    if d3_str not in por_d3:
                        por_d3[d3_str] = []
                    por_d3[d3_str].append(item)
                
                for d3_str in sorted(por_d3.keys()):
                    items = por_d3[d3_str]
                    log(f"\nD+3 = {d3_str} ({len(items)} contratos):")
                    for item in items:
                        log(f"  - Contrato {item['contrato']} (ID {item['id']}) - Vigência dia {item['vigencia_dia']}")
            
            # Verifica especificamente contratos fim de mês
            fim_mes_verificar = [
                item for item in resultados['seriam_verificados']
                if item.get('vigencia_dia') and item['vigencia_dia'] >= 28
            ]
            
            log("")
            log("-" * 80)
            log(f"CONTRATOS FIM DE MÊS (28-31) QUE SERIAM VERIFICADOS: {len(fim_mes_verificar)}")
            log("-" * 80)
            
            if fim_mes_verificar:
                # Verifica se D+3 está correto (deve cair no mês atual)
                corretos = 0
                incorretos = 0
                
                for item in fim_mes_verificar:
                    if item['data_d3'].month == data_hoje_simulada.month:
                        corretos += 1
                    else:
                        incorretos += 1
                        log(f"  [ATENCAO] Contrato {item['contrato']}: D+3 = {item['data_d3']} (mês {item['data_d3'].month}), esperado mês {data_hoje_simulada.month}")
                
                log(f"  Corretos (D+3 no mês atual): {corretos}")
                log(f"  Incorretos (D+3 em outro mês): {incorretos}")
            
            # Detalhes dos que não seriam verificados
            if resultados['nao_seriam_verificados']:
                log("")
                log("-" * 80)
                log("CONTRATOS QUE NAO SERIAM VERIFICADOS:")
                log("-" * 80)
                
                # Agrupa por motivo
                por_motivo = {}
                for item in resultados['nao_seriam_verificados']:
                    motivo = item['motivo']
                    if motivo not in por_motivo:
                        por_motivo[motivo] = []
                    por_motivo[motivo].append(item)
                
                for motivo, items in por_motivo.items():
                    log(f"\n{motivo}: {len(items)} contratos")
                    for item in items[:20]:  # Mostra até 20 por motivo
                        log(f"  - Contrato {item['contrato']} (ID {item['id']})")
                    if len(items) > 20:
                        log(f"  ... e mais {len(items) - 20} contratos")
            
            # Erros
            if resultados['erros']:
                log("")
                log("-" * 80)
                log("ERROS:")
                log("-" * 80)
                for item in resultados['erros']:
                    log(f"  Contrato {item['contrato']} (ID {item['id']}): {item['erro']}")
            
            # Restaura dados originais
            log("")
            log("=" * 80)
            log("RESTAURANDO DADOS ORIGINAIS")
            log("=" * 80)
            
            for backup in self.contratos_backup:
                contrato = Contrato.query.get(backup['id'])
                if contrato:
                    contrato.data_vigencia = backup['data_vigencia_original']
                    contrato.data_checagem = backup['data_checagem_original']
                    contrato.status = backup['status_original']
            
            db.session.commit()
            log(f"Restaurados {len(self.contratos_backup)} contratos")
            
            # Salva log em arquivo
            log("")
            log("=" * 80)
            log("TESTE CONCLUÍDO")
            log("=" * 80)
            
            try:
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(log_lines))
                log(f"Log salvo em: {log_file}")
            except Exception as e:
                log(f"Erro ao salvar log: {e}")
            
            return resultados


def main():
    """Função principal para rodar os testes."""
    teste = TesteD3Producao()
    
    print("=" * 70)
    print("TESTE PRÁTICO D+3 EM PRODUÇÃO")
    print("=" * 70)
    print("\nEste script permite:")
    print("1. Configurar contratos reais para teste")
    print("2. Simular diferentes datas 'hoje'")
    print("3. Ver quais contratos seriam verificados")
    print("4. Restaurar dados originais depois")
    print()
    
    # Exemplo de uso
    print("EXEMPLO DE USO:")
    print("-" * 70)
    print("1. Configure um contrato para teste:")
    print("   teste.configurar_contrato_teste(")
    print("       contrato_id=1234,")
    print("       vigencia_dia=30,")
    print("       data_hoje_simulada=date(2025, 12, 2)  # Simula 02/12")
    print("   )")
    print()
    print("2. Teste a lógica completa:")
    print("   teste.testar_lógica_completa(date(2025, 12, 2))")
    print()
    print("3. Restaure os dados:")
    print("   teste.restaurar_dados_originais()")
    print()
    
    # Teste automático com exemplo
    print("\n" + "=" * 70)
    print("RODANDO TESTE AUTOMÁTICO")
    print("=" * 70)
    
    # Busca um contrato real para teste
    with app.app_context():
        contrato_teste = Contrato.query.filter(
            Contrato.status.in_(["Em dia", "Pago"]),
            Contrato.data_vigencia.isnot(None)
        ).first()
        
        if contrato_teste:
            print(f"\nUsando contrato {contrato_teste.contrato} (ID {contrato_teste.id}) para teste")
            
            # CENÁRIO 1: Simula 02/12 (deveria usar D+3 de novembro)
            print("\n" + "-" * 70)
            print("CENÁRIO 1: Data simulada = 02/12/2025")
            print("Vigência: 30/11, D+3 esperado: 03/12")
            print("-" * 70)
            
            teste.configurar_contrato_teste(
                contrato_id=contrato_teste.id,
                vigencia_dia=30,
                data_hoje_simulada=date(2025, 12, 2)
            )
            
            teste.testar_lógica_completa(date(2025, 12, 2))
            
            # CENÁRIO 2: Simula 03/12 (D+3 de novembro)
            print("\n" + "-" * 70)
            print("CENÁRIO 2: Data simulada = 03/12/2025")
            print("Vigência: 30/11, D+3: 03/12 (hoje!)")
            print("-" * 70)
            
            teste.testar_lógica_completa(date(2025, 12, 3))
            
            # Restaura
            teste.restaurar_dados_originais()
        else:
            print("[X] Nenhum contrato encontrado para teste")


def main_lista_contratos():
    """Função para testar lista específica de contratos."""
    # Lista reduzida de contratos (primeiros 50)
    contratos_lista = [
        "2467956000", "2469631000", "2180931000", "2180919000", "2180916000",
        "2180912000", "2180909000", "2180906000", "2180905000", "2180902000",
        "2498149000", "2469621000", "2429905000", "2180901000", "2444999000",
        "2469620000", "2526161000", "2526518000", "2526511000", "2526519000",
        "2526513000", "2526510000", "2180899000", "2180898000", "2180876000",
        "2431942000", "2180870000", "2180834000", "2498550000", "2526491000",
        "2526504000", "2088242000", "2526503000", "2526501000", "2525543000",
        "2171235000", "2469608000", "2553046000", "2429917000", "2431888000",
        "2346597000", "2346598000", "2526502000", "2346594000", "2346593000",
        "2346587000", "2526499000", "2526483000", "2526482000", "2526481000",
        "2346581000", "2059372000", "2346578000", "2346566000", "2160637000"
    ]
    
    teste = TesteD3Producao()
    
    # Testa com data simulada: 02/12/2025
    # (deveria usar D+3 de novembro = 03/12)
    teste.testar_lista_contratos(
        contratos_lista=contratos_lista,
        data_hoje_simulada=date(2025, 12, 2),
        vigencia_dia=30
    )


if __name__ == "__main__":
    import sys
    
    # Se passar argumento "lista", testa a lista de contratos
    if len(sys.argv) > 1 and sys.argv[1] == "lista":
        main_lista_contratos()
    else:
        main()