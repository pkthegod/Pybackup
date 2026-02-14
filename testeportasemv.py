#!/usr/bin/python3

import socket
import ssl
import datetime
import json

def is_domain_port_reachable(domain, port):
    try:
        # Tenta resolver o endereço IP do domínio
        ip_address = socket.gethostbyname(domain)
        
        # Cria um objeto de soquete
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        # Wrap the socket with SSL context using secure protocol
        context = ssl.create_default_context()
        context.check_hostname = False
        
        with context.wrap_socket(sock, server_hostname=domain) as secure_sock:
            # Tenta conectar ao domínio e porta
            secure_sock.connect((ip_address, port))
            
            # Verifica a validade do certificado
            cert = secure_sock.getpeercert()
            expiration_date = datetime.datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
            current_date = datetime.datetime.utcnow()
            if expiration_date > current_date:
                return {"Domain": domain, "Port": port, "Reachable": True, "Valid Certificate": True, "Expiry Date": str(expiration_date)}
            else:
                return {"Domain": domain, "Port": port, "Reachable": True, "Valid Certificate": False, "Expiry Date": str(expiration_date)}
    except (socket.timeout, ConnectionRefusedError, socket.gaierror, ssl.SSLError, socket.error):
        # Lida com timeouts, erros de conexão e erros de resolução de DNS
        return {"Domain": domain, "Port": port, "Reachable": False, "Valid Certificate": False, "Expiry Date": None}

def load_domains_from_file(filename):
    try:
        with open(filename, "r") as file:
            domains = [line.strip() for line in file.readlines()]
        return domains
    except FileNotFoundError:
        print("File not found. Make sure the file exists.")
        return []

# Configurações estáticas
port = 8080
domains_file = '/usr/lib/zabbix/externalscripts/testeporta.txt'
json_file = 'speed.json'

domains = load_domains_from_file(domains_file)

if not domains:
    print("No domains to test. Exiting.")
    exit()

results = []

for domain in domains:
    result = is_domain_port_reachable(domain, port)
    results.append(result)

# Salva os resultados em um arquivo JSON (sempre sobrescreve)
with open(json_file, 'w') as jsonfile:
    json.dump(results, jsonfile)

print("Results saved to", json_file)
