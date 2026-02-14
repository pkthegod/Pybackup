def ler_arquivo_txt(caminho, encoding='utf-8', case_insensitive=False, debug=False):
    """Lê um arquivo TXT e retorna um dicionário {linha_normalizada: linha_original} ou um conjunto"""
    try:
        with open(caminho, 'r', encoding=encoding) as f:
            if case_insensitive:
                # Dicionário para manter o caso original e evitar duplicatas case-insensitive
                linhas = {}
                for line in f:
                    linha_original = line.rstrip('\n\r')
                    if linha_original:
                        chave = linha_original.lower()
                        if chave not in linhas:  # Mantém a primeira ocorrência
                            linhas[chave] = linha_original
            else:
                # Conjunto para comparação case-sensitive
                linhas = set()
                for line in f:
                    linha = line.rstrip('\n\r')
                    if linha:
                        linhas.add(linha)
            
            if debug:
                print(f"\nDebug - Arquivo: {caminho}")
                print(f"Formato: {'Case-insensitive' if case_insensitive else 'Case-sensitive'}")
                print(f"Total de linhas únicas: {len(linhas)}")
                if linhas:
                    print("Amostra de 5 linhas (com repr()):")
                    amostra = list(linhas.values())[:5] if case_insensitive else list(linhas)[:5]
                    for linha in amostra:
                        print(f"  {repr(linha)}")
            
            return linhas
            
    except FileNotFoundError:
        print(f"Erro: Arquivo '{caminho}' não encontrado.")
        return {} if case_insensitive else set()
    except Exception as e:
        print(f"Erro ao ler arquivo '{caminho}': {e}")
        return {} if case_insensitive else set()

def remover_linhas_duplicadas(arquivo1, arquivo2, saida, case_insensitive=False, encoding='utf-8', debug=False):
    """Remove do arquivo1 as linhas presentes no arquivo2 com várias opções"""
    # Ler arquivos
    linhas_arquivo1 = ler_arquivo_txt(arquivo1, encoding, case_insensitive, debug)
    linhas_arquivo2 = ler_arquivo_txt(arquivo2, encoding, True, debug)  # Sempre lê arquivo2 como case-insensitive

    # Validar leitura
    if not linhas_arquivo1 or not linhas_arquivo2:
        print("Erro na leitura dos arquivos. Verifique acima.")
        return

    # Calcular linhas únicas
    if case_insensitive:
        # Extrair chaves normalizadas
        chaves_arquivo1 = set(linhas_arquivo1.keys())
        chaves_arquivo2 = set(linhas_arquivo2.keys())
        chaves_unicas = chaves_arquivo1 - chaves_arquivo2
        linhas_unicas = [linhas_arquivo1[chave] for chave in sorted(chaves_unicas)]
    else:
        # Comparação direta case-sensitive
        linhas_unicas = sorted(linhas_arquivo1 - linhas_arquivo2)

    # Escrever resultado
    try:
        with open(saida, 'w', encoding=encoding) as f:
            for linha in linhas_unicas:
                f.write(f"{linha}\n")
        
        # Estatísticas
        print("\n" + "="*50)
        print(f"Arquivo gerado: {saida}")
        print(f"Configuração: {'Case-insensitive' if case_insensitive else 'Case-sensitive'}")
        print(f"Linhas em {arquivo1}: {len(linhas_arquivo1)}")
        print(f"Linhas em {arquivo2}: {len(linhas_arquivo2)}")
        print(f"Linhas removidas: {len(linhas_arquivo1) - len(linhas_unicas)}")
        print(f"Linhas restantes: {len(linhas_unicas)}")
        
        if debug:
            print("\nDebug - Sobreposição de linhas (5 primeiras):")
            if case_insensitive:
                sobreposicao = set(linhas_arquivo1.keys()) & set(linhas_arquivo2.keys())
            else:
                sobreposicao = linhas_arquivo1 & linhas_arquivo2
            for linha in list(sobreposicao)[:5]:
                print(f"  {repr(linha)}")

    except Exception as e:
        print(f"Erro ao salvar arquivo: {e}")

def main():
    # Configurações
    config = {
        'arquivo1': 'C:\\Users\\paulo\\combinado.txt',
        'arquivo2': 'D:\\Documentos\\Servidores\\Python_files\\dominios_liberados.txt',
        'saida': 'D:\\Documentos\\Servidores\\Python_files\\resultado.txt',
        'case_insensitive': True,  # Ative/desative conforme necessidade
        'encoding': 'utf-8',       # Altere para 'latin-1' se necessário
        'debug': True              # Mostra detalhes da execução
    }

    print(f"\nIniciando processamento...")
    remover_linhas_duplicadas(
        config['arquivo1'],
        config['arquivo2'],
        config['saida'],
        case_insensitive=config['case_insensitive'],
        encoding=config['encoding'],
        debug=config['debug']
    )

if __name__ == "__main__":
    main()