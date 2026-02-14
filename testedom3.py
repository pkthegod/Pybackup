#!/usr/bin/python3
import os
import socket
import ssl
import datetime
import json
import logging
import argparse
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
import OpenSSL.SSL
import idna

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('domain_checker.log'),
        logging.StreamHandler()
    ]
)

# Configuração de log
def setup_logging(quiet_mode: bool = False):
    """Configura o logging com base no modo (normal ou quieto)"""
    log_level = logging.ERROR if quiet_mode else logging.INFO
    
    # Limpar os manipuladores de log existentes
    logging.getLogger().handlers.clear()
    
    # Configurar manipulador de arquivo
    file_handler = logging.FileHandler('domain_checker.log')
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    
    # Configurar manipuladores
    handlers = [file_handler]
    
    # Adicionar manipulador de console apenas se não estiver em modo quieto
    if not quiet_mode:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        handlers.append(console_handler)
    
    # Configurar logging
    logging.basicConfig(
        level=log_level,
        handlers=handlers
    )
@dataclass
class Config:
    """Classe para armazenar configurações do programa"""
    BASE_DIR: Path = Path('/usr/lib/zabbix/externalscripts/')
    ALTERN_DIR: Path = Path('/usr/share/zabbix/')
    TIMEOUT_SECONDS: int = 10
    DEFAULT_PORT: int = 8080
    DOMAINS_FILE: str = 'testeporta.txt'
    RESULTS_FILE: str = 'speed.json'

class CertificateInfo:
    """Classe para armazenar informações do certificado"""
    def __init__(self):
        self.subject = None
        self.issuer = None
        self.not_before = None
        self.not_after = None
        self.serial_number = None
        self.version = None
        self.has_expired = False

class DomainCheckResult:
    """Classe para armazenar e formatar resultados da verificação de domínio"""
    def __init__(self, domain: str, port: int):
        self.domain = domain
        self.port = port
        self.reachable = False
        self.valid_certificate = False
        self.expiry_date = None
        self.error_message = None
        self.ip_address = None
        self.cert_info = None
        self.days_to_expire = None

    def to_dict(self) -> Dict:
        cert_info = {}
        if self.cert_info:
            cert_info = {
                "subject": self.cert_info.subject,
                "issuer": self.cert_info.issuer,
                "valid_from": str(self.cert_info.not_before) if self.cert_info.not_before else None,
                "valid_until": str(self.cert_info.not_after) if self.cert_info.not_after else None,
                "serial_number": self.cert_info.serial_number,
                "version": self.cert_info.version,
                "has_expired": self.cert_info.has_expired,
                "days_to_expire": self.days_to_expire
            }

        return {
            "Domain": self.domain,
            "IP": self.ip_address,
            "Port": self.port,
            "Reachable": self.reachable,
            "Valid Certificate": self.valid_certificate,
            "Certificate Info": cert_info,
            "Error": self.error_message
        }

class DomainChecker:
    """Classe principal para verificação de domínios"""
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def get_certificate_info(self, hostname: str, port: int) -> Optional[CertificateInfo]:
        """Obtém informações detalhadas do certificado SSL"""
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
                    
                    # Extrair informações do certificado
                    cert_info.subject = str(x509.get_subject().get_components())
                    cert_info.issuer = str(x509.get_issuer().get_components())
                    cert_info.not_before = datetime.strptime(
                        x509.get_notBefore().decode('ascii'),
                        '%Y%m%d%H%M%SZ'
                    ).replace(tzinfo=timezone.utc)
                    cert_info.not_after = datetime.strptime(
                        x509.get_notAfter().decode('ascii'),
                        '%Y%m%d%H%M%SZ'
                    ).replace(tzinfo=timezone.utc)
                    cert_info.serial_number = x509.get_serial_number()
                    cert_info.version = x509.get_version()
                    cert_info.has_expired = x509.has_expired()

                    return cert_info

        except Exception as e:
            self.logger.error(f"Error getting certificate info for {hostname}: {str(e)}")
            return None

    def check_domain(self, domain: str, port: int) -> DomainCheckResult:
        """Verifica a disponibilidade e certificado SSL de um domínio"""
        result = DomainCheckResult(domain, port)
        
        try:
            # Converter domínio para IDNA para suporte a caracteres internacionais
            domain_idna = idna.encode(domain).decode('ascii')
            
            # Resolução DNS
            result.ip_address = socket.gethostbyname(domain_idna)
            self.logger.info(f"Resolved {domain} to {result.ip_address}")
            
            # Obter informações do certificado
            cert_info = self.get_certificate_info(domain_idna, port)
            
            if cert_info:
                result.reachable = True
                result.cert_info = cert_info
                result.valid_certificate = not cert_info.has_expired
                
                # Calcular dias até a expiração
                if cert_info.not_after:
                    now = datetime.now(timezone.utc)
                    result.days_to_expire = (cert_info.not_after - now).days
                    
                    self.logger.info(
                        f"Certificate for {domain} expires in {result.days_to_expire} days "
                        f"({cert_info.not_after.strftime('%Y-%m-%d')})"
                    )
            else:
                result.error_message = "Unable to get certificate information"
                
        except socket.gaierror as e:
            result.error_message = f"DNS Resolution Error: {str(e)}"
            self.logger.error(result.error_message)
        except socket.timeout:
            result.error_message = "Connection Timeout"
            self.logger.error(f"Timeout connecting to {domain}:{port}")
        except ConnectionRefusedError:
            result.error_message = "Connection Refused"
            self.logger.error(f"Connection refused to {domain}:{port}")
        except Exception as e:
            result.error_message = f"Unexpected Error: {str(e)}"
            self.logger.error(f"Unexpected error checking {domain}: {str(e)}")
        
        return result

    def load_domains(self) -> List[str]:
        """Carrega lista de domínios do arquivo"""
        domains_path = self.config.BASE_DIR / self.config.DOMAINS_FILE
        try:
            with open(domains_path, "r") as file:
                domains = [line.strip() for line in file.readlines() if line.strip()]
            self.logger.info(f"Loaded {len(domains)} domains from {domains_path}")
            return domains
        except FileNotFoundError:
            self.logger.error(f"Domains file not found: {domains_path}")
            return []
        except Exception as e:
            self.logger.error(f"Error loading domains file: {str(e)}")
            return []

    def save_results(self, results: List[DomainCheckResult]) -> bool:
        """Salva resultados em arquivo JSON"""
        results_path = self.config.ALTERN_DIR / self.config.RESULTS_FILE
        try:
            results_dict = [result.to_dict() for result in results]
            results_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(results_path, 'w') as jsonfile:
                json.dump(results_dict, jsonfile, indent=2)
            
            self.logger.info(f"Results saved to {results_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")
            return False


def main(quiet_mode: bool = False):
    #Função principal do programa com suporte a modo quieto
    # Configurar logging baseado no modo
    setup_logging(quiet_mode)
    
    config = Config()
    checker = DomainChecker(config)
    
    # Carrega domínios
    domains = checker.load_domains()
    if not domains:
        logging.error("No domains to test. Exiting.")
        return False

    # Verifica cada domínio
    results = []
    total_domains = len(domains)
    for index, domain in enumerate(domains, 1):
        logging.info(f"Checking domain {index}/{total_domains}: {domain}")
        result = checker.check_domain(domain, config.DEFAULT_PORT)
        results.append(result)

    # Salva resultados
    if checker.save_results(results):
        # Gera resumo da execução
        successful_checks = sum(1 for r in results if r.reachable)
        valid_certs = sum(1 for r in results if r.valid_certificate)
        
        logging.info("=== Execution Summary ===")
        logging.info(f"Total domains checked: {total_domains}")
        logging.info(f"Successful connections: {successful_checks}")
        logging.info(f"Valid certificates: {valid_certs}")
        
        # Exibe alertas para certificados próximos da expiração
        for result in results:
            if result.days_to_expire is not None and result.days_to_expire < 30:
                logging.warning(
                    f"Certificate for {result.domain} will expire in {result.days_to_expire} days!"
                )
        
        return True
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Domain and SSL Certificate Checker")
    parser.add_argument("-q", "--quiet", action="store_true", 
                        help="Run in quiet mode (only log to file, no terminal output)")
    args = parser.parse_args()

    try:
        success = main(quiet_mode=args.quiet)
        exit(0 if success else 1)
    except KeyboardInterrupt:
        logging.info("Process interrupted by user")
        exit(1)
    except Exception as e:
        logging.critical(f"Critical error: {str(e)}")
        exit(1)