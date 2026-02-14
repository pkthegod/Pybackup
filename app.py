# app.py - Arquivo principal
from flask import Flask, request, jsonify, send_file, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import hashlib
import os
import time
import logging
import logging.handlers
import bcrypt
import ipaddress
import threading
from dotenv import load_dotenv
import redis
from functools import wraps
from datetime import datetime
from prometheus_client import Counter, Histogram, start_http_server

# Configuração inicial
load_dotenv()

class Config:
    API_KEY_HASH = os.getenv('API_KEY_HASH', '').encode()
    RPZ_FILE = os.getenv('RPZ_FILE', 'db.rpz.zone.hosts')
    WHITELIST_FILE = os.getenv('WHITELIST_FILE', 'whitelist.txt')
    WHITELIST_RELOAD_INTERVAL = int(os.getenv('WHITELIST_RELOAD_INTERVAL', 30))
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    LOG_FILE = os.getenv('LOG_FILE', '/var/log/api.log')
    HOST = os.getenv('API_HOST', '0.0.0.0')
    PORT = int(os.getenv('API_PORT', 5101))

class SecurityManager:
    def __init__(self, config, redis_client):
        self.config = config
        self.redis_client = redis_client
        self.allowed_ips = set()
        self.last_modified_time = 0
        self._setup_logging()
        self._start_whitelist_watcher()
    
    def _setup_logging(self):
        """Configuração do sistema de logging"""
        os.makedirs(os.path.dirname(self.config.LOG_FILE), exist_ok=True)
        
        log_handler = logging.handlers.RotatingFileHandler(
            self.config.LOG_FILE,
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        log_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
        )
        self.logger = logging.getLogger('security_manager')
        self.logger.addHandler(log_handler)
        self.logger.setLevel(logging.INFO)

    def _start_whitelist_watcher(self):
        """Inicia o monitor de alterações na whitelist"""
        self.whitelist_thread = threading.Thread(
            target=self._whitelist_watcher,
            daemon=True
        )
        self.whitelist_thread.start()

    def _whitelist_watcher(self):
        """Monitora alterações no arquivo de whitelist"""
        while True:
            try:
                if os.path.exists(self.config.WHITELIST_FILE):
                    current_modified_time = os.path.getmtime(self.config.WHITELIST_FILE)
                    if current_modified_time > self.last_modified_time:
                        self._load_whitelist()
                        self.last_modified_time = current_modified_time
                        self.logger.info("Whitelist recarregada com sucesso")
                else:
                    self.logger.warning(f"Arquivo whitelist não encontrado: {self.config.WHITELIST_FILE}")
                    self.allowed_ips = set()
            except Exception as e:
                self.logger.error(f"Erro ao recarregar whitelist: {str(e)}")
            time.sleep(self.config.WHITELIST_RELOAD_INTERVAL)

    def _load_whitelist(self):
        """Carrega a whitelist do arquivo"""
        try:
            with open(self.config.WHITELIST_FILE, 'r') as file:
                self.allowed_ips = {
                    line.strip() for line in file 
                    if line.strip() and not line.startswith('#')
                }
        except Exception as e:
            self.logger.error(f"Erro ao carregar whitelist: {str(e)}")
            self.allowed_ips = set()

    def is_ip_allowed(self, ip):
        """Verifica se um IP está autorizado"""
        try:
            addr = ipaddress.ip_address(ip)
            return any(
                addr in ipaddress.ip_network(allowed, strict=False)
                for allowed in self.allowed_ips
            )
        except ValueError:
            self.logger.error(f"IP inválido recebido: {ip}")
            return False

    def verify_api_key(self, api_key):
        """Verifica se a API key é válida"""
        if not api_key:
            return False
        
        try:
            return bcrypt.checkpw(
                api_key.encode('utf-8'),
                self.config.API_KEY_HASH
            )
        except Exception as e:
            self.logger.error(f"Erro na verificação da API key: {str(e)}")
            return False

# Métricas Prometheus
REQUEST_COUNT = Counter('http_requests_total', 'Total de requisições HTTP', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'Duração das requisições HTTP')

def create_app():
    """Função factory para criar a aplicação Flask"""
    app = Flask(__name__)
    config = Config()
    
    # Inicializa Redis
    redis_client = redis.Redis(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30
    )
    
    # Inicializa componentes
    security_manager = SecurityManager(config, redis_client)
    
    # Configuração do rate limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}",
        strategy="fixed-window-elastic-expiry"
    )
    
    def require_api_key(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            api_key = request.args.get('auth_token')
            if not security_manager.verify_api_key(api_key):
                security_manager.logger.warning("Tentativa de acesso com API key inválida")
                return jsonify({'error': 'API key inválida'}), 401
            return f(*args, **kwargs)
        return decorated

    @app.before_request
    def before_request():
        request.start_time = time.time()
        client_ip = request.headers.get('X-Real-IP') or request.remote_addr
        if not security_manager.is_ip_allowed(client_ip):
            security_manager.logger.warning(f"Acesso bloqueado para IP: {client_ip}")
            return jsonify({'error': 'IP não autorizado'}), 403

    @app.after_request
    def after_request(response):
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.endpoint,
            status=response.status_code
        ).inc()
        
        latency = time.time() - request.start_time
        REQUEST_LATENCY.observe(latency)
        
        response.headers.update({
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
        })
        
        return response

    @app.route("/rpz_zone", methods=['GET'])
    @limiter.limit("10/minute")
    @require_api_key
    def get_rpz_zone():
        """Endpoint para obter zona RPZ"""
        try:
            if not os.path.exists(config.RPZ_FILE):
                return jsonify({'error': 'Arquivo RPZ não encontrado'}), 404
            
            return send_file(
                config.RPZ_FILE,
                mimetype='text/plain',
                as_attachment=True,
                download_name=f"rpz_zone_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
        except Exception as e:
            security_manager.logger.error(f"Erro ao servir arquivo RPZ: {str(e)}")
            return jsonify({'error': 'Erro interno do servidor'}), 500

    @app.route('/rpz_hash', methods=['GET'])
    @limiter.limit("30/minute")
    @require_api_key
    def get_rpz_hash():
        """Endpoint para obter hash da zona RPZ"""
        try:
            if not os.path.exists(config.RPZ_FILE):
                return jsonify({'error': 'Arquivo RPZ não encontrado'}), 404
            
            with open(config.RPZ_FILE, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            return jsonify({"hash": file_hash})
        except Exception as e:
            security_manager.logger.error(f"Erro ao calcular hash: {str(e)}")
            return jsonify({'error': 'Erro interno do servidor'}), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        security_manager.logger.error(f"Erro não tratado: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

    return app

app = create_app()

if __name__ == "__main__":
    # Inicia servidor de métricas do Prometheus
    start_http_server(8000)
    
    # Inicia a aplicação
    import uvicorn
    uvicorn.run(
        app,
        host="192.168.50.75",
        port=5101,
        workers=4,
        limit_concurrency=100,
        timeout_keep_alive=30,
        access_log=True
    )