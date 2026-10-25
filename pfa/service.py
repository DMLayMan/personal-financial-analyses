"""Owned local background service. No login item or OS service is installed."""
import argparse
import fcntl
import json
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "data/runtime"
STATE = RUNTIME / "service.json"
_OWNED_CHILDREN = {}


def probe(port):
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/healthz", timeout=2) as response:
            return json.load(response)
    except (OSError, ValueError):
        return None


def load():
    try:
        return json.loads(STATE.read_text())
    except (FileNotFoundError, ValueError):
        return None


def status():
    saved = load()
    if not saved:
        return dict(status="stopped", reason="没有本项目的服务记录")
    health = probe(saved["port"])
    if health and health.get("instance_id") == saved["instance_id"]:
        return dict(status=health["status"], url=f"http://127.0.0.1:{saved['port']}",
                    pid=saved["pid"], health=health, log=saved["log"])
    return dict(status="unavailable", reason="服务未响应或实例不匹配", recorded_pid=saved["pid"], log=saved["log"])


def port_occupied(port):
    with socket.socket() as sock:
        sock.settimeout(.3)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def start(port=8765, db_path=None):
    existing = status()
    if existing["status"] == "ready":
        return existing
    if port_occupied(port):
        raise ValueError(f"端口{port}已被其他进程占用；不会关闭或覆盖它")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    instance_id = secrets.token_hex(16)
    log = RUNTIME / "server.log"
    interpreter = ROOT / ".venv/bin/python"
    if not interpreter.is_file():
        interpreter = Path(sys.executable)
    command = [str(interpreter), "-m", "pfa.server", "--port", str(port), "--instance-id", instance_id]
    if db_path is not None:
        command += ["--db", str(db_path)]
    with log.open("ab") as stream:
        child = subprocess.Popen(command, cwd=str(ROOT),
                                 stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                                 start_new_session=True)
    _OWNED_CHILDREN[child.pid] = child
    saved = dict(pid=child.pid, port=port, instance_id=instance_id,
                 log=str(log), started_at=time.time())
    temporary = STATE.with_suffix(".tmp")
    temporary.write_text(json.dumps(saved, ensure_ascii=False, indent=2)+"\n")
    temporary.replace(STATE)
    for _ in range(50):
        result = status()
        if result["status"] == "ready":
            return result
        if child.poll() is not None:
            raise ValueError("服务启动失败，请查看data/runtime/server.log")
        time.sleep(.2)
    raise ValueError("服务尚未就绪，请检查status和data/runtime/server.log；未另开第二个进程")


def stop():
    saved = load()
    if not saved:
        return dict(status="stopped")
    health = probe(saved["port"])
    if not port_occupied(saved["port"]):
        STATE.unlink(missing_ok=True)
        return dict(status="stopped", reason="先前服务已退出；清理本项目失效记录，未发送信号")
    # Even a recycled PID cannot authorize stopping another process.
    if not health or health.get("instance_id") != saved["instance_id"] or health.get("pid") != saved["pid"]:
        raise ValueError("无法验证进程归属，未发送停止信号；请检查status与日志")
    os.kill(saved["pid"], signal.SIGTERM)
    for _ in range(40):
        if not port_occupied(saved["port"]):
            child = _OWNED_CHILDREN.pop(saved["pid"], None)
            if child is not None:
                child.wait(timeout=5)
            STATE.unlink(missing_ok=True)
            return dict(status="stopped")
        time.sleep(.1)
    raise ValueError("停止尚未完成，未强制终止其他进程")


def doctor(port=8765):
    checks = []
    for route in ("/api/healthz", "/", "/app.js", "/workspace.js", "/evolution.js", "/api/bootstrap", "/api/platform", "/api/knowledge", "/api/markets", "/api/information", "/api/industries", "/api/reports/catl", "/api/companies/catl"):
        try:
            with urlopen(f"http://127.0.0.1:{port}{route}", timeout=5) as response:
                body = response.read()
                valid = response.status == 200 and bool(body)
                if route.startswith('/api/'):
                    result = json.loads(body)
                    valid &= result.get('status') == 'ready' if route.endswith('healthz') else 'error' not in result
                checks.append(dict(route=route, passed=bool(valid)))
        except (OSError, ValueError) as exc:
            checks.append(dict(route=route, passed=False, error=str(exc)))
    return dict(passed=all(c['passed'] for c in checks), checks=checks)


def main():
    parser = argparse.ArgumentParser(description="Personal Financial Analyses local service")
    parser.add_argument("action", choices=["start", "status", "stop", "restart", "doctor"])
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    RUNTIME.mkdir(parents=True, exist_ok=True)
    try:
        with (RUNTIME/"control.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if args.action == 'start': result=start(args.port)
            elif args.action == 'stop': result=stop()
            elif args.action == 'restart':
                if load(): stop()
                result=start(args.port)
            elif args.action == 'doctor': result=doctor(args.port)
            else: result=status()
        print(json.dumps(result, ensure_ascii=False))
        if result.get('passed') is False or result.get('status') in ('unavailable','degraded'):
            raise SystemExit(1)
    except ValueError as exc:
        print(json.dumps(dict(error=str(exc)), ensure_ascii=False))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
