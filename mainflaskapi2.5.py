from flask import Flask, request, jsonify, send_file, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import hashlib
import os
import time
import logging
from functools import wraps
import bcrypt
import ipaddress
import threading
from dotenv import load_dotenv

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carrega as variáveis de ambiente
load_dotenv()
API_KEY_PLAIN = os.getenv('API_KEY')

if not API_KEY_PLAIN:
    logging.critical("API_KEY não definida nas variáveis de ambiente.")
    raise ValueError("API_KEY não definida.")

# Gera o hash da chave de API uma vez
API_KEY_HASH = bcrypt.hashpw(API_KEY_PLAIN.encode('utf-8'), bcrypt.gensalt())

RPZ_FILE = 'db.rpz.zone.hosts'
WHITELIST_FILE = 'whitelist.txt'
WHITELIST_RELOAD_INTERVAL = 60

allowed_ips = []
last_modified_time = 0

# Carregar e monitorar whitelist
def load_whitelist():
    global allowed_ips, last_modified_time
    try:
        current_modified_time = os.path.getmtime(WHITELIST_FILE)
        if current_modified_time > last_modified_time:
            with open(WHITELIST_FILE, 'r') as file:
                allowed_ips = [line.strip() for line in file if line.strip() and not line.startswith('#')]
            last_modified_time = current_modified_time
            logging.info("Whitelist recarregada.")
    except FileNotFoundError:
        logging.error(f"Arquivo de whitelist '{WHITELIST_FILE}' não encontrado.")
        allowed_ips = []

def whitelist_watcher():
    while True:
        load_whitelist()
        time.sleep(WHITELIST_RELOAD_INTERVAL)

# Inicia o monitoramento da whitelist
threading.Thread(target=whitelist_watcher, daemon=True).start()

# Função para verificar IP permitido
def is_ip_allowed(ip):
    try:
        addr = ipaddress.ip_address(ip)
        for allowed in allowed_ips:
            try:
                network = ipaddress.ip_network(allowed, strict=False)
                if addr in network:
                    return True
            except ValueError:
                if addr == ipaddress.ip_address(allowed):
                    return True
        return False
    except ValueError:
        return False

@app.before_request
def check_ip():
    client_ip = get_client_ip()
    logging.info(f"Requisição recebida de: {client_ip}")

    if not is_ip_allowed(client_ip):
        logging.warning(f"Acesso não autorizado de: {client_ip}")
        abort(403)

# Limitar o número de requisições por minuto
limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="redis://localhost:6379"
)

@app.route("/")
@limiter.limit("5 per minute")
def index():
    return "OK!"

# Função para exigir API key usando bcrypt
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get('X-API-Key')
        if not provided_key or not bcrypt.checkpw(provided_key.encode('utf-8'), API_KEY_HASH):
            logging.warning(f"API key inválida fornecida: {provided_key}")
            abort(401)
        return f(*args, **kwargs)
    return decorated_function

# Função para obter o IP do cliente
def get_client_ip():
    return request.headers.get('X-Real-IP') or request.remote_addr

@app.errorhandler(403)
def forbidden(e):
    return jsonify(error="Acesso não autorizado"), 403

@app.errorhandler(401)
def unauthorized(e):
    return jsonify(error="API key inválida"), 401

# Rota para baixar o arquivo RPZ
@app.route('/rpz_zone', methods=['GET'])
@require_api_key
@limiter.limit("10/minute")
def get_rpz_zone():
    if not os.path.exists(RPZ_FILE):
        abort(404)
    return send_file(RPZ_FILE, mimetype='text/plain')

# Rota para obter o hash do arquivo RPZ
@app.route('/rpz_hash', methods=['GET'])
@require_api_key
@limiter.limit("30/minute")
def get_rpz_hash():
    if not os.path.exists(RPZ_FILE):
        abort(404)
    with open(RPZ_FILE, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()
    return jsonify({"hash": file_hash})

# Teste para verificar o IP do cliente
@app.route('/test-ip', methods=['GET'])
def test_ip():
    return jsonify({
        "client_ip": get_client_ip(),
        "remote_addr": request.remote_addr,
        "x_forwarded_for": request.headers.get('X-Forwarded-For')
    })

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='192.168.50.75', port=5101)