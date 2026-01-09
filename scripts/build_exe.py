import PyInstaller.__main__
import os
import shutil

# Limpa builds anteriores
if os.path.exists("dist"): shutil.rmtree("dist")
if os.path.exists("build"): shutil.rmtree("build")

print("🚀 Iniciando Build do Sistema Bree...")

# 1. Build da Interface (Web)
print("🔨 Compilando Interface (Web)...")
PyInstaller.__main__.run([
    'run.py',
    '--name=SistemaBree_Interface',
    '--onefile',
    '--add-data=app/templates;app/templates',
    '--add-data=app/static;app/static',
    '--hidden-import=pg8000',
    '--hidden-import=sqlalchemy.sql.default_comparator',
    '--icon=app/static/favicon.ico' if os.path.exists('app/static/favicon.ico') else '--clean',
])

# 2. Build da Automação (Bot)
print("🔨 Compilando Automação (Bot)...")
PyInstaller.__main__.run([
    'scripts/automacao.py',
    '--name=SistemaBree_Automacao',
    '--onefile',
    '--add-data=.env;.env', # Tenta incluir .env, mas ideal é usuário fornecer
    '--hidden-import=selenium',
    '--hidden-import=webdriver_manager',
])

# 3. Build da Migração (DB Fix)
print("🔨 Compilando Migração (DB Fix)...")
PyInstaller.__main__.run([
    'scripts/master_migration.py',
    '--name=MigracaoBree_V3',
    '--onefile',
    '--hidden-import=pg8000',
    '--hidden-import=sqlalchemy.sql.default_comparator',
    '--hidden-import=flask_sqlalchemy',
])

print("✅ Builds concluídos! Executáveis na pasta 'dist/'.")
print("⚠️ IMPORTANTE: Copie a pasta 'dist' para o PC de produção e certifique-se de que o arquivo .env esteja na mesma pasta dos executáveis.")
