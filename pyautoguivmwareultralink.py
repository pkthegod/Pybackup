import pyautogui
import time
import webbrowser
import cv2

# Configurações iniciais
senha = 'NKVrEBvsE0IwsqPfqI#q'
proxmox_url = "https://179.48.72.0:65081/ui/#/login"

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

def abrir_vmware7():
    """Abre o Proxmox no navegador."""
    webbrowser.open(proxmox_url)
    time.sleep(15)

def logar_console_maquina(pos_maquina):
    """Abre o console da máquina e insere a senha."""
    pyautogui.click(pos_maquina)
    time.sleep(6)
    pyautogui.write(senha)
    pyautogui.press('enter')
    print("Máquina UP.")
    time.sleep(8)

def fechar_terminal(pos_terminal):
    """Fecha o terminal usando as coordenadas fornecidas."""
    pyautogui.click(pos_terminal)
    time.sleep(6)

def selecionar_terminal(pos_terminal):
    """Fecha o terminal usando as coordenadas fornecidas."""
    pyautogui.click(pos_terminal)
    time.sleep(5)
    pyautogui.click(pos_terminal)
    time.sleep(5)

# Execução do script
abrir_vmware7()

# Substitua as coordenadas com as imagens se disponível ou use a função de clique em coordenadas.
clicar_em_imagem('./ultralink/login1.png', tempo_espera=5) or pyautogui.click(249,526)
time.sleep(4)

# Abrir o menu de VMs
pyautogui.doubleClick(120, 237)
time.sleep(6)
# Abrir o console da Máquina 1
selecionar_terminal((363, 234))
time.sleep(4)

logar_console_maquina((363, 234))
time.sleep(7)

pyautogui.click(1047,148)

pyautogui.doubleClick(120, 237)
time.sleep(6)
# Abrir o console da Máquina 2
selecionar_terminal((398,260))
time.sleep(4)

logar_console_maquina((398,260))
time.sleep(7)

pyautogui.click(1047,148)

pyautogui.doubleClick(120, 237)
time.sleep(6)
# Abrir o console da Máquina 2
selecionar_terminal((344, 285))
time.sleep(4)

logar_console_maquina((344, 285))
time.sleep(7)

pyautogui.click(1047,148)

pyautogui.doubleClick(120, 237)
time.sleep(6)
# Abrir o console da Máquina 2
selecionar_terminal((375,411))
time.sleep(4)

logar_console_maquina((375,411))
time.sleep(7)

pyautogui.click(1047,148)

print("Script concluído com sucesso.")
