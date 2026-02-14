import requests
import hashlib
import os
import argparse
import subprocess
import logging
from dotenv import load_dotenv

# Carrega as variáveis de ambiente de um arquivo .env
load_dotenv()

# Configurações
API_URL = os.getenv('API_URL', 'https://api.procyon.tec.br')
API_KEY = os.getenv('API_KEY')
LOCAL_RPZ_FILE = '/etc/bind/rpz/db.rpz.zone.hosts'

# Configura logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_rpz_hash(api_url, api_key):
    """Obtém o hash do arquivo RPZ do servidor."""
    try:
        response = requests.get(f"{api_url}/rpz_hash", headers={'X-API-Key': api_key})
        response.raise_for_status()
        return response.json()['hash']
    except requests.RequestException as e:
        logging.error(f"Erro ao acessar o servidor: {e}")
        return None

def download_rpz_zone(api_url, api_key, local_file):
    """Baixa o arquivo de zona RPZ do servidor."""
    try:
        response = requests.get(f"{api_url}/rpz_zone", headers={'X-API-Key': api_key})
        response.raise_for_status()
        with open(local_file, 'wb') as f:
            f.write(response.content)
        logging.info(f"Arquivo RPZ baixado e salvo como {local_file}")
    except requests.RequestException as e:
        logging.error(f"Erro ao baixar o arquivo RPZ: {e}")

def get_local_hash(local_file):
    """Calcula o hash do arquivo RPZ local."""
    if not os.path.exists(local_file):
        return None
    with open(local_file, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def update_rpz(api_url, api_key, local_file):
    """Verifica e atualiza o arquivo RPZ local se necessário."""
    server_hash = get_rpz_hash(api_url, api_key)
    if server_hash is None:
        return

    local_hash = get_local_hash(local_file)

    if local_hash != server_hash:
        logging.info("Arquivo RPZ desatualizado. Baixando nova versão...")
        download_rpz_zone(api_url, api_key, local_file)
        restart_bind()  # Reinicia o BIND9 após o download
    else:
        logging.info("Arquivo RPZ local está atualizado.")

def restart_bind():
    """Reinicia o serviço BIND9."""
    try:
        result = subprocess.run(["systemctl", "restart", "bind9"], check=True, capture_output=True)
        logging.info(f"BIND9 reiniciado com sucesso. Saída: {result.stdout.decode()}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro ao reiniciar o BIND9: {e.stderr.decode()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente para servidor de zona RPZ")
    parser.add_argument('--force', action='store_true', help="Força o download do arquivo RPZ")
    parser.add_argument('--api-url', default=API_URL, help="URL do servidor API")
    parser.add_argument('--api-key', default=API_KEY, help="Chave API")
    args = parser.parse_args()

    if not args.api_key:
        raise ValueError("API_KEY não definida. Configure-a no arquivo .env")

    if not args.api_url:
        raise ValueError("API_URL não definida. Configure-a no arquivo .env")

    if not os.path.isdir(os.path.dirname(LOCAL_RPZ_FILE)):
        raise ValueError(f"Diretório {os.path.dirname(LOCAL_RPZ_FILE)} não existe.")

    if args.force:
        logging.info("Forçando download do arquivo RPZ...")
        download_rpz_zone(args.api_url, args.api_key, LOCAL_RPZ_FILE)
        restart_bind()  # Reinicia o BIND9 após o download
    else:
        update_rpz(args.api_url, args.api_key, LOCAL_RPZ_FILE)