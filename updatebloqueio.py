import requests
import hashlib
import os
import time
import logging
import subprocess
from requests.exceptions import RequestException
from tenacity import retry, stop_after_attempt, wait_exponential

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_URL = "https://api.procyon.tec.br"  # Use HTTPS
LOCAL_FILE = "/etc/bind/rpz/db.rpz.zone.hosts"
BIND_CONFIG = "/etc/bind/named.conf"
API_KEY = os.environ.get('API_KEY', 'default_key')

headers = {
    'X-API-Key': API_KEY
}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def api_request(endpoint):
    response = requests.get(f"{API_URL}/{endpoint}", headers=headers, timeout=10)
    response.raise_for_status()
    return response

def get_local_hash():
    if not os.path.exists(LOCAL_FILE):
        logging.warning(f"Arquivo local não encontrado: {LOCAL_FILE}")
        return None
    return hashlib.md5(open(LOCAL_FILE, 'rb').read()).hexdigest()

def update_file():
    try:
        response = api_request('rpz_zone')
        with open(LOCAL_FILE, 'wb') as f:
            f.write(response.content)
        logging.info("Arquivo db.rpz.zone.hosts atualizado com sucesso.")
        reload_bind()
    except RequestException as e:
        logging.error(f"Erro ao baixar o arquivo: {str(e)}")

def reload_bind():
    try:
        subprocess.run(["rndc", "reload"], check=True, capture_output=True)
        logging.info("BIND9 recarregado com sucesso.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Erro ao recarregar BIND9: {e.stderr.decode()}")

def main():
    while True:
        try:
            local_hash = get_local_hash()
            response = api_request('rpz_hash')
            api_hash = response.json()['hash']
            
            if local_hash != api_hash:
                logging.info("Hash diferente detectado. Atualizando arquivo...")
                update_file()
            else:
                logging.info("Arquivo está atualizado.")
        except Exception as e:
            logging.error(f"Erro inesperado: {str(e)}")
        
        time.sleep(86400)

if __name__ == "__main__":
    main()