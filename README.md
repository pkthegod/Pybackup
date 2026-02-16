# SSH Audit Tool

Script Python para auditoria automatizada de acesso SSH em múltiplos servidores Linux.

## Descrição

Ferramenta que testa conectividade TCP e autenticação SSH em uma lista de servidores, retornando resultados estruturados em JSON. Útil para validar acessos, detectar problemas de conectividade e automatizar verificações de infraestrutura.

## Requisitos

```bash
pip install paramiko
```

## Uso Básico

```bash
# Teste com ssh-agent (recomendado)
python ssh_audit.py --list servidores.txt --use-agent --accept-unknown-hosts

# Gerar relatório JSON
python ssh_audit.py --list servidores.txt --use-agent --json-output resultado.json

# Apenas saída JSON
python ssh_audit.py --list servidores.txt --use-agent --json-only > resultado.json
```

## Formato do Arquivo de Servidores

```txt
# Uma entrada por linha
192.168.1.100
192.168.1.101:2222
admin@192.168.1.102
root@192.168.1.103:22
```

## Formato de Saída JSON

```json
{
  "summary": {
    "total": 10,
    "success": 7,
    "failed": 3,
    "timestamp": "2024-02-14 15:30:45"
  },
  "success": [
    {
      "target": "root@192.168.1.100:22",
      "response": "ok:OK\\nserver01\\nroot",
      "elapsed_seconds": 1.23
    }
  ],
  "failed": [
    {
      "target": "root@192.168.1.102:22",
      "error_code": "tcp_timeout",
      "error_type": "tcp"
    }
  ]
}
```

## Principais Funcionalidades

- ✅ Teste de conectividade TCP
- ✅ Autenticação SSH com chave ED25519
- ✅ Suporte a ssh-agent
- ✅ Saída estruturada em JSON
- ✅ Códigos de erro detalhados
- ✅ Timeouts configuráveis
- ✅ Suporte a múltiplos usuários e portas

## Opções Principais

```bash
--list              # Arquivo com lista de servidores (obrigatório)
--user              # Usuário SSH padrão (default: root)
--port              # Porta SSH padrão (default: 65522)
--use-agent         # Usar ssh-agent para autenticação
--passphrase        # Passphrase da chave SSH
--accept-unknown-hosts  # Aceitar hosts desconhecidos
--json-output       # Salvar resultado em arquivo JSON
--json-only         # Saída apenas JSON (sem progresso)
```

## Exemplo com PowerShell

```powershell
# Executar audit
python ssh_audit.py --list servers.txt --use-agent --json-output result.json

# Analisar resultados
$r = Get-Content result.json | ConvertFrom-Json
$r.summary
$r.failed | Format-Table
```

## Licença

MIT
