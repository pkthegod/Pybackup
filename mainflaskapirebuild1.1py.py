from flask import Flask
from flask_caching import Cache
from pathlib import Path
import sys
import logging
import redis
from typing import Optional, Any

class CacheManager:
    """Gerenciador de cache para a API RPZ"""
    
    def __init__(self, app: Flask, config: 'AppConfig'):
        self.app = app
        self.config = config
        self.cache = self._initialize_cache()
        self._verify_redis_connection()
    
    def _initialize_cache(self) -> Cache:
        """Inicializa o sistema de cache com Redis"""
        cache_config = {
            'CACHE_TYPE': 'redis',
            'CACHE_REDIS_URL': self.config.redis_url,
            'CACHE_DEFAULT_TIMEOUT': self.config.cache_timeout,
            'CACHE_KEY_PREFIX': 'rpz_api:',
            'CACHE_OPTIONS': {
                'socket_timeout': 10,
                'socket_connect_timeout': 10,
                'retry_on_timeout': True
            }
        }
        
        cache = Cache(self.app, config=cache_config)
        return cache
    
    def _verify_redis_connection(self):
        """Verifica a conexão com Redis"""
        try:
            redis_client = redis.from_url(self.config.redis_url)
            redis_client.ping()
        except redis.ConnectionError as e:
            logging.error(f"Erro ao conectar ao Redis: {e}")
            raise SystemExit("Não foi possível conectar ao Redis. Verifique se o servidor está rodando.")

class RPZApi:
    def __init__(self, config: 'AppConfig'):
        """
        Inicializa a API RPZ com a configuração fornecida
        
        Args:
            config: Instância de AppConfig com as configurações
        """
        self.config = config
        self.app = Flask(__name__)
        
        try:
            # Valida a configuração
            self.config.validate()
            
            # Configura o logger primeiro
            self.setup_logging()
            
            # Configura o cache
            self.cache_manager = self._setup_cache()
            
            # Configura rate limiting
            self.setup_rate_limiting()
            
            # Inicializa outras configurações
            self.init_app()
            
        except Exception as e:
            logging.critical(f"Erro na inicialização: {e}")
            sys.exit(1)
    
    def _setup_cache(self) -> CacheManager:
        """
        Configura o sistema de cache
        Returns:
            CacheManager: Instância do gerenciador de cache
        """
        try:
            return CacheManager(self.app, self.config)
        except Exception as e:
            logging.critical(f"Erro ao configurar cache: {e}")
            raise
    
    # Exemplo de uso do cache em uma rota
    def setup_routes(self):
        @self.app.route('/rpz/data/<key>')
        @self.cache_manager.cache.cached(timeout=300)  # 5 minutos
        def get_rpz_data(key):
            # Lógica para buscar dados
            return {'data': 'exemplo'}
        
        @self.app.route('/rpz/status')
        @self.cache_manager.cache.cached(timeout=60)  # 1 minuto
        def get_status():
            # Lógica para status
            return {'status': 'ok'}

def main():
    try:
        # Importações necessárias
        from flask_caching import Cache
        from waitress import serve
        
        # Carrega configuração do ambiente
        config = AppConfig.from_env()
        
        # Cria instância da API
        api = RPZApi(config)
        
        # Log das configurações carregadas
        logging.info(f"Configurações carregadas: {config.to_dict()}")
        
        # Inicia a aplicação
        serve(
            api.app,
            host=config.host,
            port=config.port,
            threads=4,
            url_scheme='http'
        )
    
    except ImportError as e:
        logging.critical(f"Erro de importação: {e}. Certifique-se de que todas as dependências estão instaladas.")
        print("\nPara instalar as dependências necessárias, execute:")
        print("pip install flask-caching redis")
        sys.exit(1)
    except Exception as e:
        logging.critical(f"Erro fatal: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()