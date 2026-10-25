"""Bounded public-document retrieval and a persistent local job queue."""
import hashlib
import json
import re
import ssl
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler

from .store import uid, now, dump


ALLOWED_DOMAINS = ("sec.gov", "microsoft.com", "costco.com", "tencent.com",
                   "cninfo.com.cn", "hkexnews.hk", "hkex.com.hk", "byd.com",
                   "catl.com", "cmbchina.com")
MAX_BYTES = 25 * 1024 * 1024


def validate_url(url):
    p = urlparse(url)
    domain = (p.hostname or "").lower()
    if p.scheme != "https" or p.username or p.password or p.port not in (None, 443):
        raise ValueError("仅支持白名单原始来源的HTTPS地址")
    if not any(domain == d or domain.endswith("." + d) for d in ALLOWED_DOMAINS):
        raise ValueError("该域名尚未列入公开原文来源。可先在配置中审阅加入；不抓取任意网址。")
    return url


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def retrieve(url, raw_dir, metadata=None):
    validate_url(url)
    opener = build_opener(SafeRedirect(), HTTPSHandler(context=ssl.create_default_context()))
    request = Request(url, headers={"User-Agent": "PersonalFinancialAnalyses/0.2 personal-public-research", "Accept": "application/pdf,text/html,application/json"})
    with opener.open(request, timeout=25) as response:
        body = response.read(MAX_BYTES + 1)
        content_type = response.headers.get("Content-Type", "").lower()
        final_url = validate_url(response.url)
    if len(body) > MAX_BYTES:
        raise ValueError("原文超过25MB，本地首版请采用受控离线资料包")
    if not body:
        raise ValueError("来源返回空正文")
    extension = ".pdf" if body.startswith(b"%PDF") else ".json" if "json" in content_type else ".html"
    if extension == ".json":
        json.loads(body)
    if extension == ".html" and (b"access denied" in body[:2000].lower() or b"captcha" in body[:2000].lower()):
        raise ValueError("来源返回访问限制，不能当作财报正文")
    sha = hashlib.sha256(body).hexdigest()
    path = Path(raw_dir) / (sha + extension)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    result = dict(metadata or {}, url=url, resolved_url=final_url, sha256=sha,
                  local_path=str(path.resolve()), retrieved_at=now(), content_type=content_type)
    result.setdefault("title", urlparse(url).path.rsplit("/", 1)[-1] or "公开资料")
    return result


def document_text(document, root, page=1):
    path = Path(document.get("local_path", ""))
    if path.is_absolute() and "data/raw/" in str(path):
        path = Path(root)/"data/raw"/str(path).split("data/raw/",1)[1]
    if not path.is_absolute():
        path = Path(root)/path
    path = path.resolve()
    raw_root = (Path(root)/"data"/"raw").resolve()
    if raw_root not in path.parents or not path.is_file():
        raise ValueError("本地原件不存在。请从原文链接重新获取；未用缓存冒充原件。")
    body = path.read_bytes()
    if hashlib.sha256(body).hexdigest() != document["sha256"]:
        raise ValueError("原件校验值不匹配，停止将该文件用于核验")
    if body.startswith(b"%PDF"):
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ValueError("请安装 requirements.txt 中的pypdf，原文链接仍可使用") from None
        reader = PdfReader(str(path))
        if not 1 <= page <= len(reader.pages):
            raise ValueError("页码超出原文范围")
        sheet = reader.pages[page-1]
        stream = sheet.get_contents()
        if stream and len(stream.get_data()) > 8*1024*1024:
            raise ValueError("此页内容过大，请回看原始PDF页图")
        text = sheet.extract_text(extraction_mode="layout") or ""
        return dict(text=text[:150000], page=page, pages=len(reader.pages),
                    note="PDF抽取辅助定位；表格与字体映射可能有误，应回看原页，不自动核验。")
    text = body.decode("utf-8", errors="replace")
    if path.suffix == ".json":
        text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
    else:
        text = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", "", text, flags=re.S|re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
    # Chunks are character windows for HTML/JSON, not printed filing pages.
    width = 18000
    pages = max(1, (len(text)+width-1)//width)
    if not 1 <= page <= pages:
        raise ValueError("片段超出正文范围")
    return dict(text=text[(page-1)*width:page*width], page=page, pages=pages,
                note="HTML/JSON按字符分段，并非印刷页码。事实仍需具体原文定位。")


class Jobs:
    def __init__(self, research, root):
        self.research, self.store, self.root = research, research.store, Path(root)

    def enqueue(self, issuer, data):
        url = validate_url(data["url"])
        with self.store.tx() as db:
            self.research.issuer(db, issuer)
            self.research.expect(db, issuer, data.get("expected_revision"))
            active = db.execute("SELECT id,payload FROM jobs WHERE issuer=? AND status IN ('queued','running')", (issuer,))
            for row in active:
                if json.loads(row["payload"])["url"] == url:
                    return dict(id=row["id"], deduplicated=True)
            ident = uid("job")
            payload = {k:v for k,v in data.items() if k != "expected_revision"}
            db.execute("INSERT INTO jobs VALUES (?,?,?,'queued',0,NULL,?,?)",
                       (ident, issuer, dump(payload), now(), now()))
            self.store.log(db, issuer, "排队获取公开资料", {"job_id": ident, "url": url, "gap_key": data.get("gap_key")})
            return dict(id=ident)

    def recover(self):
        with self.store.tx() as db:
            db.execute("UPDATE jobs SET status='failed',error='上次运行中断且已达三次尝试，需人工处理',updated_at=? WHERE status='running' AND attempts>=3", (now(),))
            db.execute("UPDATE jobs SET status='queued',error='上次运行中断，等待恢复',updated_at=? WHERE status='running' AND attempts<3", (now(),))

    def one(self):
        with self.store.tx() as db:
            row = db.execute("SELECT * FROM jobs WHERE issuer IN (SELECT id FROM records WHERE kind='issuer') AND status='queued' AND attempts<3 ORDER BY created_at LIMIT 1").fetchone()
            if row is None:
                return False
            row = dict(row)
            db.execute("UPDATE jobs SET status='running',attempts=attempts+1,updated_at=? WHERE id=?", (now(), row["id"]))
        data = json.loads(row["payload"])
        try:
            metadata = {k:v for k,v in data.items() if k in ("title", "published_at", "period_start", "period_end", "currency", "basis", "scope")}
            doc = retrieve(data["url"], self.root/"data/raw/fetched", metadata)
            doc["local_path"] = str(Path(doc["local_path"]).relative_to(self.root))
            with self.store.tx() as db:
                item = self.research.import_document(db, row["issuer"], doc)
                db.execute("UPDATE jobs SET status='succeeded',error=NULL,updated_at=? WHERE id=?", (now(), row["id"]))
                self.store.log(db, row["issuer"], "资料获取完成，待提取核验", {"job_id": row["id"], "document_id": item["id"], "gap_key": data.get("gap_key")})
        except Exception as exc:
            with self.store.tx() as db:
                # Retries are explicit, bounded and visible; avoid hammering an unavailable public source.
                db.execute("UPDATE jobs SET status='failed',error=?,updated_at=? WHERE id=?", (str(exc)[:1000], now(), row["id"]))
                self.store.log(db, row["issuer"], "资料获取失败", {"job_id": row["id"], "reason": str(exc)[:1000]})
        return True

    def retry(self, issuer, data):
        with self.store.tx() as db:
            self.research.expect(db, issuer, data.get("expected_revision"))
            row = db.execute("SELECT * FROM jobs WHERE id=? AND issuer=?", (data["job_id"], issuer)).fetchone()
            if not row or row["status"] != "failed" or row["attempts"] >= 3:
                raise ValueError("仅允许失败任务重试，总计不超过三次")
            db.execute("UPDATE jobs SET status='queued',updated_at=? WHERE id=?", (now(), row["id"]))
            self.store.log(db, issuer, "重试资料获取", {"job_id": row["id"]})
