from flask import Flask, request, jsonify, send_file, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import hashlib
import os
import logging
from functools import wraps
import redis
import bcrypt
import ipaddress

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Simples ACL - você deve expandir isso para maior segurança
# Lista de IPs/CIDRs permitidos
ALLOWED_IPS = [
    '127.0.0.1',
    '::1',
    '45.190.251.2',
    '179.127.248.0/21',
    '200.0.179.91',
    '201.182.39.130'  # Exemplo de CIDR
]

RPZ_FILE = 'db.rpz.zone.hosts'  # Nome do arquivo RPZ
API_KEY_PLAIN = os.environ.get('API_KEY', 'default_key')  # Use uma variável de ambiente para a chave API
API_KEY_HASH = bcrypt.hashpw(API_KEY_PLAIN.encode('utf-8'), bcrypt.gensalt())

limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri="redis://localhost:6379"
)

@app.route("/")
@limiter.limit("5 per minute")
def index():
    return "Bem-vindo!"

def is_ip_allowed(ip):
    try:
        addr = ipaddress.ip_address(ip)
        for allowed in ALLOWED_IPS:
            if isinstance(ipaddress.ip_network(allowed, strict=False), ipaddress.IPv4Network):
                if addr in ipaddress.ip_network(allowed, strict=False):
                    return True
            elif ip == allowed:
                return True
        return False
    except ValueError:
        return False

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get('X-API-Key')
        if not provided_key or not bcrypt.checkpw(provided_key.encode('utf-8'), API_KEY_HASH):
            abort(401)
        return f(*args, **kwargs)
    return decorated_function

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers.get('X-API-Key') != API_KEY:
            abort(401)
        return f(*args, **kwargs)
    return decorated_function

def get_client_ip():
    return request.headers.get('X-Real-IP') or request.remote_addr

@app.before_request
def check_ip():
    client_ip = get_client_ip()
    logging.info(f"Requisição recebida de: {client_ip}")
    if client_ip not in ALLOWED_IPS:
        logging.warning(f"Acesso não autorizado de: {client_ip}")
        abort(403)

@app.errorhandler(403)
def forbidden(e):
    return jsonify(error="Acesso não autorizado"), 403

@app.errorhandler(401)
def unauthorized(e):
    return jsonify(error="API key inválida"), 401

@app.route('/rpz_zone', methods=['GET'])
@require_api_key
@limiter.limit("10/minute")
def get_rpz_zone():
    if not os.path.exists(RPZ_FILE):
        abort(404)
    return send_file(RPZ_FILE, mimetype='text/plain')

@app.route('/rpz_hash', methods=['GET'])
@require_api_key
@limiter.limit("30/minute")
def get_rpz_hash():
    if not os.path.exists(RPZ_FILE):
        abort(404)
    with open(RPZ_FILE, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()
    return jsonify({"hash": file_hash})

# Teste para checar se o IP real está chegando até a API
#@app.route('/test-ip', methods=['GET'])
#def test_ip():
#    return jsonify({
#        "client_ip": get_client_ip(),
#        "remote_addr": request.remote_addr,
#        "x_forwarded_for": request.headers.get('X-Forwarded-For')
#    })

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='192.168.50.75', port=5101)