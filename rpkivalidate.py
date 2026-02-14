import os
import socket
import json
import subprocess
from ping3 import ping
from concurrent.futures import ThreadPoolExecutor, as_completed

# Directory where the output JSON will be saved
ALTERN_DIR = '/usr/share/zabbix/'
OUTPUT_FILE = os.path.join(ALTERN_DIR, 'outputdom.json')

# File containing the list of domains
DOMAINS_FILE = "domains.txt"

# Words to combine with each domain
COMBINED_WORDS = ["teste.", "velocidade.", "speed.", "speedtest.", "st.", "ookla."]

# Function to resolve IP addresses (IPv4 and IPv6) using Python's socket
def get_ip_addresses(domain):
    ipv4 = []
    ipv6 = []

    try:
        ipv4 = [result[4][0] for result in socket.getaddrinfo(domain, None, socket.AF_INET)]
    except socket.gaierror:
        ipv4 = []

    try:
        ipv6 = [result[4][0] for result in socket.getaddrinfo(domain, None, socket.AF_INET6)]
    except socket.gaierror:
        ipv6 = []

    is_reachable = ping(domain) is not None
    if ipv4 or ipv6:
        return {"domain": domain, "ipv4": ipv4, "ipv6": ipv6, "ping": is_reachable}
    else:
        return None

# Combines each word with the domain and fetches IP information
def combine_words(domain):
    results = []
    for word in COMBINED_WORDS:
        result = get_ip_addresses(f"{word}{domain}")
        if result:
            results.append(result)
    return results

# Main function to process domains from the file and save the results in JSON format
def print_json_array():
    if not os.path.exists(DOMAINS_FILE):
        print(f"Error: The file {DOMAINS_FILE} does not exist.")
        return

    results = []

    with open(DOMAINS_FILE, "r") as file:
        domains = [line.strip() for line in file]

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_domain = {executor.submit(combine_words, domain): domain for domain in domains}
        for future in as_completed(future_to_domain):
            combined_results = future.result()
            if combined_results:
                results.extend(combined_results)

    # Ensure the output directory exists
    os.makedirs(ALTERN_DIR, exist_ok=True)

    # Save the results to the specified output file
    with open(OUTPUT_FILE, "w") as output_file:
        json.dump(results, output_file, indent=2)

    print(f"JSON output saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    # Check if the required system tools are available
    try:
        subprocess.run(["which", "dig"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print("Error: 'dig' command is not available. Please install 'dnsutils'.")

    try:
        subprocess.run(["which", "ping"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print("Error: 'ping' command is not available. Please install 'inetutils-ping'.")

    print_json_array()

root@zbxserver:/usr/lib/zabbix/externalscripts# cat rpki
rpkimancer/    rpki.sh        rpki_test2.py  rpki_test3.py  rpki_test4.py  rpki_test5.py  rpki_test6.py  rpki_test.py   rpki_test.sh
root@zbxserver:/usr/lib/zabbix/externalscripts# cat rpki_test6.py 
import aiohttp
import asyncio
import json

INPUT_FILE = "as_prefix_list2.txt"
OUTPUT_FILE = "/usr/share/zabbix/validation_results.json"

async def validate_asn_prefix(session, isp, asn, prefixes):
    results = {"isp": isp, "asn": asn, "validations": []}

    for prefix in prefixes:
        version = "IPv6" if ':' in prefix else "IPv4"
        url = f"https://rpki-validator.ripe.net/validity?asn={asn}&prefix={prefix}"
        
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                state = data['validated_route']['validity']['state']
                generated_time = data['generatedTime']
                results["validations"].append({
                    "prefix": prefix,
                    "state": state,
                    "generated_time": generated_time,
                    "version": version
                })
            else:
                results["validations"].append({
                    "prefix": prefix,
                    "error": f"Falha ao consultar {prefix} - Status Code: {response.status}",
                    "version": version
                })

    return results

async def main():
    async with aiohttp.ClientSession() as session:
        with open(INPUT_FILE, 'r') as file:
            lines = file.readlines()

        total_lines = len(lines)
        print(f"[INFO] Iniciando a validação de {total_lines} entradas.")

        tasks = []
        for index, line in enumerate(lines):
            values = line.strip().split()
            isp = values[0]
            asn = values[1]
            prefixes = values[2:]  # Collect all prefixes (both IPv4 and IPv6)
            tasks.append(validate_asn_prefix(session, isp, asn, prefixes))

        results_list = await asyncio.gather(*tasks)

        with open(OUTPUT_FILE, 'w') as outfile:
            json.dump(results_list, outfile, indent=4)

        print(f"[INFO] Validação concluída. Resultados salvos em {OUTPUT_FILE}.")

# Executar o código assíncrono
if __name__ == "__main__":
    asyncio.run(main())
