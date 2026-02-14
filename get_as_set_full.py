import requests
import argparse
import json

# Função para buscar e exibir informações do ASN usando a API do PeeringDB
def get_asn_info(asn):
    # Faz a requisição para a API do PeeringDB usando o ASN fornecido
    response = requests.get(f'https://www.peeringdb.com/api/net?asn={asn}')
    
    # Verifica se a requisição foi bem-sucedida
    if response.status_code == 200:
        # Carrega a resposta JSON
        data = response.json()
        
        # Exibe o JSON completo formatado com indentação para facilitar a leitura
        print(json.dumps(data, indent=4))
    else:
        print(f"Erro ao acessar a API: {response.status_code}")

# Função principal que captura o argumento da linha de comando
def main():
    # Configura o argparse para receber o ASN como argumento
    parser = argparse.ArgumentParser(description="Obter informações sobre um ASN usando a API do PeeringDB.")
    parser.add_argument('asn', type=int, help='Número do ASN a ser consultado')

    # Captura o argumento inserido pelo usuário
    args = parser.parse_args()

    # Chama a função que busca as informações do ASN
    get_asn_info(args.asn)

# Execução do script
if __name__ == "__main__":
    main()
