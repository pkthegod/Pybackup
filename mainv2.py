from flask import Flask, request, jsonify, send_file, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
from datetime import datetime, timedelta
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
from typing import Optional, Callable
import secrets
from dataclasses import dataclass
from prometheus_client import Counter, Histogram, start_http_server
import uvicorn

# Configuração de Classes e DataClasses
@dataclass
class APIConfig:
    """Classe para configurações da API"""
    api_key_hash: bytes
    rpz_file: str
    whitelist_file: str
    whitelist_reload_interval: int
    redis_host: str
    redis_port: int
    log_file: str
    host: str
    port: int

class SecurityManager:
    """Gerenciador de segurança da API"""
    def __init__(self, config: APIConfig, redis_client: redis.Redis):
        self.config = config
        self.redis_client = redis_client
        self.allowed_ips = set()
        self.last_modified_time = 0
        self._setup_logging()
        self._start_whitelist_watcher()

    def _setup_logging(self) -> None:
        """Configuração do sistema de logging"""
        log_handler = logging.handlers.RotatingFileHandler(
            self.config.log_file,
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        log_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
        )
        self.logger = logging.getLogger('security_manager')
        self.logger.addHandler(log_handler)
        self.logger.setLevel(logging.INFO)

    def _start_whitelist_watcher(self) -> None:
        """Inicia o monitor de alterações na whitelist"""
        self.whitelist_thread = threading.Thread(
            target=self._whitelist_watcher,
            daemon=True
        )
        self.whitelist_thread.start()

    def _whitelist_watcher(self) -> None:
        """Monitora alterações no arquivo de whitelist"""
        while True:
            try:
                current_modified_time = os.path.getmtime(self.config.whitelist_file)
                if current_modified_time > self.last_modified_time:
                    self._load_whitelist()
                    self.last_modified_time = current_modified_time
                    self.logger.info("Whitelist recarregada com sucesso")
            except Exception as e:
                self.logger.error(f"Erro ao recarregar whitelist: {str(e)}")
            time.sleep(self.config.whitelist_reload_interval)

    def _load_whitelist(self) -> None:
        """Carrega a whitelist do arquivo"""
        try:
            with open(self.config.whitelist_file, 'r') as file:
                self.allowed_ips = {
                    line.strip() for line in file 
                    if line.strip() and not line.startswith('#')
                }
        except Exception as e:
            self.logger.error(f"Erro ao carregar whitelist: {str(e)}")
            self.allowed_ips = set()

    def is_ip_allowed(self, ip: str) -> bool:
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

    def verify_api_key(self, api_key: str) -> bool:
        """Verifica se a API key é válida"""
        if not api_key:
            return False
        
        # Adiciona rate limiting por API key
        rate_limit_key = f"rate_limit:{api_key}"
        current_count = self.redis_client.get(rate_limit_key)
        
        if current_count and int(current_count) > 1000:  # Limite de 1000 requisições por hora
            self.logger.warning(f"Rate limit excedido para API key: {api_key}")
            return False
            
        self.redis_client.incr(rate_limit_key)
        self.redis_client.expire(rate_limit_key, 3600)  # Expira em 1 hora
        
        try:
            return bcrypt.checkpw(
                api_key.encode('utf-8'),
                self.config.api_key_hash
            )
        except Exception as e:
            self.logger.error(f"Erro na verificação da API key: {str(e)}")
            return False

# Métricas Prometheus
REQUEST_COUNT = Counter('http_requests_total', 'Total de requisições HTTP', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'Duração das requisições HTTP')

def create_app() -> Flask:
    """Função factory para criar a aplicação Flask"""
    app = Flask(__name__)
    
    # Carrega configurações do ambiente
    load_dotenv()
    
    config = APIConfig(
        api_key_hash=os.getenv('API_KEY_HASH').encode(),
        rpz_file=os.getenv('RPZ_FILE', 'db.rpz.zone.hosts'),
        whitelist_file=os.getenv('WHITELIST_FILE', 'whitelist.txt'),
        whitelist_reload_interval=int(os.getenv('WHITELIST_RELOAD_INTERVAL', 30)),
        redis_host=os.getenv('REDIS_HOST', 'localhost'),
        redis_port=int(os.getenv('REDIS_PORT', 6379)),
        log_file=os.getenv('LOG_FILE', '/var/log/api.log'),
        host=os.getenv('API_HOST', '0.0.0.0'),
        port=int(os.getenv('API_PORT', 5101))
    )
    
    # Inicializa Redis com retry e pool de conexões
    redis_client = redis.Redis(
        host=config.redis_host,
        port=config.redis_port,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30,
        connection_pool=redis.ConnectionPool(
            max_connections=10,
            host=config.redis_host,
            port=config.redis_port
        )
    )
    
    # Inicializa o gerenciador de segurança
    security_manager = SecurityManager(config, redis_client)
    
    # Configuração do rate limiter
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=f"redis://{config.redis_host}:{config.redis_port}",
        strategy="fixed-window-elastic-expiry"
    )
    
    def require_api_key(f: Callable) -> Callable:
        """Decorator para verificar API key"""
        @wraps(f)
        def decorated(*args, **kwargs):
            api_key = request.args.get('auth_token')
            if not security_manager.verify_api_key(api_key):
                security_manager.logger.warning(f"Tentativa de acesso com API key inválida: {api_key}")
                return jsonify({'error': 'API key inválida'}), 401
            return f(*args, **kwargs)
        return decorated

    @app.before_request
    def before_request() -> Optional[tuple]:
        """Middleware para verificar IP e registrar métricas"""
        # Inicia timer para métricas
        request.start_time = time.time()
        
        # Verifica IP
        client_ip = request.headers.get('X-Real-IP') or request.remote_addr
        if not security_manager.is_ip_allowed(client_ip):
            security_manager.logger.warning(f"Acesso bloqueado para IP: {client_ip}")
            return jsonify({'error': 'IP não autorizado'}), 403

    @app.after_request
    def after_request(response):
        """Middleware para finalizar métricas"""
        # Registra métricas
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.endpoint,
            status=response.status_code
        ).inc()
        
        # Registra latência
        latency = time.time() - request.start_time
        REQUEST_LATENCY.observe(latency)
        
        # Adiciona headers de segurança
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response

    @app.route("/rpz_zone", methods=['GET'])
    @limiter.limit("10/minute")
    @require_api_key
    def get_rpz_zone():
        """Endpoint para obter zona RPZ"""
        try:
            if not os.path.exists(config.rpz_file):
                return jsonify({'error': 'Arquivo RPZ não encontrado'}), 404
            
            return send_file(
                config.rpz_file,
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
            if not os.path.exists(config.rpz_file):
                return jsonify({'error': 'Arquivo RPZ não encontrado'}), 404
            
            with open(config.rpz_file, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            return jsonify({"hash": file_hash})
        except Exception as e:
            security_manager.logger.error(f"Erro ao calcular hash: {str(e)}")
            return jsonify({'error': 'Erro interno do servidor'}), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handler global de exceções"""
        security_manager.logger.error(f"Erro não tratado: {str(e)}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

    return app

if __name__ == '__main__':
    # Inicia servidor de métricas do Prometheus
    start_http_server(8000)
    
    # Cria e executa aplicação com uvicorn
    app = create_app()
    uvicorn.run(
        app,
        host=os.getenv('API_HOST', '192.168.50.75'),
        port=int(os.getenv('API_PORT', 5101)),
        workers=4,
        limit_concurrency=100,
        timeout_keep_alive=30,
        access_log=True
    )