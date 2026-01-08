# 📦 Instruções para Executáveis Portáteis - Bree System

## 🚀 Como Gerar os Executáveis

### Opção 1: Script Automático (Recomendado)
```batch
gerar_executaveis.bat
```

### Opção 2: Manual
```powershell
# 1. Ative o ambiente virtual
.\venv\Scripts\activate

# 2. Gere o executável da automação
pyinstaller automacao.spec

# 3. Gere o executável do sistema
pyinstaller bree.spec
```

Os executáveis serão gerados na pasta `dist\`:
- `BreeAutomacao.exe` - Automação de verificação de contratos
- `BreeSistema.exe` - Sistema web Bree

---

## 💻 Como Usar no PC Destino

### Pré-requisitos no PC Destino:

1. **PostgreSQL instalado e configurado**
   - O banco de dados deve estar acessível
   - A string de conexão está no código (verifique em `bree.py` linha 191)

2. **Chrome/Chromium instalado**
   - Necessário para a automação (Selenium)
   - O ChromeDriver será baixado automaticamente na primeira execução

3. **Firewall/Portas**
   - O sistema web usa a porta 5000 (padrão)
   - Certifique-se de que a porta está liberada

---

## 📋 Passos para Executar

### 1. Automação (BreeAutomacao.exe)

1. Copie `BreeAutomacao.exe` para o PC destino
2. Execute o arquivo
3. Uma janela de console será aberta mostrando os logs
4. A pasta `logs\` será criada automaticamente no mesmo diretório
5. A automação rodará continuamente verificando contratos

**Observações:**
- A automação precisa de conexão com a internet (para acessar o portal Amil)
- A primeira execução pode demorar mais (download do ChromeDriver)
- Para parar a automação, feche a janela do console

### 2. Sistema Web (BreeSistema.exe)

1. Copie `BreeSistema.exe` para o PC destino
2. Execute o arquivo
3. Uma janela de console será aberta mostrando o servidor Flask
4. Abra o navegador e acesse: `http://localhost:5000`
5. Faça login no sistema

**Observações:**
- O sistema web precisa estar rodando para acessar a interface
- Para parar o servidor, feche a janela do console
- Certifique-se de que o banco de dados está configurado corretamente

---

## ⚙️ Configurações Importantes

### String de Conexão do Banco de Dados

A string de conexão está em `bree.py` (linha 191). Se precisar alterar:

**Opção 1:** Edite o código antes de gerar o executável
**Opção 2:** Use variáveis de ambiente (requer ajuste no código)

### Credenciais do Portal Amil

As credenciais estão em `automacao.py` (linhas 64-65). Se precisar alterar:

**Opção 1:** Edite o código antes de gerar o executável
**Opção 2:** Use variáveis de ambiente (requer ajuste no código)

---

## 🔧 Solução de Problemas

### Erro: "Módulo não encontrado"
- Certifique-se de que todas as dependências estão no `hiddenimports` do `.spec`
- Regenere o executável

### Erro: "ChromeDriver não encontrado"
- A primeira execução baixa automaticamente
- Certifique-se de que há conexão com a internet

### Erro: "Não foi possível conectar ao banco"
- Verifique se o PostgreSQL está rodando
- Verifique a string de conexão em `bree.py`
- Verifique se o firewall permite a conexão

### Executável muito grande
- Isso é normal, inclui todas as dependências
- O executável é portátil e não precisa de instalação

---

## 📝 Notas Importantes

1. **Primeira Execução:**
   - A automação pode demorar mais na primeira vez (download do ChromeDriver)
   - O sistema web pode demorar para iniciar na primeira vez

2. **Logs:**
   - Os logs são salvos na pasta `logs\` (criada automaticamente)
   - Cada execução gera um novo arquivo de log

3. **Performance:**
   - Os executáveis são maiores que os scripts Python
   - Mas são completamente portáteis e não precisam de instalação

4. **Atualizações:**
   - Para atualizar, regenere os executáveis com o código atualizado
   - Não é necessário reinstalar nada no PC destino

---

## 🆘 Suporte

Em caso de problemas:
1. Verifique os logs na pasta `logs\`
2. Verifique se todas as dependências estão instaladas no ambiente de desenvolvimento
3. Certifique-se de que o código está funcionando antes de gerar o executável

