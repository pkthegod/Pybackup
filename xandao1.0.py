import os
import datetime
import sys

def get_serial_number():
    """
    Gera um número de série baseado na data atual no formato ano-mês-dia-01.
    """
    today = datetime.date.today()
    return today.strftime("%Y%m%d01")

def create_rpz_zone_file(domain_file, output_file, var_domain):
    """
    Cria um arquivo de zona RPZ com base na lista de domínios.
    """
    serial_number = get_serial_number()
    with open(domain_file, 'r') as domains, open(output_file, 'w') as output:
        output.write(f"$TTL 1H\n@       IN      SOA LOCALHOST. {var_domain}. (\n")
        output.write(f"                {serial_number}      ; Serial\n")
        output.write("                1h              ; Refresh\n")
        output.write("                15m             ; Retry\n")
        output.write("                30d             ; Expire\n")
        output.write("                2h              ; Negative Cache TTL\n        )\n")
        output.write(f"        NS  {var_domain}.\n\n")

        for domain in domains:
            domain = domain.strip()
            output.write(f"{domain} IN CNAME .\n")
            output.write(f"*.{domain} IN CNAME .\n")

def main(var_domain):
    """
    Executa o script principal: cria o arquivo de zona RPZ com base na lista de domínios.
    """
    domain_list_file = '/opt/api-flask/domains.txt'
    rpz_zone_file = '/opt/api-flask/db.rpz.zone.hosts'

    create_rpz_zone_file(domain_list_file, rpz_zone_file, var_domain)
    print("Arquivo de zona RPZ atualizado.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 script.py sub.dominio.com.br")
        sys.exit(1)
    main(sys.argv[1])