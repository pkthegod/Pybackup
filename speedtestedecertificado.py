import socket
import ssl
import datetime
import csv

def is_domain_port_reachable(domain, port):
    try:
        # Create a socket object
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # Set a timeout for the connection attempt
        
        # Wrap the socket with SSL context using secure protocol
        context = ssl.create_default_context()
        with context.wrap_socket(sock, server_hostname=domain) as secure_sock:
            # Attempt to connect to the domain and port
            secure_sock.connect((domain, port))
            
            # Check certificate validity
            cert = secure_sock.getpeercert()
            expiration_date = datetime.datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
            current_date = datetime.datetime.utcnow()
            if expiration_date > current_date:
                return True, expiration_date
            else:
                return False, expiration_date
    except (socket.timeout, ConnectionRefusedError, socket.gaierror, ssl.SSLError):
        # Connection timed out, refused, domain resolution failed, or SSL error
        return False, None
    finally:
        sock.close()

def load_domains_from_file(filename):
    try:
        with open(filename, "r") as file:
            domains = [line.strip() for line in file.readlines()]
        return domains
    except FileNotFoundError:
        print("File not found. Make sure the file exists.")
        return []

filename = input("Enter the filename containing domains: ")
port = int(input("Enter the port: "))

domains = load_domains_from_file(filename)

if not domains:
    print("No domains to test. Exiting.")
    exit()

with open('resultado.csv', 'w', newline='') as csvfile:
    csv_writer = csv.writer(csvfile)
    csv_writer.writerow(['Domain', 'Port', 'Reachable', 'Valid Certificate', 'Expiry Date'])

    for domain in domains:
        reachable, expiration_date = is_domain_port_reachable(domain, port)
        valid_certificate = reachable and expiration_date is not None
        csv_writer.writerow([domain, port, reachable, valid_certificate, expiration_date])
        
        if valid_certificate:
            print(f"The domain '{domain}' on port {port} is reachable. SSL certificate is valid until {expiration_date}.")
        else:
            print(f"The domain '{domain}' on port {port} is not reachable or the SSL certificate is not valid.")
print("Results saved to resultado.csv.")
