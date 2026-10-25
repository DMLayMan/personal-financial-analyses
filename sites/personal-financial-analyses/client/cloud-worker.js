/* Research computation runs off the UI thread using the same Python sources. */
importScripts('/vendor/pyodide/pyodide.js');
let py,version=0,known=new Set(),blocked=false;
const root='/app';
const notify=(message)=>self.postMessage({type:'progress',message});
const hex=async bytes=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
async function checked(url,options){const r=await fetch(url,{cache:'no-store',...options});if(!r.ok){let error;try{error=(await r.json()).error;}catch{}if(r.status===409)blocked=true;throw new Error(error||`请求失败 HTTP ${r.status}`);}return r;}
function write(path,bytes){const at=root+'/'+path;py.FS.mkdirTree(at.slice(0,at.lastIndexOf('/')));py.FS.writeFile(at,bytes);}
function b64(bytes){let out='';for(let i=0;i<bytes.length;i+=16384)out+=String.fromCharCode(...bytes.subarray(i,i+16384));return btoa(out);}
function run(expression,variables={}){for(const[k,v]of Object.entries(variables))py.globals.set(k,v);try{return py.runPython(expression);}finally{for(const k of Object.keys(variables))py.globals.delete(k);}}
async function batches(items,callback,n=3){let next=0;await Promise.all(Array.from({length:Math.min(n,items.length)},async()=>{while(next<items.length){let i=next++;await callback(items[i],i);}}));}
async function initialise(){
 notify('正在加载研究计算环境（首次访问需要下载运行时）…');
 py=await loadPyodide({indexURL:'/vendor/pyodide/'});
 await py.loadPackage(['sqlite3','tzdata','ssl']);
 const bundle=await (await checked('/kernel.json')).json();
 for(const[path,source]of Object.entries(bundle.files))write(path,new TextEncoder().encode(source));
 const wheel=new Uint8Array(await (await checked('/vendor/pypdf.whl')).arrayBuffer());
 py.unpackArchive(wheel,'zip',{extractDir:'/vendor-python'});
 py.runPython("import sys\nsys.path[:0]=['/app','/vendor-python']\n");
 const state=await (await checked('/cloud/state')).json();version=state.version;
 if(!version)throw new Error('云端资料尚未导入。请完成资料迁移后重新载入。');
 const db=new Uint8Array(await (await checked('/cloud/blobs/'+state.sha256)).arrayBuffer());
 if(await hex(db)!==state.sha256)throw new Error('云端数据库摘要不匹配，停止加载');
 write('data/pfa.sqlite3',db);
 let count=0;
 await batches(state.files,async file=>{
   const bytes=new Uint8Array(await (await checked('/cloud/blobs/'+file.sha256)).arrayBuffer());
   if(bytes.length!==file.bytes||await hex(bytes)!==file.sha256)throw new Error('原件摘要不匹配：'+file.path);
   write(file.path,bytes);known.add(file.sha256);count++;
   notify(`正在核验云端证据 ${count}/${state.files.length}（仅证明文件一致）…`);
 });
 run("from pfa.cloud_bridge import BrowserBridge\nimport json\nbridge=BrowserBridge('/app/data/pfa.sqlite3')\n");
 // Run the exact CPython control suite in the browser runtime too. Fixtures in
 // this bundle are source-only and contain no account credentials or holdings.
 notify('正在复核研究内核与云端保存状态…');
 const urls=JSON.parse(run('json.dumps(bridge.pending_urls())'));
 if(urls.length)await drain();
 notify(`云端 v${version} 已载入 · 按需更新`);
 return JSON.parse(run("json.dumps({'kernel_digest':__import__('pfa.assurance',fromlist=['RUNNING_KERNEL']).RUNNING_KERNEL,'version':__import__('pfa').__version__})"));
}
async function persist(){
 try{
 if(blocked)throw new Error('保存发生冲突。请先导出未保存记录，再重新载入云端版本。');
 const files=JSON.parse(run("json.dumps(bridge.snapshot('/app/data/cloud-snapshot.sqlite3'))"));
 await batches(files.filter(f=>!known.has(f.sha256)),async f=>{
  const bytes=py.FS.readFile(root+'/'+f.path);if(await hex(bytes)!==f.sha256)throw new Error('上传前原件发生变化');
  await checked('/cloud/blobs/'+f.sha256,{method:'PUT',headers:{'X-PFA-Request':'1'},body:bytes});known.add(f.sha256);
 });
 const bytes=py.FS.readFile('/app/data/cloud-snapshot.sqlite3'),sha=await hex(bytes);
 await checked('/cloud/blobs/'+sha,{method:'PUT',headers:{'X-PFA-Request':'1'},body:bytes});
 const saved=await (await checked('/cloud/commit',{method:'POST',headers:{'Content-Type':'application/json','X-PFA-Request':'1'},body:JSON.stringify({expectedVersion:version,sha256:sha,files})})).json();
 version=saved.version;notify(`已保存到云端 v${version} · ${new Date(saved.updated_at).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false})}`);
 }catch(error){blocked=true;throw new Error('本轮云端保存未确认，已暂停修改。请导出记录后重新载入。'+error.message);}
}
async function drain(){
 const urls=JSON.parse(run('json.dumps(bridge.pending_urls())'));
 if(!urls.length)return;
 notify(`正在按需获取 ${urls.length} 个公开来源；失败会保留旧日期…`);
 const cache={};await batches(urls,async url=>{
   try{const r=await checked('/cloud/retrieve',{method:'POST',headers:{'Content-Type':'application/json','X-PFA-Request':'1'},body:JSON.stringify({url})});
    cache[url]={body:b64(new Uint8Array(await r.arrayBuffer())),content_type:r.headers.get('X-PFA-Content-Type'),url:decodeURIComponent(r.headers.get('X-PFA-Resolved')||encodeURIComponent(url))};
   }catch(e){cache[url]={error:String(e.message)};}
 });
 run('bridge.cache=json.loads(_cache)\nbridge.run_jobs()',{_cache:JSON.stringify(cache)});await persist();
}
async function request(message){
 if(message.type==='init')return initialise();
 if(!py)throw new Error('研究内核尚未就绪');
 if(message.type==='recovery'){
   const files=JSON.parse(run("json.dumps(bridge.snapshot('/app/data/recovery.sqlite3'))"));
   return {database:py.FS.readFile('/app/data/recovery.sqlite3'),files,cloudVersion:version};
 }
 if(message.type==='control-tests'){
   return JSON.parse(run("import unittest,io\n_suite=unittest.TestSuite(unittest.defaultTestLoader.discover('/app/tests',pattern=name) for name in ['test_cloud_bridge.py','test_evolution.py','test_markets.py'])\n_suite.addTests(unittest.defaultTestLoader.loadTestsFromName('test_research.FinancialLogic'))\n_stream=io.StringIO()\n_result=unittest.TextTestRunner(stream=_stream,verbosity=1).run(_suite)\njson.dumps({'passed':_result.wasSuccessful(),'tests':_result.testsRun,'log':_stream.getvalue()})"));
 }
 if(message.method==='POST'&&blocked)throw new Error('当前页面有未保存冲突，请先导出记录再重新载入');
 // Check before mutation; the server's compare-and-swap is still authoritative.
 if(message.method==='POST'){
   const head=await(await checked('/cloud/state')).json();
   if(head.version!==version){blocked=true;throw new Error('其他设备已更新研究记录。本轮没有修改；请重新载入。');}
 }
 const result=JSON.parse(run('json.dumps(bridge.request(_path,_method,json.loads(_data)))',{_path:message.path,_method:message.method||'GET',_data:JSON.stringify(message.data??null)}));
 if(message.method==='POST'&&result.status<300){
   notify('研究操作完成，正在保存云端版本…');
   await persist();await drain();
 }
 return result;
}
let queue=Promise.resolve();
self.onmessage=event=>{const message=event.data;queue=queue.then(async()=>{
 try{const result=await request(message);self.postMessage({id:message.id,result});}
 catch(error){notify('操作未完成：'+(error.message||String(error)));self.postMessage({id:message.id,error:error.message||String(error)});}
});};
