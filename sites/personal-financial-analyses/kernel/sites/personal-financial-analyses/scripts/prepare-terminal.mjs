import fs from 'node:fs/promises';import path from 'node:path';import crypto from 'node:crypto';
const root=process.cwd(),pub=path.join(root,'public'),vendor=path.join(pub,'vendor/pyodide');
await fs.mkdir(vendor,{recursive:true});
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const manifest=JSON.parse(await fs.readFile('kernel-manifest.json','utf8')),files={};
for(const [name,expected]of Object.entries(manifest)){
 const bytes=await fs.readFile(path.join('kernel',name));if(sha(bytes)!==expected)throw new Error('Kernel source digest mismatch: '+name);files[name]=bytes.toString('utf8');
}
await fs.writeFile(path.join(pub,'kernel.json'),JSON.stringify({files,manifest}));
for(const name of ['app.js','workspace.js','evolution.js','styles.css'])await fs.copyFile(path.join('kernel/static',name),path.join(pub,name));
for(const name of ['bridge.js','cloud-worker.js','standalone.js'])await fs.copyFile(path.join('client',name),path.join(pub,name));
const publications=JSON.parse(files['knowledge/research-publications.json']);
await fs.mkdir(path.join(pub,'research'),{recursive:true});
for(const report of publications.publications){
 if(!/^\/research\/[a-z0-9-]+\.html$/.test(report.route))throw new Error('Invalid publication route');
 const bytes=await fs.readFile(path.join('kernel',report.path));
 if(sha(bytes)!==report.sha256)throw new Error('Publication digest mismatch');
 await fs.writeFile(path.join(pub,report.route.slice(1)),bytes);
}
let html=files['static/index.html'].replace(/    <script src="\/(workspace|evolution|app)\.js" defer><\/script>\n/g,'');
html=html.replace('</head>','<script src="/bridge.js" defer></script></head>').replace(' 本地',' 云端').replace('仅本机访问','私有云端 · 按需更新').replace('LOCAL EDITION / 0.5','PRIVATE CLOUD / 0.6');
await fs.writeFile('lib/terminal-html.ts','export const terminalHtml = '+JSON.stringify(html)+';\n');
await fs.appendFile(path.join(pub,'styles.css'),'\n.cloud-strip{position:sticky;top:0;z-index:20;background:#edf3eb;border-bottom:1px solid #c8d7c9;padding:9px 16px;font-size:12px;display:flex;flex-wrap:wrap;gap:9px;align-items:center}.cloud-strip span{flex:1;min-width:140px}\n');
const runtime='node_modules/pyodide';
for(const name of ['pyodide.js','pyodide.asm.js','pyodide.asm.wasm','python_stdlib.zip','pyodide-lock.json'])await fs.copyFile(path.join(runtime,name),path.join(vendor,name));
const lock=JSON.parse(await fs.readFile(path.join(runtime,'pyodide-lock.json'),'utf8'));
async function download(url,dest,expected){
 try{const old=await fs.readFile(dest);if(!expected||sha(old)===expected)return old;}catch{}
 const r=await fetch(url);if(!r.ok)throw new Error('Vendor download failed '+r.status+' '+url);const b=Buffer.from(await r.arrayBuffer());if(expected&&sha(b)!==expected)throw new Error('Vendor integrity failed '+url);await fs.writeFile(dest,b);return b;
}
const needed=new Set();function need(name){if(needed.has(name))return;needed.add(name);for(const d of lock.packages[name].depends)need(d);}
for(const name of ['sqlite3','tzdata','ssl'])need(name);
for(const name of needed){const p=lock.packages[name];await download('https://cdn.jsdelivr.net/pyodide/v0.29.3/full/'+p.file_name,path.join(vendor,p.file_name),p.sha256);}
const wheelInfo=await(await fetch('https://pypi.org/pypi/pypdf/6.21.2/json')).json();
const wheel=wheelInfo.urls.find(x=>x.filename.endsWith('py3-none-any.whl'));if(!wheel)throw new Error('Pinned pypdf wheel missing');
await download(wheel.url,path.join(pub,'vendor/pypdf.whl'),wheel.digests.sha256);
console.log(JSON.stringify({kernelFiles:Object.keys(files).length,pyodide:'0.29.3',pypdf:wheelInfo.info.version,vendorPackages:[...needed]}));
