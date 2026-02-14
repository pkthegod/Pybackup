def ler_arquivo_txt(caminho):
    """Lê um arquivo TXT e retorna um conjunto de linhas únicas"""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho}' não encontrado.")
        return set()
    except Exception as e:
        print(f"Erro ao ler arquivo '{caminho}': {e}")
        return set()

def combinar_arquivos(txt1, txt2, saida):
    """Combina os arquivos mantendo todos do txt1 e adicionando apenas únicos do txt2"""
    # Ler os arquivos
    conjunto1 = ler_arquivo_txt(txt1)
    conjunto2 = ler_arquivo_txt(txt2)
    
    # Verificar se os arquivos foram lidos corretamente
    if conjunto1 is None or conjunto2 is None:
        return
    
    # Combinar os conjuntos
    combinado = conjunto1.union(conjunto2)
    
    # Escrever o resultado no arquivo de saída
    try:
        with open(saida, 'w', encoding='utf-8') as f:
            for item in sorted(combinado):
                f.write(item + '\n')
        print(f"\nCombinação concluída! Arquivo salvo em: {saida}")
        print(f"Total de itens em {txt1}: {len(conjunto1)}")
        print(f"Total de itens em {txt2}: {len(conjunto2)}")
        print(f"Total de itens únicos combinados: {len(combinado)}")
    except Exception as e:
        print(f"Erro ao salvar arquivo combinado: {e}")

def main():
    # Configurações
    arquivo1 = 'D:\\Documentos\\Servidores\\Python_files\\lista_server.txt'  # Substitua pelo caminho do primeiro arquivo
    arquivo2 = 'arquivo1_sem_duplicados.txt'  # Substitua pelo caminho do segundo arquivo
    saida = 'combinado.txt'    # Arquivo de saída
    
    print("Iniciando combinação de arquivos...")
    combinar_arquivos(arquivo1, arquivo2, saida)

if __name__ == "__main__":
    main()