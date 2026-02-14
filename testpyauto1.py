import pyautogui
import time
import webbrowser
import cv2

# Configurações iniciais
senha = 'NKVrEBvsE0IwsqPfqI#q'
proxmox_url = "https://168.228.184.154:8006"

def clicar_em_imagem(imagem, tempo_espera=2, tentativas=3):
    """Clica na imagem especificada se estiver presente na tela."""
    for _ in range(tentativas):
        try:
            pos = pyautogui.locateCenterOnScreen(imagem, confidence=0.8)
            if pos:
                pyautogui.click(pos)
                time.sleep(tempo_espera)
                return True
        except pyautogui.ImageNotFoundException:
            print(f"Imagem {imagem} não encontrada. Tentando novamente...")
        time.sleep(1)
    return False

def abrir_proxmox():
    """Abre o Proxmox no navegador."""
    webbrowser.open(proxmox_url)
    time.sleep(10)

def logar_console_maquina(pos_maquina):
    """Abre o console da máquina e insere a senha."""
    pyautogui.doubleClick(pos_maquina)
    time.sleep(5)
    pyautogui.click(pos_maquina)
    time.sleep(3)
    pyautogui.write(senha)
    pyautogui.press('enter')
    print("Máquina UP.")
    time.sleep(8)

def fechar_terminal(pos_icone_fechar):
    """Fecha o terminal usando as coordenadas fornecidas."""
    pyautogui.click(pos_icone_fechar)
    time.sleep(6)

# Execução do script
abrir_proxmox()

# Substitua as coordenadas com as imagens se disponível ou use a função de clique em coordenadas.
clicar_em_imagem('./abenet/botao_login.png', tempo_espera=5) or pyautogui.click(1089, 631)

# Clicar em OK
clicar_em_imagem('./abenet/botao_ok.png', tempo_espera=2) or pyautogui.click(940, 599)

# Abrir o menu de VMs
pyautogui.doubleClick(57, 166)
time.sleep(5)

# Acessar e desbloquear a Máquina 1
logar_console_maquina((122, 369))

# Fechar o console da Máquina 1
fechar_terminal((1006, 20))

# Acessar e desbloquear a Máquina 2
logar_console_maquina((114, 388))

print("Script concluído com sucesso.")
