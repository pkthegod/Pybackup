#!/usr/bin/env python3
import argparse
import socket
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, List

import paramiko


@dataclass
class Target:
    host: str
    port: int
    user: str


def parse_target(line: str, default_user: str, default_port: int) -> Optional[Target]:
    """
    Accepts:
      host
      host:port
      user@host
      user@host:port
    Ignores blank lines and comments (# ...)
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    user = default_user
    hostport = line

    if "@" in line:
        user, hostport = line.split("@", 1)

    host = hostport
    port = default_port
    if ":" in hostport:
        # split on last ':' to avoid issues with weird inputs
        parts = hostport.rsplit(":", 1)
        host = parts[0].strip()
        try:
            port = int(parts[1].strip())
        except ValueError:
            raise ValueError(f"Invalid port in line: {line}")

    return Target(host=host, port=port, user=user)


def tcp_check(host: str, port: int, timeout: float) -> Tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, "tcp_ok"
    except socket.timeout:
        return False, "tcp_timeout"
    except OSError as e:
        return False, f"tcp_error:{e.__class__.__name__}"


def ssh_check(
    t: Target,
    key_path: Path,
    conn_timeout: float,
    auth_timeout: float,
    known_hosts: Path,
    accept_unknown: bool,
    command: str,
    passphrase: Optional[str] = None,
) -> Tuple[bool, str, float]:
    """
    Secure behavior:
      - Uses a dedicated known_hosts file (default: ~/.ssh/known_hosts)
      - If accept_unknown is False: rejects unknown hosts (best practice)
      - If accept_unknown is True: adds unknown hosts to known_hosts (convenient but less strict)
    """
    start = time.time()

    client = paramiko.SSHClient()

    # Load known hosts
    if known_hosts.exists():
        client.load_host_keys(str(known_hosts))
    else:
        # Don't silently create trust; file can be created when accept_unknown=True
        pass

    if accept_unknown:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    else:
        client.set_missing_host_key_policy(paramiko.RejectPolicy())

    # Load ed25519 key (Paramiko supports OpenSSH-format keys; encrypted keys require passphrase)
    try:
        pkey = paramiko.Ed25519Key.from_private_key_file(str(key_path), password=passphrase)
    except paramiko.PasswordRequiredException:
        return False, "key_encrypted_needs_passphrase", time.time() - start
    except paramiko.SSHException as e:
        # Passphrase incorreta ou outro erro SSH
        return False, f"key_load_failed:{str(e)[:60]}", time.time() - start
    except Exception as e:
        return False, f"key_load_failed:{e.__class__.__name__}", time.time() - start

    try:
        client.connect(
            hostname=t.host,
            port=t.port,
            username=t.user,
            pkey=pkey,
            timeout=conn_timeout,
            auth_timeout=auth_timeout,
            banner_timeout=conn_timeout,
            allow_agent=False,
            look_for_keys=False,
        )

        stdin, stdout, stderr = client.exec_command(command, timeout=auth_timeout)
        out = stdout.read().decode(errors="replace").strip()
        err = stderr.read().decode(errors="replace").strip()

        client.close()

        if err and not out:
            return True, f"ok_but_stderr:{err[:120]}", time.time() - start

        # Keep response short but informative
        preview = out[:120] if out else "no_output"
        return True, f"ok:{preview}", time.time() - start

    except paramiko.BadHostKeyException:
        return False, "bad_host_key_mismatch", time.time() - start
    except paramiko.ssh_exception.SSHException as e:
        # includes handshake issues, kex problems, etc.
        return False, f"ssh_exception:{e.__class__.__name__}", time.time() - start
    except socket.timeout:
        return False, "ssh_timeout", time.time() - start
    except Exception as e:
        return False, f"ssh_failed:{e.__class__.__name__}", time.time() - start
    finally:
        try:
            client.close()
        except Exception:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit SSH reachability/auth for a list of servers.")
    ap.add_argument("--list", required=True, help="Path to servers list file (one per line).")
    ap.add_argument("--user", default="root", help="Default SSH username.")
    ap.add_argument("--port", type=int, default=65522, help="Default SSH port.")
    ap.add_argument("--key", default=str(Path.home() / ".ssh" / "id_ed25519"), help="Path to ED25519 private key.")
    ap.add_argument("--passphrase", default=None, help="Passphrase for encrypted SSH key.")
    ap.add_argument("--known-hosts", default=str(Path.home() / ".ssh" / "known_hosts"),
                    help="Known hosts file to trust host keys from.")
    ap.add_argument("--accept-unknown-hosts", action="store_true",
                    help="Auto-add unknown host keys to known-hosts (less strict).")
    ap.add_argument("--tcp-timeout", type=float, default=2.5, help="TCP connect timeout seconds.")
    ap.add_argument("--conn-timeout", type=float, default=4.0, help="SSH connect timeout seconds.")
    ap.add_argument("--auth-timeout", type=float, default=6.0, help="SSH auth/command timeout seconds.")
    ap.add_argument("--command", default="echo OK && hostname && whoami", help="Command to run after login to validate.")
    args = ap.parse_args()

    list_path = Path(args.list).expanduser()
    key_path = Path(args.key).expanduser()
    known_hosts = Path(args.known_hosts).expanduser()

    if not list_path.exists():
        print(f"ERROR: list file not found: {list_path}", file=sys.stderr)
        return 2

    if not key_path.exists():
        print(f"ERROR: key not found: {key_path}", file=sys.stderr)
        return 2

    targets: List[Target] = []
    for raw in list_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            t = parse_target(raw, args.user, args.port)
            if t:
                targets.append(t)
        except ValueError as e:
            print(f"SKIP line parse error: {e}", file=sys.stderr)

    if not targets:
        print("No valid targets found in list.")
        return 1

    ok = 0
    fail = 0

    print(f"Targets: {len(targets)} | default_user={args.user} | default_port={args.port}")
    print(f"Key: {key_path} | known_hosts: {known_hosts} | accept_unknown={args.accept_unknown_hosts}")
    if args.passphrase:
        print(f"Passphrase: *** (provided)")
    print("-" * 80)

    for t in targets:
        tcp_ok, tcp_reason = tcp_check(t.host, t.port, args.tcp_timeout)
        if not tcp_ok:
            fail += 1
            print(f"[FAIL] {t.user}@{t.host}:{t.port} | {tcp_reason}")
            continue

        ssh_ok, reason, elapsed = ssh_check(
            t=t,
            key_path=key_path,
            conn_timeout=args.conn_timeout,
            auth_timeout=args.auth_timeout,
            known_hosts=known_hosts,
            accept_unknown=args.accept_unknown_hosts,
            command=args.command,
            passphrase=args.passphrase,
        )

        if ssh_ok:
            ok += 1
            print(f"[ OK ] {t.user}@{t.host}:{t.port} | {reason} | {elapsed:.2f}s")
        else:
            fail += 1
            print(f"[FAIL] {t.user}@{t.host}:{t.port} | {reason} | {elapsed:.2f}s")

    print("-" * 80)
    print(f"Result: OK={ok} FAIL={fail}")

    return 0 if fail == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())