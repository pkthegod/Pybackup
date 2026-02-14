import fitz  # PyMuPDF
import re
import os
import pandas as pd
from openpyxl import load_workbook

# Regex baseada na versão original com expansão para novos casos
DOMAIN_REGEX = r'\b(?:[a-z0-9-]{2,}\.[a-z0-9-]{2,}(?:\.[a-z0-9-]{2,})*)\b'

def extract_text_from_pdf(pdf_path):
    """Extrai texto de PDFs mantendo a abordagem original que funcionava"""
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    return text

def extract_text_from_excel(excel_path):
    """Extrai texto de planilhas de forma simples"""
    text = ""
    try:
        df = pd.read_excel(excel_path, sheet_name=None, header=None)
        for sheet in df:
            text += df[sheet].to_string(index=False, header=False) + "\n"
    except:
        pass
    return text

def clean_domain(domain):
    """Limpeza básica mantendo a estrutura original"""
    return domain.lower().split('/')[0].split('?')[0].strip('.,;:!')

def find_domains(text):
    """Combinação da abordagem original com filtro mínimo"""
    raw_domains = re.findall(DOMAIN_REGEX, text, re.IGNORECASE)
    return {clean_domain(d) for d in raw_domains if d.count('.') >= 1}

def process_files(folder_path):
    """Processa PDFs e Excel com logging detalhado"""
    all_domains = set()
    
    for root, _, files in os.walk(folder_path):
        for file in files:
            path = os.path.join(root, file)
            try:
                if file.lower().endswith('.pdf'):
                    text = extract_text_from_pdf(path)
                elif file.lower().endswith(('.xls', '.xlsx', '.ods')):
                    text = extract_text_from_excel(path)
                else:
                    continue
                
                domains = find_domains(text)
                all_domains.update(domains)
                print(f"Arquivo: {file} | Domínios encontrados: {len(domains)}")
                
            except Exception as e:
                print(f"Erro em {file}: {str(e)}")
    
    return sorted(all_domains)

# Configuração
input_folder = r"C:\pdfs"
output_file = "dominios_extraidos.txt"

# Execução
print("Iniciando processamento...")
result = process_files(input_folder)

# Salvando resultados
with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n".join(result))

print(f"\n✅ Concluído! Total de domínios: {len(result)}")