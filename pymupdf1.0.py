import fitz  # PyMuPDF
import re
import os

# Regex para capturar domínios no formato xxx.xxx.xxx ou xx.xx
DOMAIN_REGEX = r'\b(?:[a-zA-Z0-9-]{2,}\.[a-zA-Z]{2,}|[a-zA-Z0-9-]{3,}\.[a-zA-Z0-9-]{3,}\.[a-zA-Z]{2,})\b'

def extract_text_from_pdf(pdf_path):
    """Extrai texto de um arquivo PDF."""
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    return text

def extract_domains_from_text(text):
    """Aplica regex para encontrar domínios no texto extraído."""
    return re.findall(DOMAIN_REGEX, text)

def process_pdfs_in_folder(folder_path):
    """Percorre todos os PDFs em uma pasta e extrai os domínios."""
    all_domains = set()
    for file_name in os.listdir(folder_path):
        if file_name.lower().endswith(".pdf"):
            pdf_path = os.path.join(folder_path, file_name)
            print(f"\n📄 Processando: {pdf_path}")
            text = extract_text_from_pdf(pdf_path)
            domains = extract_domains_from_text(text)
            all_domains.update(domains)
    return all_domains

# Defina a pasta onde os PDFs estão localizados
pdf_folder = r"C:\pdfs"

# Executa a extração
extracted_domains = process_pdfs_in_folder(pdf_folder)

# Salva os domínios extraídos em um arquivo
with open("dominios_extraidos.txt", "w") as f:
    for domain in sorted(extracted_domains):
        f.write(domain + "\n")

print("\n✅ Extração concluída! Domínios salvos em 'dominios_extraidos.txt'.")
