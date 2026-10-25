export const dynamic='force-dynamic';
export async function GET(request:Request,{params}:any){
 const {issuer}=await params;if(!/^[a-z0-9_]+$/.test(issuer))return new Response('报告标识无效',{status:400});
 return new Response(`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>正在生成研究报告 · PFA</title><link rel="stylesheet" href="/styles.css"><body data-report="${issuer}"><main id="report-document"><p id="cloud-status" role="status">正在加载同版本研究内核与云端证据…</p></main><script src="/standalone.js" defer></script></body></html>`,{headers:{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; connect-src 'self'; worker-src 'self'; base-uri 'none'; frame-ancestors 'none'"}});
}
