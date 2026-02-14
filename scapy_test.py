from scapy.all import rdpcap

# Carregar o arquivo PCAP
packets = rdpcap("C:\\Users\\paulo\\Área de Trabalho\\arquivo.pcap")

# Exibir os 5 primeiros pacotes para entender a estrutura
for i, pkt in enumerate(packets[:5]):
    print(f"Pacote {i+1}:")
    pkt.show()
    print("-" * 50)
