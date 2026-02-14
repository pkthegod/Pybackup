import requests
import hashlib
import os
import argparse
import subprocess
import logging
from datetime import datetime
from dotenv import load_dotenv

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/rpz_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('rpz_client')

# Carrega as variáveis de ambiente
load_dotenv()

# Configurações
API_URL = "https://api.procyon.tec.br"
API_KEY = "ProcyonTecnologia2024"  # Definindo a chave diretamente ou use 
#API_KEY = os.getenv('API_KEY', 'default')
LOCAL_RPZ_FILE = "/etc/bind/rpz/db.rpz.zone.hosts"
BACKUP_DIR = "/etc/bind/rpz/backups"

def ensure_directories():
    """Garante que os diretórios necessários existam"""
    os.makedirs(os.path.dirname(LOCAL_RPZ_FILE), exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)

def backup_current_file():
    """Faz backup do arquivo RPZ atual se ele existir"""
    if os.path.exists(LOCAL_RPZ_FILE):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(BACKUP_DIR, f"db.rpz.zone.hosts.{timestamp}")
        try:
            subprocess.run(['cp', LOCAL_RPZ_FILE, backup_file], check=True)
            logger.info(f"Backup criado: {backup_file}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Erro ao criar backup: {e}")

def get_rpz_hash():
    """Obtém o hash do arquivo RPZ do servidor."""
    try:
        headers = {'X-API-Key': API_KEY}
        response = requests.get(f"{API_URL}/rpz_hash", headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()['hash']
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao obter hash do servidor: {e}")
        raise

def download_rpz_zone():
    """Baixa o arquivo de zona RPZ do servidor."""
    try:
        headers = {'X-API-Key': API_KEY}
        response = requests.get(f"{API_URL}/rpz_zone", headers=headers, timeout=30)
        response.raise_for_status()
        
        # Faz backup do arquivo atual antes de substituir
        backup_current_file()
        
        # Salva o novo arquivo
        with open(LOCAL_RPZ_FILE, 'wb') as f:
            f.write(response.content)
        logger.info(f"Arquivo RPZ baixado e salvo como {LOCAL_RPZ_FILE}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao baixar arquivo RPZ: {e}")
        raise

def get_local_hash():
    """Calcula o hash do arquivo RPZ local."""
    try:
        if not os.path.exists(LOCAL_RPZ_FILE):
            return None
        with open(LOCAL_RPZ_FILE, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except IOError as e:
        logger.error(f"Erro ao ler arquivo local: {e}")
        return None

def restart_bind():
    """Reinicia o serviço BIND9."""
    try:
        # Verifica a sintaxe da configuração antes de reiniciar
        check_result = subprocess.run(
            ["named-checkzone", "rpz.local", LOCAL_RPZ_FILE],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(f"Verificação de zona: {check_result.stdout}")
        
        # Reinicia o serviço
        result = subprocess.run(
            ["systemctl", "restart", "bind9"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("BIND9 reiniciado com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao reiniciar BIND9: {e.stderr}")
        return False

def update_rpz():
    """Verifica e atualiza o arquivo RPZ local se necessário."""
    try:
        ensure_directories()
        server_hash = get_rpz_hash()
        local_hash = get_local_hash()
        
        if local_hash != server_hash:
            logger.info("Arquivo RPZ desatualizado. Baixando nova versão...")
            download_rpz_zone()
            if restart_bind():
                logger.info("Atualização concluída com sucesso")
            else:
                logger.error("Falha ao reiniciar o BIND9 após atualização")
        else:
            logger.info("Arquivo RPZ local está atualizado")
    except Exception as e:
        logger.error(f"Erro durante atualização: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente para servidor de zona RPZ")
    parser.add_argument('--force', action='store_true', help="Força o download do arquivo RPZ")
    args = parser.parse_args()

    try:
        if args.force:
            logger.info("Forçando download do arquivo RPZ...")
            ensure_directories()
            download_rpz_zone()
            restart_bind()
        else:
            update_rpz()
    except Exception as e:
        logger.error(f"Erro na execução do script: {e}")
        exit(1)