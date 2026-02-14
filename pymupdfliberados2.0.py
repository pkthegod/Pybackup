import os
import re
import fitz
import pytesseract
from pdf2image import convert_from_path
from openpyxl import load_workbook
import csv
import logging
from tqdm import tqdm

# Configurações
INPUT_FOLDER = r"C:\pdfs\liberados"
OUTPUT_FILE = "dominios_liberados.txt"
EXTENSOES = ('.pdf', '.xls', '.xlsx', '.ods', '.csv')

logging.basicConfig(level=logging.INFO, format='%(message)s')

def extract_text_with_ocr(pdf_path: str) -> str:
    """Extrai texto de PDFs usando OCR"""
    try:
        text = ""
        images = convert_from_path(pdf_path)
        for page_num, img in enumerate(images):
            text += pytesseract.image_to_string(img, lang='por') + "\n"
        return text
    except Exception as e:
        logging.error(f"Erro no OCR {pdf_path}: {str(e)}")
        return ""

def extract_text_from_pdf(pdf_path: str) -> str:
    """Tenta extração normal primeiro, depois OCR"""
    try:
        # Primeira tentativa: extração direta
        with fitz.open(pdf_path) as doc:
            text = ""
            for page in doc:
                text += page.get_text("text", flags=fitz.TEXT_PRESERVE_WHITESPACE) + "\n"
            
            # Verifica se encontrou texto relevante
            if len(text.strip()) > 50:  # Limiar arbitrário
                return text
            
            # Se texto insuficiente, usa OCR
            logging.warning(f"PDF pode ser imagem: {os.path.basename(pdf_path)}")
            return extract_text_with_ocr(pdf_path)
            
    except Exception as e:
        logging.error(f"Erro no PDF {pdf_path}: {str(e)}")
        return ""

def find_domains(text: str) -> set:
    """Busca tolerante a erros de OCR"""
    pattern = r'''
        (?:[a-zA-Z0-9]      # Primeiro caractere não pode ser hífen
        [a-zA-Z0-9-]{0,61}  # Parte do domínio
        [a-zA-Z0-9]\.)      # Último caractere antes do ponto
        +[a-zA-Z]{2,}       # TLD
        (?=\b|$|:|/)        # Lookahead para evitar captura parcial
    '''
    matches = re.finditer(pattern, text, re.VERBOSE)
    
    domains = set()
    for match in matches:
        candidate = match.group()
        # Limpeza agressiva
        domain = (
            candidate.lower()
            .replace(" ", "").replace("_", "")   # Comum em erros de OCR
            .replace(",", ".").replace("..", ".") # Correção de vírgulas
            .strip('.:;!*()[]{}')
        )
        
        # Validação adaptada
        parts = domain.split('.')
        if (3 <= len(domain) <= 253 and
            len(parts) >= 2 and
            all(1 <= len(part) <= 63 for part in parts)):
            domains.add(domain)
    
    return domains

def process_files():
    """Processamento principal"""
    all_files = []
    for root, _, files in os.walk(INPUT_FOLDER):
        for file in files:
            if file.lower().endswith(EXTENSOES):
                all_files.append(os.path.join(root, file))
    
    if not all_files:
        logging.warning("Nenhum arquivo encontrado!")
        return
    
    all_domains = set()
    
    for file_path in tqdm(all_files, desc="Processando arquivos"):
        file_name = os.path.basename(file_path)
        try:
            # Extração de texto
            if file_path.lower().endswith('.pdf'):
                text = extract_text_from_pdf(file_path)
            elif file_path.lower().endswith(('.xls', '.xlsx', '.ods')):
                text = extract_text_from_excel(file_path)  # Mantenha função anterior
            elif file_path.lower().endswith('.csv'):
                text = extract_text_from_csv(file_path)    # Mantenha função anterior
            
            # Busca de domínios
            if text:
                domains = find_domains(text)
                if domains:
                    logging.info(f"✅ {len(domains)} domínios em {file_name}")
                    all_domains.update(domains)
                    
        except Exception as e:
            logging.error(f"Falha crítica em {file_name}: {str(e)}")
    
    # Resultado final
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(sorted(all_domains)))
    
    logging.info(f"\n✅ Concluído! Domínios encontrados: {len(all_domains)}")

if __name__ == '__main__':
    process_files()