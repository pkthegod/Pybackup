import pyautogui
import time
import webbrowser

senha='NKVrEBvsE0IwsqPfqI#q'
# Configurações iniciais
proxmox_url = "https://168.228.184.154:8006"  # Substitua pelo endereço do Proxmox
#senha = "sua_senha"  # Substitua pela sua senha

# Passo 1: Abrir o navegador e acessar o Proxmox
webbrowser.open(proxmox_url)
time.sleep(10)  # Tempo para o navegador carregar o Proxmox

pyautogui.click(1089,631)
time.sleep(5)

pyautogui.click(940,599)
time.sleep(2)

# Passo 2: Navegar e clicar no console
# Ajuste as coordenadas abaixo de acordo com a posição do botão "Console" no Proxmox
pyautogui.doubleClick(57,166)  # Clique nas coordenadas do botão Console
time.sleep(5)  # Espera o console abrir

pyautogui.doubleClick(122,369)
time.sleep(5)

pyautogui.click(122,369)
time.sleep(2)

# Passo 3: Inserir a senha e apertar Enter
pyautogui.write(senha)  # Digita a senha
pyautogui.press('enter')  # Pressiona Enter

print("Automação concluída.")
