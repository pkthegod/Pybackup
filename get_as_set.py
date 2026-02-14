import requests
import argparse

# Função para buscar informações de uma rede específica usando a API do PeeringDB
def get_asn_info(asn):
    # Faz a requisição para a API usando o ASN fornecido
    response = requests.get(f'https://www.peeringdb.com/api/net?asn={asn}')
    
    # Verifica se a requisição foi bem-sucedida
    if response.status_code == 200:
        data = response.json()
        
        # Verifica se há dados para o ASN fornecido
        if data['data']:
            # Exibe as informações da rede
            for net in data['data']:
                print(f"Nome: {net['name']}")
                print(f"ASN: {net['asn']}")
                print(f"Política de Peering: {net['policy_general']}")
        else:
            print(f"Nenhum dado encontrado para o ASN: {asn}")
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