import os
import hashlib
from datetime import datetime

# Configurações
TIPOS_ARQUIVOS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.png']  # Adicione mais tipos se necessário

def calcular_hash_arquivo(caminho_arquivo, bloqueio=65536):
    try:
        hasher = hashlib.md5()
        with open(caminho_arquivo, 'rb') as f:
            buffer = f.read(bloqueio)
            while len(buffer) > 0:
                hasher.update(buffer)
                buffer = f.read(bloqueio)
        return hasher.hexdigest()
    except Exception as e:
        print(f"Erro ao ler arquivo {caminho_arquivo}: {e}")
        return None

def encontrar_duplicados(pasta):
    hashes = {}
    tamanhos = {}
    
    # Primeira passada: agrupa por tamanho
    for pasta_raiz, _, arquivos in os.walk(pasta):
        for arquivo in arquivos:
            if any(arquivo.lower().endswith(ext) for ext in TIPOS_ARQUIVOS):
                caminho_completo = os.path.join(pasta_raiz, arquivo)
                tamanho = os.path.getsize(caminho_completo)
                if tamanho not in tamanhos:
                    tamanhos[tamanho] = []
                tamanhos[tamanho].append(caminho_completo)
    
    # Segunda passada: compara hashes apenas para arquivos com mesmo tamanho
    for tamanho, arquivos in tamanhos.items():
        if len(arquivos) > 1:
            for caminho in arquivos:
                hash_arquivo = calcular_hash_arquivo(caminho)
                if hash_arquivo:
                    if hash_arquivo in hashes:
                        hashes[hash_arquivo].append(caminho)
                    else:
                        hashes[hash_arquivo] = [caminho]
    
    return {chave: val for chave, val in hashes.items() if len(val) > 1}

def escolher_arquivo_principal(arquivos, manter_mais_recente=True):
    """Escolhe o arquivo principal a ser mantido"""
    if manter_mais_recente:
        # Mantém o arquivo mais recente
        return max(arquivos, key=lambda f: os.path.getmtime(f))
    else:
        # Mantém o primeiro arquivo (comportamento original)
        return arquivos[0]

def eliminar_duplicados(duplicados, manter_mais_recente=True):
    """Elimina arquivos duplicados, mantendo apenas uma cópia de cada."""
    for hash_arquivo, arquivos in duplicados.items():
        arquivo_principal = escolher_arquivo_principal(arquivos, manter_mais_recente)
        
        for arquivo in arquivos:
            if arquivo != arquivo_principal:
                try:
                    os.remove(arquivo)
                    print(f"Removido arquivo duplicado: {arquivo}")
                except Exception as e:
                    print(f"Erro ao remover arquivo {arquivo}: {e}")
        
        print(f"Mantido: {arquivo_principal} (Modificado em: {datetime.fromtimestamp(os.path.getmtime(arquivo_principal)).strftime('%Y-%m-%d %H:%M:%S')})\n")

def main():
    pasta_alvo = r'C:\pdfs'
    
    if not os.path.exists(pasta_alvo):
        print(f"A pasta {pasta_alvo} não existe!")
        return
    
    print("Procurando arquivos duplicados...")
    duplicados = encontrar_duplicados(pasta_alvo)
    
    if not duplicados:
        print("Nenhum arquivo duplicado encontrado.")
        return
    
    print("\nArquivos duplicados encontrados:")
    for hash_arquivo, arquivos in duplicados.items():
        print(f"\nHash MD5: {hash_arquivo}")
        for arquivo in arquivos:
            mod_time = datetime.fromtimestamp(os.path.getmtime(arquivo)).strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n - {arquivo} (Última modificação: {mod_time})")
    
    resposta = input("\nDeseja eliminar os arquivos duplicados? (s/n): ").lower()
    if resposta == 's':
        manter_recente = input("\nDeseja manter o arquivo mais recente? (s/n): ").lower() == 's'
        eliminar_duplicados(duplicados, manter_mais_recente=manter_recente)
        print("\nDuplicados eliminados com sucesso!")
    else:
        print("\nNenhum arquivo foi removido.")

if __name__ == "__main__":
    main()