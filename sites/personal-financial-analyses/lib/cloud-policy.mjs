export const MAX_BLOB = 25 * 1024 * 1024;
export const shaPattern = /^[a-f0-9]{64}$/;
export function allowedUrl(input) {
  const u = new URL(input);
  const companies=['sec.gov','microsoft.com','costco.com','tencent.com','cninfo.com.cn','hkexnews.hk','hkex.com.hk','byd.com','catl.com','cmbchina.com'];
  const host=u.hostname.toLowerCase();
  const document=companies.some(d=>host===d||host.endsWith('.'+d));
  const selected=host==='query1.finance.yahoo.com'&&u.pathname.startsWith('/v8/finance/chart/') ||
    host==='fred.stlouisfed.org'&&u.pathname==='/graph/fredgraph.csv' ||
    host==='www.federalreserve.gov'&&u.pathname==='/feeds/press_all.xml';
  if(u.protocol!=='https:'||u.username||u.password||(u.port&&u.port!=='443')||!(document||selected))throw new Error('不允许此来源地址');
  return u.toString();
}
export function validateManifest(files) {
  if(!Array.isArray(files)||files.length>500)throw new Error('原件目录无效或过大');
  const seen=new Set();
  for(const f of files){
    if(!f||typeof f.path!=='string'||!/^data\/(raw|market\/raw|information\/raw)\/[A-Za-z0-9_./-]+$/.test(f.path)||f.path.split('/').some(x=>!x||x==='.'||x==='..')||!shaPattern.test(f.sha256)||!Number.isSafeInteger(f.bytes)||f.bytes<1||f.bytes>MAX_BLOB||seen.has(f.path))throw new Error('原件路径、摘要或大小无效');
    seen.add(f.path);
  }
  return files;
}
export function validateMutation(request) {
  const origin=request.headers.get('Origin');
  if(request.headers.get('X-PFA-Request')!=='1'||(origin&&origin!==new URL(request.url).origin)||request.headers.get('Sec-Fetch-Site')==='cross-site')throw new Error('不允许跨站或未标识的修改');
}
export async function boundedBody(response,max=MAX_BLOB){
  const content=Number(response.headers.get('Content-Length'));
  if(content>max)throw new Error('响应超过大小上限');
  if(!response.body)throw new Error('来源返回空正文');
  const reader=response.body.getReader(),chunks=[];let size=0;
  for(;;){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>max){await reader.cancel();throw new Error('响应超过大小上限');}chunks.push(value);}
  if(!size)throw new Error('来源返回空正文');
  const bytes=new Uint8Array(size);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length;}return bytes;
}
export async function sha256(bytes){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');}
