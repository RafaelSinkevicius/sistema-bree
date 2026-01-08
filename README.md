# Sistema Bree 🐝

Sistema de automação para verificação de status de contratos Amil e gestão de cobrança.

## Estrutura do Projeto

- **`app/`**: Aplicação Flask (Backend e Frontend).
- **`scripts/`**: Scripts de automação e utilitários (`automacao.py`, `check_status.py`).
- **`data/`**: Arquivos de dados e planilhas.
- **`docs/`**: Documentação.

## Configuração

1. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure as Variáveis de Ambiente**:
   - Copie o arquivo `.env.example` para `.env`:
     ```bash
     cp .env.example .env  # Linux/Mac
     copy .env.example .env # Windows
     ```
   - Edite o arquivo `.env` e adicione suas credenciais da Amil:
     ```
     AMIL_USER=seu_usuario
     AMIL_PASSWORD=sua_senha
     ```

## Executando

### Aplicação Web (Dashboard)
```bash
python run.py
```
Acesse em: `http://localhost:5000`

### Automação (Bot)
Para rodar manualmente em modo de desenvolvimento:
```bash
python scripts/automacao.py
```

## 📦 Criando Executáveis (.exe)
Para gerar os arquivos `SistemaBree_Interface.exe` e `SistemaBree_Automacao.exe` para distribuição:

1. Execute o script de build:
   ```bash
   python build_exe.py
   ```
2. Os arquivos estarão na pasta `dist/`.
3. **Importante**: Ao mover para o PC final, copie a pasta `dist` inteira e certifique-se de criar o arquivo `.env` dentro dela (ao lado dos executáveis).

## 🌐 Acesso em Rede (IP Fixo)
Para acessar o sistema de outros computadores sem preocupação com mudança de IP:
1. Em vez do IP (ex: `192.168.0.XX`), use o **NOME DO COMPUTADOR**.
2. Descubra o nome no PC servidor rodando `hostname` no terminal (ex: `DESKTOP-19DTU11`).
3. Acesse no navegador: `http://DESKTOP-19DTU11:5000` (substitua pelo nome real).
   - Isso funciona automaticamente no Windows e evita configurações complexas de roteador.

## 🤖 Automação no Agendador de Tarefas
Se for agendar o robô no Windows Task Scheduler para rodar uma vez por dia (ex: 00:05):
1. No campo "Argumentos" da tarefa, adicione: `--once`
   - Exemplo: `C:\Caminho\SistemaBree_Automacao.exe`
   - Argumento: `--once`
2. Isso fará o robô rodar o ciclo completo, processar tudo e fechar sozinho.

## Notas de Segurança
- O arquivo `.env` contém senhas e **NÃO** deve ser commitado no Git.
- O arquivo `.gitignore` já está configurado para excluir dados sensíveis e arquivos temporários.
