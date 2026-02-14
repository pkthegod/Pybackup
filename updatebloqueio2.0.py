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
API_URL = "https://api.procyon.tec.br"  # Ajuste para o endereço correto do seu servidor
API_KEY = os.getenv('API_KEY')  # A chave API será carregada de uma variável de ambiente
LOCAL_RPZ_FILE = "/etc/bind/rpz/db.rpz.zone.hosts"

# Configura logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_rpz_hash():
    """Obtém o hash do arquivo RPZ do servidor."""
    response = requests.get(f"{API_URL}/rpz_hash", headers={'X-API-Key': API_KEY})
    response.raise_for_status()
    return response.json()['hash']

def download_rpz_zone():
    """Baixa o arquivo de zona RPZ do servidor."""
    response = requests.get(f"{API_URL}/rpz_zone", headers={'X-API-Key': API_KEY})
    response.raise_for_status()
    with open(LOCAL_RPZ_FILE, 'wb') as f:
        f.write(response.content)
    print(f"Arquivo RPZ baixado e salvo como {LOCAL_RPZ_FILE}")

def get_local_hash():
    """Calcula o hash do arquivo RPZ local."""
    if not os.path.exists(LOCAL_RPZ_FILE):
        return None
    with open(LOCAL_RPZ_FILE, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def update_rpz():
    """Verifica e atualiza o arquivo RPZ local se necessário."""
    try:
        server_hash = get_rpz_hash()
        local_hash = get_local_hash()

        if local_hash != server_hash:
            print("Arquivo RPZ desatualizado. Baixando nova versão...")
            download_rpz_zone()
            restart_bind()  # Reinicia o BIND9 após o download
        else:
            print("Arquivo RPZ local está atualizado.")
    except requests.RequestException as e:
        print(f"Erro ao acessar o servidor: {e}")

def restart_bind():
    """Reinicia o serviço BIND9."""
    try:
        # Reinicia o serviço BIND9 usando systemctl
        result = subprocess.run(["systemctl", "restart", "bind9"], check=True, capture_output=True)
        logging.info(f"BIND9 reiniciado com sucesso. Saída: {result.stdout.decode()}")
        print("BIND9 reiniciado com sucesso.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro ao reiniciar o BIND9: {e.stderr.decode()}")
        print(f"Erro ao reiniciar o BIND9: {e.stderr.decode()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente para servidor de zona RPZ")
    parser.add_argument('--force', action='store_true', help="Força o download do arquivo RPZ")
    args = parser.parse_args()

    if not API_KEY:
        raise ValueError("API_KEY não definida. Configure-a no arquivo .env")

    if args.force:
        print("Forçando download do arquivo RPZ...")
        download_rpz_zone()
        restart_bind()  # Reinicia o BIND9 após o download
    else:
        update_rpz()
