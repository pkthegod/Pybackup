# 1. Estrutura Básica do AppConfig

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

@dataclass
class AppConfig:
    """Configuração da aplicação RPZ API"""
    # Arquivos e Diretórios
    rpz_file: Path
    whitelist_file: Path
    log_file: Path
    
    # Configurações de Rede
    host: str
    port: int
    redis_url: str
    
    # Intervalos e Timeouts
    whitelist_reload_interval: int = 60  # segundos
    cache_timeout: int = 300  # segundos
    request_timeout: int = 30  # segundos
    
    # Configurações de Log
    log_level: str = "INFO"
    log_max_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    
    # Rate Limiting
    rate_limit_default: str = "100/minute"
    rate_limit_rpz_download: str = "10/minute"
    
    # Configurações adicionais
    debug: bool = False
    testing: bool = False
    
    # Dicionário para configurações extras
    extra_settings: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """
        Cria uma instância de AppConfig a partir de variáveis de ambiente
        """
        load_dotenv()  # Carrega variáveis do arquivo .env
        
        return cls(
            rpz_file=Path(os.getenv('RPZ_FILE', 'db.rpz.zone.hosts')),
            whitelist_file=Path(os.getenv('WHITELIST_FILE', 'whitelist.txt')),
            log_file=Path(os.getenv('LOG_FILE', 'rpz_api.log')),
            host=os.getenv('HOST', '192.168.50.75'),
            port=int(os.getenv('PORT', '5101')),
            redis_url=os.getenv('REDIS_URL', 'redis://localhost:6379'),
            whitelist_reload_interval=int(os.getenv('WHITELIST_RELOAD_INTERVAL', '60')),
            cache_timeout=int(os.getenv('CACHE_TIMEOUT', '300')),
            request_timeout=int(os.getenv('REQUEST_TIMEOUT', '30')),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            log_max_size=int(os.getenv('LOG_MAX_SIZE', str(10 * 1024 * 1024))),
            log_backup_count=int(os.getenv('LOG_BACKUP_COUNT', '5')),
            rate_limit_default=os.getenv('RATE_LIMIT_DEFAULT', '100/minute'),
            rate_limit_rpz_download=os.getenv('RATE_LIMIT_RPZ_DOWNLOAD', '10/minute'),
            debug=os.getenv('DEBUG', 'false').lower() == 'true',
            testing=os.getenv('TESTING', 'false').lower() == 'true'
        )
    
    def validate(self) -> None:
        """
        Valida a configuração
        Raises:
            ValueError: Se alguma configuração estiver inválida
        """
        # Valida arquivos e diretórios
        if not self.rpz_file.parent.exists():
            raise ValueError(f"Diretório do arquivo RPZ não existe: {self.rpz_file.parent}")
        
        if not self.whitelist_file.exists():
            raise ValueError(f"Arquivo whitelist não existe: {self.whitelist_file}")
            
        # Valida diretório de logs
        log_dir = self.log_file.parent
        if not log_dir.exists():
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ValueError(f"Não foi possível criar diretório de logs: {e}")
        
        # Valida porta
        if not 1 <= self.port <= 65535:
            raise ValueError(f"Porta inválida: {self.port}")
        
        # Valida intervalos
        if self.whitelist_reload_interval < 10:
            raise ValueError("Intervalo de recarga da whitelist muito baixo")
        
        if self.cache_timeout < 60:
            raise ValueError("Cache timeout muito baixo")
            
        # Valida nível de log
        valid_log_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if self.log_level.upper() not in valid_log_levels:
            raise ValueError(f"Nível de log inválido: {self.log_level}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte a configuração para um dicionário
        """
        return {
            'rpz_file': str(self.rpz_file),
            'whitelist_file': str(self.whitelist_file),
            'log_file': str(self.log_file),
            'host': self.host,
            'port': self.port,
            'redis_url': self.redis_url,
            'whitelist_reload_interval': self.whitelist_reload_interval,
            'cache_timeout': self.cache_timeout,
            'request_timeout': self.request_timeout,
            'log_level': self.log_level,
            'log_max_size': self.log_max_size,
            'log_backup_count': self.log_backup_count,
            'rate_limit_default': self.rate_limit_default,
            'rate_limit_rpz_download': self.rate_limit_rpz_download,
            'debug': self.debug,
            'testing': self.testing,
            'extra_settings': self.extra_settings
        }
```

# 2. Exemplo de arquivo .env

```env
# Arquivos e Diretórios
RPZ_FILE=db.rpz.zone.hosts
WHITELIST_FILE=whitelist.txt
LOG_FILE=rpz_api.log

# Configurações de Rede
HOST=192.168.50.75
PORT=5101
REDIS_URL=redis://localhost:6379

# Intervalos e Timeouts
WHITELIST_RELOAD_INTERVAL=60
CACHE_TIMEOUT=300
REQUEST_TIMEOUT=30

# Configurações de Log
LOG_LEVEL=INFO
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5

# Rate Limiting
RATE_LIMIT_DEFAULT=100/minute
RATE_LIMIT_RPZ_DOWNLOAD=10/minute

# Debug e Testing
DEBUG=false
TESTING=false
```

# 3. Implementação na Aplicação Principal

```python
from flask import Flask
from pathlib import Path
import sys
import logging

class RPZApi:
    def __init__(self, config: AppConfig):
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
            
            # Configura o logger
            self.setup_logging()
            
            # Configura o cache
            self.setup_cache()
            
            # Configura rate limiting
            self.setup_rate_limiting()
            
            # Inicializa outras configurações
            self.init_app()
            
        except Exception as e:
            logging.critical(f"Erro na inicialização: {e}")
            sys.exit(1)
    
    def setup_logging(self):
        """Configura o sistema de logging"""
        logging.basicConfig(
            filename=str(self.config.log_file),
            level=getattr(logging, self.config.log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Adiciona handler para console se em modo debug
        if self.config.debug:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            logging.getLogger('').addHandler(console_handler)
    
    def setup_cache(self):
        """Configura o sistema de cache"""
        self.cache = Cache(self.app, config={
            'CACHE_TYPE': 'redis',
            'CACHE_REDIS_URL': self.config.redis_url,
            'CACHE_DEFAULT_TIMEOUT': self.config.cache_timeout
        })
    
    def setup_rate_limiting(self):
        """Configura o rate limiting"""
        self.limiter = Limiter(
            app=self.app,
            key_func=get_remote_address,
            default_limits=[self.config.rate_limit_default]
        )

# 4. Uso da Aplicação

def main():
    try:
        # Carrega configuração do ambiente
        config = AppConfig.from_env()
        
        # Cria instância da API
        api = RPZApi(config)
        
        # Log das configurações carregadas
        logging.info(f"Configurações carregadas: {config.to_dict()}")
        
        # Inicia a aplicação
        from waitress import serve
        serve(
            api.app,
            host=config.host,
            port=config.port,
            threads=4,
            url_scheme='http'
        )
    
    except Exception as e:
        logging.critical(f"Erro fatal: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

# 5. Exemplo de Uso em Testes

```python
import pytest
from pathlib import Path

@pytest.fixture
def test_config():
    """Fixture para criar configuração de teste"""
    return AppConfig(
        rpz_file=Path('tests/data/test.rpz'),
        whitelist_file=Path('tests/data/test_whitelist.txt'),
        log_file=Path('tests/logs/test.log'),
        host='127.0.0.1',
        port=5000,
        redis_url='redis://localhost:6379',
        testing=True
    )

def test_config_validation(test_config):
    """Testa a validação da configuração"""
    try:
        test_config.validate()
    except ValueError as e:
        pytest.fail(f"Validação falhou: {e}")
```