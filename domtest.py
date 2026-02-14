import os
import socket
import json
import subprocess

ALTERN_DIR = '/usr/share/zabbix/'

# File containing the list of domains
DOMAINS_FILE = "domains.txt"

# Words to combine with each domain
COMBINED_WORDS = ["teste.", "velocidade.", "speed.", "speedtest.", "st."]

def get_ip_addresses(domain):
    ipv4 = subprocess.getoutput(f"dig +short {domain} A")
    ipv6 = subprocess.getoutput(f"dig +short {domain} AAAA")

    if ipv4 or ipv6:
        ping_result = subprocess.run(["ping", "-c", "1", domain], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        is_reachable = ping_result.returncode == 0
        return {"domain": domain, "ipv4": ipv4, "ipv6": ipv6, "ping": is_reachable}
    else:
        return None

output_file = os.path.join(ALTERN_DIR, 'outputdom.json')


def combine_words(domain):
    results = []
    for word in COMBINED_WORDS:
        result = get_ip_addresses(f"{word}{domain}")
        if result:
            results.append(result)
    return results

def print_json_array():
    first_domain = True
    results = []

    with open(DOMAINS_FILE, "r") as file:
        for line in file:
            domain = line.strip()
            combined_results = combine_words(domain)
            if combined_results:
                for result in combined_results:
                    results.append(result)

    with open("outputdom.json", "w") as output_file:
        json.dump(results, output_file, indent=2)

    print("JSON output saved to outputdom.json")

if __name__ == "__main__":
    print_json_array()