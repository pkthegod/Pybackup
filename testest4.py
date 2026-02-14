#!/usr/bin/python3
import os
import socket
import ssl
import datetime
import json
import logging
import argparse
import time
import csv
import html
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone, timedelta
import OpenSSL.SSL
import idna
import concurrent.futures

class CustomFormatter(logging.Formatter):
    """Custom log formatter with colors"""
    COLORS = {
        logging.DEBUG: '\033[94m',    # Blue
        logging.INFO: '\033[92m',     # Green
        logging.WARNING: '\033[93m',  # Yellow
        logging.ERROR: '\033[91m',    # Red
        logging.CRITICAL: '\033[1;31m'  # Bold Red
    }
    RESET = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelno, self.RESET)
        formatter = logging.Formatter(
            f'{log_color}%(asctime)s - %(levelname)s - %(message)s{self.RESET}'
        )
        return formatter.format(record)

@dataclass
class Config:
    """Enhanced configuration class"""
    TIMEOUT_SECONDS: int = 10
    DEFAULT_PORTS: List[int] = field(default_factory=lambda: [80, 443, 8080])
    CERTIFICATE_WARNING_DAYS: int = 30
    LOG_DIRECTORY: Path = Path('./logs')
    MAX_WORKERS: int = 10
    OUTPUT_DIRECTORY: Path = Path('./output')
    DEBUG_MODE: bool = False

class CertificateInfo:
    """Expanded certificate information class"""
    def __init__(self):
        self.subject = None
        self.issuer = None
        self.not_before = None
        self.not_after = None
        self.serial_number = None
        self.version = None
        self.has_expired = False
        self.alternative_names = []
        self.signature_algorithm = None

class DomainCheckResult:
    """Enhanced domain check result with more detailed information"""
    def __init__(self, domain: str, port: int):
        self.domain = domain
        self.port = port
        self.reachable = False
        self.valid_certificate = False
        self.expiry_date = None
        self.error_message = None
        self.ip_address = None
        self.cert_info: Optional[CertificateInfo] = None
        self.days_to_expire = None
        self.additional_validations = {}

    def to_dict(self) -> Dict[str, Any]:
        def serialize_value(value):
            """Converte valores para tipos serializáveis"""
            if isinstance(value, bytes):
                try:
                    return value.decode('utf-8', errors='ignore')
                except:
                    return str(value)
            elif isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, tuple):
                return [serialize_value(item) for item in value]
            return value

        cert_info = {}
        if self.cert_info:
            cert_info = {
                "subject": serialize_value(self.cert_info.subject),
                "issuer": serialize_value(self.cert_info.issuer),
                "valid_from": serialize_value(self.cert_info.not_before),
                "valid_until": serialize_value(self.cert_info.not_after),
                "serial_number": serialize_value(self.cert_info.serial_number),
                "version": serialize_value(self.cert_info.version),
                "has_expired": self.cert_info.has_expired,
                "alternative_names": [serialize_value(name) for name in self.cert_info.alternative_names],
                "signature_algorithm": serialize_value(self.cert_info.signature_algorithm)
            }

        return {
            "domain": serialize_value(self.domain),
            "ip": serialize_value(self.ip_address),
            "port": self.port,
            "reachable": self.reachable,
            "valid_certificate": self.valid_certificate,
            "days_to_expire": self.days_to_expire,
            "certificate_info": cert_info,
            "additional_validations": {
                k: serialize_value(v) for k, v in self.additional_validations.items()
            },
            "error": serialize_value(self.error_message) if self.error_message else None
        }

class DomainChecker:
    """Advanced domain and SSL checker"""
    def __init__(self, config: Config):
        self.config = config
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """Setup logger with custom formatting"""
        log_dir = self.config.LOG_DIRECTORY
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logger = logging.getLogger('DomainChecker')
        logger.setLevel(logging.DEBUG if self.config.DEBUG_MODE else logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler(log_dir / 'domain_checker.log')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        # Console handler with colors
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(CustomFormatter())
        
        logger.handlers.clear()
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger

    def get_certificate_info(self, hostname: str, port: int) -> Optional[CertificateInfo]:
        try:
            cert_info = CertificateInfo()
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with socket.create_connection((hostname, port), timeout=self.config.TIMEOUT_SECONDS) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssl_sock:
                    binary_cert = ssl_sock.getpeercert(binary_form=True)
                    if not binary_cert:
                        return None
                
                    x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, binary_cert)
                
                    # Conversão segura de componentes
                    cert_info.subject = [
                        (k.decode('utf-8', errors='ignore'), v.decode('utf-8', errors='ignore')) 
                        for k, v in x509.get_subject().get_components()
                    ]
                    cert_info.issuer = [
                        (k.decode('utf-8', errors='ignore'), v.decode('utf-8', errors='ignore')) 
                        for k, v in x509.get_issuer().get_components()
                    ]
                
                    # Restante do código permanece o mesmo...
                    
                    # Tratamento de nomes alternativos
                    try:
                        san_ext = x509.get_extension(OpenSSL.crypto.X509_PURPOSE_SSL_SERVER)
                        san_names = [
                            name.decode('utf-8', errors='ignore') 
                            for name in str(san_ext).split(', ')
                        ]
                        cert_info.alternative_names = san_names
                    except Exception:
                        cert_info.alternative_names = []

                    return cert_info

        except Exception as e:
            self.logger.error(f"Error getting certificate info for {hostname}: {str(e)}")
            return None

    def advanced_certificate_validation(self, cert_info: CertificateInfo) -> Dict:
        """Advanced certificate security validations"""
        validations = {
            "wildcard_certificate": any("*" in str(component) for component in cert_info.subject),
            "expired": cert_info.has_expired,
            "alternative_names_count": len(cert_info.alternative_names),
            "signature_algorithm": cert_info.signature_algorithm
        }
        return validations

    def check_domain(self, domain: str, port: int) -> DomainCheckResult:
        """Comprehensive domain and SSL check"""
        result = DomainCheckResult(domain, port)
        
        try:
            # Convert domain to IDNA
            domain_idna = idna.encode(domain).decode('ascii')
            
            # DNS resolution
            result.ip_address = socket.gethostbyname(domain_idna)
            self.logger.info(f"Resolved {domain} to {result.ip_address}")
            
            # Get certificate information
            cert_info = self.get_certificate_info(domain_idna, port)
            
            if cert_info:
                result.reachable = True
                result.cert_info = cert_info
                result.valid_certificate = not cert_info.has_expired
                
                # Calculate days until expiration
                if cert_info.not_after:
                    now = datetime.now(timezone.utc)
                    result.days_to_expire = max(0, (cert_info.not_after - now).days)
                    
                    if result.days_to_expire <= self.config.CERTIFICATE_WARNING_DAYS:
                        self.logger.warning(
                            f"Certificate for {domain} expires in {result.days_to_expire} days "
                            f"({cert_info.not_after.strftime('%Y-%m-%d')})"
                        )
                
                # Additional certificate validations
                result.additional_validations = self.advanced_certificate_validation(cert_info)
            else:
                result.error_message = "Unable to get certificate information"
                
        except Exception as e:
            result.error_message = str(e)
            self.logger.error(f"Unexpected error checking {domain}: {str(e)}")
        
        return result

def check_multiple_domains(domains: List[str], config: Config) -> List[DomainCheckResult]:
    """Concurrent domain checking"""
    results = []
    checker = DomainChecker(config)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        # Create futures for each domain and port combination
        futures = []
        for domain in domains:
            for port in config.DEFAULT_PORTS:
                futures.append(
                    executor.submit(checker.check_domain, domain, port)
                )
        
        # Collect results
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    
    return results

def export_results(results: List[DomainCheckResult], output_format: str, output_path: Optional[str] = None):
    """Export results in various formats"""
    output_dir = Path('./output')
    output_dir.mkdir(exist_ok=True)
    
    # Convert results to list of dictionaries
    data = [result.to_dict() for result in results]
    
    if output_format == 'json':
        output_file = output_path or str(output_dir / 'domain_check_results.json')
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Results exported to {output_file}")
    
    elif output_format == 'csv':
        output_file = output_path or str(output_dir / 'domain_check_results.csv')
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        print(f"Results exported to {output_file}")
    
    elif output_format == 'html':
        output_file = output_path or str(output_dir / 'domain_check_results.html')
        with open(output_file, 'w') as f:
            f.write('<html><body><table border="1">')
            f.write('<tr>' + ''.join(f'<th>{key}</th>' for key in data[0].keys()) + '</tr>')
            for row in data:
                f.write('<tr>')
                for value in row.values():
                    f.write(f'<td>{html.escape(str(value))}</td>')
                f.write('</tr>')
            f.write('</table></body></html>')
        print(f"Results exported to {output_file}")

def read_domains_from_file(file_path: Union[str, Path]) -> List[str]:
    """
    Ler domínios de um arquivo, suportando diferentes formatos:
    - Texto simples (um domínio por linha)
    - Ignorar linhas em branco
    - Ignorar comentários (linhas começando com #)
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")
    
    domains = []
    with open(file_path, 'r') as f:
        for line in f:
            # Remove whitespace e converte para lowercase
            domain = line.strip().lower()
            
            # Pula linhas em branco ou comentários
            if not domain or domain.startswith('#'):
                continue
            
            # Validação básica de domínio
            if '.' in domain:
                domains.append(domain)
    
    if not domains:
        raise ValueError(f"Nenhum domínio válido encontrado no arquivo {file_path}")
    
    return domains

def main():
    parser = argparse.ArgumentParser(description="Advanced Domain and SSL Certificate Checker")
    
    # Grupo mutuamente exclusivo para entrada de domínios
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-d", "--domains", nargs='+', type=str,
                       help="Specify one or more domains to check")
    group.add_argument("-f", "--domain-file", type=str,
                       help="Path to a file containing domains to check (one per line)")
    
    parser.add_argument("-p", "--ports", nargs='+', type=int,
                        help="Ports to check (optional)")
    parser.add_argument("-o", "--output", choices=['json', 'csv', 'html'], default='json',
                        help="Output format for results")
    parser.add_argument("--output-file", type=str,
                        help="Custom output file path")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Configurar domínios
    try:
        if args.domain_file:
            # Ler domínios do arquivo
            domains = read_domains_from_file(args.domain_file)
        else:
            # Usar domínios passados como argumento
            domains = args.domains
    except (FileNotFoundError, ValueError) as e:
        logging.error(str(e))
        exit(1)
    
    # Configure based on arguments
    config = Config(
        DEBUG_MODE=args.debug
    )
    
    # Definir portas, usando as padrão se nenhuma for especificada
    config.DEFAULT_PORTS = args.ports if args.ports else [80, 443, 8080]
    
    # Perform domain checks
    try:
        results = check_multiple_domains(domains, config)
        
        # Export results
        export_results(results, 
                       args.output, 
                       args.output_file)
        
    except Exception as e:
        logging.critical(f"Critical error: {str(e)}")
        exit(1)

# Exemplo de arquivo de domínios (domains.txt)
"""
# Comentário: Lista de domínios para verificação
google.com
microsoft.com
github.com
# Domínio de exemplo
example.com
"""

if __name__ == "__main__":
    main()