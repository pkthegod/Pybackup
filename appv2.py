# app.py
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyQuery
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import hashlib
import os
import time
import logging
import logging.handlers
import bcrypt
import ipaddress
import threading
from datetime import datetime
import redis
from dotenv import load_dotenv
from prometheus_client import Counter, Histogram, start_http_server
import uvicorn
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Carregar variáveis de ambiente
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
    def __init__(self, config: Config, redis_client: redis.Redis):
        self.config = config
        self.redis_client = redis_client
        self.allowed_ips = set()
        self.last_modified_time = 0
        self._setup_logging()
        self._start_whitelist_watcher()
    
    def _setup_logging(self):
        os.makedirs(os.path.dirname(self.config.LOG_FILE), exist_ok=True)
        
        log_handler = logging.handlers.RotatingFileHandler(
            self.config.LOG_FILE,
            maxBytes=10485760,
            backupCount=5
        )
        log_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
        )
        self.logger = logging.getLogger('security_manager')
        self.logger.addHandler(log_handler)
        self.logger.setLevel(logging.INFO)

    def _start_whitelist_watcher(self):
        self.whitelist_thread = threading.Thread(
            target=self._whitelist_watcher,
            daemon=True
        )
        self.whitelist_thread.start()

    def _whitelist_watcher(self):
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
        try:
            with open(self.config.WHITELIST_FILE, 'r') as file:
                self.allowed_ips = {
                    line.strip() for line in file 
                    if line.strip() and not line.startswith('#')
                }
        except Exception as e:
            self.logger.error(f"Erro ao carregar whitelist: {str(e)}")
            self.allowed_ips = set()

    def is_ip_allowed(self, ip: str) -> bool:
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

# Esquemas Pydantic
class ErrorResponse(BaseModel):
    error: str

class HashResponse(BaseModel):
    hash: str

# Middleware de segurança
class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, security_manager: SecurityManager):
        super().__init__(app)
        self.security_manager = security_manager

    async def dispatch(self, request: Request, call_next):
        # Registra tempo inicial
        request.state.start_time = time.time()
        
        # Verifica IP
        client_ip = request.headers.get('X-Real-IP') or request.client.host
        if not self.security_manager.is_ip_allowed(client_ip):
            self.security_manager.logger.warning(f"Acesso bloqueado para IP: {client_ip}")
            return JSONResponse(
                status_code=403,
                content={"error": "IP não autorizado"}
            )

        # Processa a requisição
        try:
            response = await call_next(request)
        except Exception as e:
            self.security_manager.logger.error(f"Erro não tratado: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": "Erro interno do servidor"}
            )

        # Métricas e headers de segurança
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        latency = time.time() - request.state.start_time
        REQUEST_LATENCY.observe(latency)
        
        response.headers.update({
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
        })
        
        return response

def create_app():
    # Configuração inicial
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
    
    # Configuração do FastAPI
    app = FastAPI(
        title="RPZ Zone API",
        description="API para acesso a zonas RPZ",
        version="1.0.0"
    )
    
    # Configuração do rate limiter
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityMiddleware, security_manager=security_manager)
    
    # Configuração da autenticação
    api_key_query = APIKeyQuery(name="auth_token", auto_error=False)
    
    async def verify_api_key(api_key: str = Depends(api_key_query)):
        if not security_manager.verify_api_key(api_key):
            raise HTTPException(
                status_code=401,
                detail="API key inválida"
            )
        return api_key

    @app.get(
        "/rpz_zone",
        response_class=FileResponse,
        dependencies=[Depends(verify_api_key)]
    )
    @limiter.limit("10/minute")
    async def get_rpz_zone(request: Request):
        """Endpoint para obter zona RPZ"""
        try:
            if not os.path.exists(config.RPZ_FILE):
                raise HTTPException(status_code=404, detail="Arquivo RPZ não encontrado")
            
            return FileResponse(
                config.RPZ_FILE,
                media_type='text/plain',
                filename=f"rpz_zone_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
        except HTTPException:
            raise
        except Exception as e:
            security_manager.logger.error(f"Erro ao servir arquivo RPZ: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")

    @app.get(
        "/rpz_hash",
        response_model=HashResponse,
        dependencies=[Depends(verify_api_key)]
    )
    @limiter.limit("30/minute")
    async def get_rpz_hash(request: Request):
        """Endpoint para obter hash da zona RPZ"""
        try:
            if not os.path.exists(config.RPZ_FILE):
                raise HTTPException(status_code=404, detail="Arquivo RPZ não encontrado")
            
            with open(config.RPZ_FILE, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            
            return {"hash": file_hash}
        except HTTPException:
            raise
        except Exception as e:
            security_manager.logger.error(f"Erro ao calcular hash: {str(e)}")
            raise HTTPException(status_code=500, detail="Erro interno do servidor")

    return app

app = create_app()

if __name__ == "__main__":
    # Inicia servidor de métricas do Prometheus
    start_http_server(8000)
    
    # Inicia a aplicação
    uvicorn.run(
        app,
        host="192.168.50.75",
        port=5101,
        workers=4,
        limit_max_requests=100,
        timeout_keep_alive=30,
        access_log=True
    )