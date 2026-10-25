"""Loopback-only JSON API and a responsive research workbench."""
import argparse
import json
import mimetypes
import secrets
import threading
import os
import sqlite3
import signal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from .research import Research, Conflict
from .sources import Jobs, document_text
from .store import Store
from . import __version__
from .assurance import RUNNING_KERNEL
from .markets import MarketBook
from .platform import Platform


ROOT = Path(__file__).resolve().parents[1]


def make_server(research, jobs, port=8765, instance_id="unmanaged", worker=None, markets=None, information=None):
    token = secrets.token_urlsafe(32)
    markets = markets or MarketBook(research.store)
    platform = Platform(research, markets)
    information = information or platform.information
    class Handler(BaseHTTPRequestHandler):
        server_version = "PersonalFinancialAnalyses/" + __version__

        def log_message(self, fmt, *args):
            if str(args[1] if len(args)>1 else "").startswith("5"):
                super().log_message(fmt, *args)

        def send(self, status, value, content_type="application/json; charset=utf-8", content_policy=None):
            body = json.dumps(value, ensure_ascii=False).encode() if content_type.startswith("application/json") else value
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", content_policy or "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get("Host") in (f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}")

        def do_GET(self):
            if not self.valid_host():
                return self.send(403, {"error": "仅允许本地访问"})
            url = urlparse(self.path)
            parts = url.path.strip("/").split("/")
            try:
                if url.path == "/api/healthz":
                    with sqlite3.connect(str(research.store.path), timeout=1) as db:
                        db.execute("SELECT COUNT(*) FROM records").fetchone()
                    alive = worker.is_alive() if worker is not None else True
                    return self.send(200 if alive else 503, dict(
                        status="ready" if alive else "degraded", version=__version__,
                        kernel_digest=RUNNING_KERNEL,
                        instance_id=instance_id, pid=os.getpid(), database="readable",
                        worker="running" if worker is not None and alive else "not_attached"))
                if url.path == "/api/bootstrap":
                    return self.send(200, dict(csrf=token, companies=research.dashboard(), version=__version__, ai="规则与人工审议；未配置外部模型服务"))
                if len(parts)==2 and parts[0]=='reports':
                    from .report_document import document,content_policy
                    html=document(platform.report(parts[1]))
                    return self.send(200,html.encode(),'text/html; charset=utf-8',content_policy(html))
                if url.path == "/api/platform":
                    return self.send(200, platform.overview())
                if parts[0]=='research':
                    from .publications import publication
                    item=publication(url.path)
                    if item is None:return self.send(404,{'error':'报告不存在'})
                    html,policy=item
                    return self.send(200,html,'text/html; charset=utf-8',policy)
                if url.path == "/api/industries":
                    return self.send(200, platform.industries())
                if url.path == "/api/markets":
                    return self.send(200, markets.read())
                if url.path == "/api/knowledge":
                    return self.send(200, platform.knowledge.read())
                if url.path == "/api/information":
                    return self.send(200, information.read())
                if len(parts) == 3 and parts[:2] == ["api", "reports"]:
                    return self.send(200, platform.report(parts[2]))
                if len(parts)==4 and parts[:2]==['api','reports'] and parts[3]=='document':
                    from .report_document import document
                    return self.send(200,dict(html=document(platform.report(parts[2]))))
                if len(parts)==3 and parts[:2]==['api','report-versions']:
                    from .report_document import document
                    with research.store.tx() as db:
                        snapshot=research.store.get(db,parts[2])
                    if snapshot['kind']!='research_report':raise ValueError('研究报告版本不存在')
                    return self.send(200,dict(html=document(snapshot['report']),version=snapshot['version']))
                if len(parts) == 3 and parts[:2] == ["api", "library"]:
                    return self.send(200, platform.library(parts[2]))
                if len(parts) == 3 and parts[:2] == ["api", "companies"]:
                    return self.send(200, research.view(parts[2]))
                if len(parts) == 3 and parts[:2] == ["api", "documents"]:
                    with research.store.tx() as db:
                        doc = research.store.get(db, parts[2])
                        if doc["kind"] != "document":
                            raise ValueError("资料不存在")
                    return self.send(200, document_text(doc, ROOT, int(parse_qs(url.query).get("page", [1])[0])))
                if len(parts) == 3 and parts[:2] == ["api", "export"]:
                    return self.send(200, research.view(parts[2]))
                assets = {"/": "index.html", "/app.js": "app.js", "/workspace.js": "workspace.js", "/evolution.js": "evolution.js", "/styles.css": "styles.css"}
                if url.path not in assets:
                    return self.send(404, {"error": "地址不存在"})
                path = ROOT/"static"/assets[url.path]
                return self.send(200, path.read_bytes(), (mimetypes.guess_type(str(path))[0] or "text/plain")+"; charset=utf-8")
            except (ValueError, KeyError) as exc:
                self.send(400, {"error": str(exc)})
            except Exception:
                self.send(500, {"error": "本地服务读取失败，请查看终端"})
                raise

        def do_POST(self):
            if not self.valid_host() or not secrets.compare_digest(self.headers.get("X-PFA-Token", ""), token):
                return self.send(403, {"error": "本地请求校验失败，请刷新应用"})
            origin = self.headers.get("Origin")
            if origin and origin not in (f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"):
                return self.send(403, {"error": "不允许跨站修改"})
            try:
                size = int(self.headers.get("Content-Length", 0))
                if not 0 < size <= 200000:
                    raise ValueError("请求大小不合适")
                if not self.headers.get("Content-Type", "").startswith("application/json"):
                    raise ValueError("需要JSON请求")
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError("请求应是JSON对象")
                parts = urlparse(self.path).path.strip("/").split("/")
                if parts == ["api", "markets", "refresh"]:
                    return self.send(200, {"result": markets.enqueue()})
                if parts == ["api", "information", "refresh"]:
                    return self.send(200, {"result": information.enqueue()})
                if parts == ["api", "knowledge"]:
                    return self.send(200, {"result": platform.knowledge.save(data)})
                if len(parts)==4 and parts[:2]==["api","reports"] and parts[3]=='snapshot':
                    return self.send(200, {"result": platform.save_report(parts[2],data)})
                if len(parts) != 4 or parts[:2] != ["api", "companies"]:
                    return self.send(404, {"error": "地址不存在"})
                issuer, action = parts[2:]
                if action == "fetch":
                    result = jobs.enqueue(issuer, data)
                elif action == "retry":
                    result = jobs.retry(issuer, data)
                else:
                    result = research.command(issuer, action, data)
                return self.send(200, {"result": result})
            except Conflict as exc:
                self.send(409, {"error": str(exc)})
            except (ValueError, KeyError, TypeError) as exc:
                self.send(400, {"error": str(exc)})
            except Exception:
                self.send(500, {"error": "本次修改失败，事务已回滚，请查看终端"})
                raise

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description="Personal Financial Analyses local research terminal")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", default=str(ROOT/"data/pfa.sqlite3"))
    parser.add_argument("--instance-id", default="foreground")
    args = parser.parse_args()
    research = Research(Store(args.db))
    research.seed(ROOT/"fixtures/companies.json")
    jobs = Jobs(research, ROOT)
    markets = MarketBook(research.store)
    from .information import Information
    information = Information(research.store,ROOT)
    jobs.recover()
    stopping = threading.Event()
    def work():
        while not stopping.is_set():
            try:
                if markets.one() or information.one() or jobs.one():
                    continue
            except Exception as exc:
                print("Background job error:", exc, flush=True)
            stopping.wait(2)
    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    server = make_server(research, jobs, args.port, args.instance_id, worker, markets, information)
    def terminate(signum, frame):
        stopping.set()
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, terminate)
    print(f"Personal Financial Analyses http://127.0.0.1:{server.server_port}", flush=True)
    print("Local only · public evidence · no external AI service or paid data", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stopping.set()
        server.server_close()


if __name__ == "__main__":
    main()
