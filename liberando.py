def ler_arquivo_txt(caminho):
    """Lê um arquivo TXT e retorna uma lista de linhas"""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return [linha.strip() for linha in f if linha.strip()]
    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho}' não encontrado.")
        return []
    except Exception as e:
        print(f"Erro ao ler arquivo '{caminho}': {e}")
        return []

def remover_correspondencias(arquivo1, arquivo2, saida):
    """
    Remove do primeiro arquivo todas as linhas que contêm qualquer string do segundo arquivo.
    """
    # Ler os arquivos
    linhas_arquivo1 = ler_arquivo_txt(arquivo1)
    linhas_arquivo2 = ler_arquivo_txt(arquivo2)
    
    # Verificar se os arquivos foram lidos corretamente
    if not linhas_arquivo1 or not linhas_arquivo2:
        return
    
    # Filtrar linhas do arquivo 1 que NÃO contêm nenhuma string do arquivo 2
    linhas_filtradas = [
        linha for linha in linhas_arquivo1
        if not any(correspondencia in linha for correspondencia in linhas_arquivo2)
    ]
    
    # Escrever o resultado no arquivo de saída
    try:
        with open(saida, 'w', encoding='utf-8') as f:
            for linha in linhas_filtradas:
                f.write(linha + '\n')
        
        print(f"\nProcesso concluído! Arquivo salvo em: {saida}")
        print(f"Total de linhas no arquivo 1: {len(linhas_arquivo1)}")
        print(f"Total de correspondências no arquivo 2: {len(linhas_arquivo2)}")
        print(f"Total de linhas no arquivo de saída: {len(linhas_filtradas)}")
        print(f"Linhas removidas: {len(linhas_arquivo1) - len(linhas_filtradas)}")
    except Exception as e:
        print(f"Erro ao salvar arquivo: {e}")

def main():
    # Configurações
    arquivo1 = 'combinado.txt'  # Substitua pelo caminho do primeiro arquivo
    arquivo2 = 'dominios_liberados.txt'  # Substitua pelo caminho do segundo arquivo
    saida = 'filtrado.txt'  # Arquivo de saída
    
    print("Iniciando remoção de correspondências...")
    remover_correspondencias(arquivo1, arquivo2, saida)

if __name__ == "__main__":
    main()