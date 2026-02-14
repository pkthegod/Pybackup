from flask import Flask, request, jsonify, send_file, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from dataclasses import dataclass
from typing import List, Optional
import hashlib
import os
import time
import logging
import logging.handlers
import bcrypt
import ipaddress
import threading
from pathlib import Path
from dotenv import load_dotenv
from functools import wraps

@dataclass
class AppConfig:
    """Application configuration class"""
    rpz_file: Path
    whitelist_file: Path
    whitelist_reload_interval: int
    redis_url: str
    host: str
    port: int
    log_file: Path
    log_level: str

class RPZApi:
    def __init__(self, config: AppConfig):
        self.config = config
        self.app = Flask(__name__)
        self.setup_logging()
        self.setup_cache()
        self.setup_rate_limiter()
        self.allowed_ips = []
        self.last_modified_time = 0
        self.api_key_hash = self._initialize_api_key()
        self._setup_routes()
        
    def setup_logging(self):
        """Configure application logging"""
        log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.config.log_file,
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(log_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.log_level.upper()))
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    def setup_cache(self):
        """Initialize Flask-Cache"""
        self.cache = Cache(self.app, config={
            'CACHE_TYPE': 'redis',
            'CACHE_REDIS_URL': self.config.redis_url,
            'CACHE_DEFAULT_TIMEOUT': 300
        })

    def setup_rate_limiter(self):
        """Initialize rate limiter"""
        self.limiter = Limiter(
            get_remote_address,
            app=self.app,
            storage_uri=self.config.redis_url,
            default_limits=["200 per day", "50 per hour"]
        )

    def _initialize_api_key(self) -> bytes:
        """Initialize API key from environment"""
        api_key = os.getenv('API_KEY')
        if not api_key:
            raise ValueError("API_KEY não definida nas variáveis de ambiente.")
        return bcrypt.hashpw(api_key.encode('utf-8'), bcrypt.gensalt())

    def require_api_key(self, f):
        """Decorator to require API key"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            provided_key = request.headers.get('X-API-Key')
            if not provided_key or not bcrypt.checkpw(provided_key.encode('utf-8'), self.api_key_hash):
                logging.warning(f"Tentativa de acesso com API key inválida de {self.get_client_ip()}")
                abort(401)
            return f(*args, **kwargs)
        return decorated_function

    def load_whitelist(self):
        """Load and validate whitelist entries"""
        try:
            current_modified_time = os.path.getmtime(self.config.whitelist_file)
            if current_modified_time > self.last_modified_time:
                with open(self.config.whitelist_file, 'r') as file:
                    self.allowed_ips = []
                    for line in file:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            try:
                                # Validate IP/Network before adding
                                ipaddress.ip_network(line, strict=False)
                                self.allowed_ips.append(line)
                            except ValueError as e:
                                logging.error(f"Invalid whitelist entry: {line} - {str(e)}")
                
                self.last_modified_time = current_modified_time
                logging.info(f"Whitelist recarregada com {len(self.allowed_ips)} entradas válidas")
        except FileNotFoundError:
            logging.error(f"Arquivo de whitelist '{self.config.whitelist_file}' não encontrado")
            self.allowed_ips = []

    def whitelist_watcher(self):
        """Monitor whitelist file for changes"""
        while True:
            try:
                self.load_whitelist()
                time.sleep(self.config.whitelist_reload_interval)
            except Exception as e:
                logging.error(f"Erro no monitoramento da whitelist: {str(e)}")
                time.sleep(10)  # Retry delay

    def is_ip_allowed(self, ip: str) -> bool:
        """Check if IP is allowed"""
        try:
            addr = ipaddress.ip_address(ip)
            return any(addr in ipaddress.ip_network(allowed, strict=False) 
                      for allowed in self.allowed_ips)
        except ValueError:
            return False

    def get_client_ip(self) -> str:
        """Get client IP with proper header checking"""
        if request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        elif request.headers.get('X-Forwarded-For'):
            # Get the first IP in X-Forwarded-For chain
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        return request.remote_addr

    @cache.memoize(timeout=300)
    def calculate_rpz_hash(self) -> str:
        """Calculate RPZ file hash with caching"""
        try:
            with open(self.config.rpz_file, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except FileNotFoundError:
            logging.error(f"Arquivo RPZ não encontrado: {self.config.rpz_file}")
            abort(404)
        except Exception as e:
            logging.error(f"Erro ao calcular hash do arquivo RPZ: {str(e)}")
            abort(500)

    def _setup_routes(self):
        """Setup Flask routes"""
        @self.app.before_request
        def check_ip():
            client_ip = self.get_client_ip()
            logging.info(f"Requisição recebida de: {client_ip}")
            if not self.is_ip_allowed(client_ip):
                logging.warning(f"Acesso não autorizado de: {client_ip}")
                abort(403)

        @self.app.route("/health")
        @self.limiter.limit("5 per minute")
        def health_check():
            return jsonify({
                "status": "healthy",
                "whitelist_entries": len(self.allowed_ips),
                "rpz_file_exists": os.path.exists(self.config.rpz_file)
            })

        @self.app.route('/rpz_zone')
        @self.require_api_key
        @self.limiter.limit("10/minute")
        def get_rpz_zone():
            try:
                return send_file(
                    self.config.rpz_file,
                    mimetype='text/plain',
                    as_attachment=True,
                    download_name='db.rpz.zone.hosts'
                )
            except FileNotFoundError:
                abort(404)
            except Exception as e:
                logging.error(f"Erro ao enviar arquivo RPZ: {str(e)}")
                abort(500)

        @self.app.route('/rpz_hash')
        @self.require_api_key
        @self.limiter.limit("30/minute")
        def get_rpz_hash():
            return jsonify({"hash": self.calculate_rpz_hash()})

        @self.app.errorhandler(403)
        def forbidden(e):
            return jsonify(error="Acesso não autorizado"), 403

        @self.app.errorhandler(401)
        def unauthorized(e):
            return jsonify(error="API key inválida"), 401

        @self.app.errorhandler(500)
        def internal_error(e):
            return jsonify(error="Erro interno do servidor"), 500

    def run(self):
        """Run the application"""
        # Start whitelist watcher thread
        threading.Thread(
            target=self.whitelist_watcher,
            daemon=True,
            name="WhitelistWatcher"
        ).start()

        # Run with production server
        from waitress import serve
        serve(self.app, host=self.config.host, port=self.config.port)

def main():
    # Load environment variables
    load_dotenv()
    
    # Application configuration
    config = AppConfig(
        rpz_file=Path('db.rpz.zone.hosts'),
        whitelist_file=Path('whitelist.txt'),
        whitelist_reload_interval=60,
        redis_url="redis://localhost:6379",
        host='192.168.50.75',
        port=5101,
        log_file=Path('rpz_api.log'),
        log_level='INFO'
    )
    
    # Initialize and run application
    api = RPZApi(config)
    api.run()

if __name__ == '__main__':
    main()