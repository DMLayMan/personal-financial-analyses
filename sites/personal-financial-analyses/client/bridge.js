'use strict';
(()=>{
 const nativeFetch=window.fetch.bind(window);let serial=0;const waiting=new Map();
 const worker=new Worker('/cloud-worker.js');let ready=false,failed=false;
 const status=document.createElement('section');status.className='cloud-strip';status.setAttribute('role','status');status.innerHTML='<span id="cloud-status-text">正在连接私有云端研究空间…</span><button id="cloud-reload" class="small" hidden>重新载入</button><button id="cloud-verify" class="small" hidden>运行内核控制检查</button><a href="/signin-with-chatgpt?return_to=/" target="_top" id="cloud-signin" hidden>登录私有站点</a><button id="cloud-recovery" class="small" hidden>导出未保存记录</button>';document.querySelector('main').prepend(status);
 const text=status.querySelector('span'),reload=status.querySelector('#cloud-reload'),recovery=status.querySelector('#cloud-recovery'),verify=status.querySelector('#cloud-verify'),signin=status.querySelector('#cloud-signin');
 const call=(message)=>new Promise((resolve,reject)=>{const id=++serial;waiting.set(id,{resolve,reject});worker.postMessage({...message,id});});
 worker.onmessage=({data})=>{
  if(data.type==='progress'){text.textContent=data.message;return;}
  const item=waiting.get(data.id);if(!item)return;waiting.delete(data.id);
  if(data.error){failed=true;reload.hidden=false;recovery.hidden=!ready;item.reject(new Error(data.error));}else item.resolve(data.result);
 };
 worker.onerror=()=>{text.textContent='研究计算线程未能完成。请重新载入；云端旧版本保留。';reload.hidden=false;for(const item of waiting.values())item.reject(new Error(text.textContent));waiting.clear();};
 verify.onclick=async()=>{verify.disabled=true;try{const r=await call({type:'control-tests'});const pre=document.createElement('pre');pre.className='cloud-check-output';pre.textContent=`浏览器运行时控制检查：${r.passed?'通过':'未通过'}；${r.tests} 项。范围：公式、来源/期间、报告门槛与版本；不是投资效果验证。\n`+r.log;status.after(pre);}catch(e){text.textContent=e.message;}finally{verify.disabled=false;}};
 reload.onclick=()=>{if(failed&&ready&&!confirm('当前可能有未保存记录，请先导出。确认重新载入云端版本？'))return;location.reload();};
 recovery.onclick=async()=>{
  try{const r=await call({type:'recovery'});const a=document.createElement('a'),url=URL.createObjectURL(new Blob([r.database],{type:'application/octet-stream'}));a.href=url;a.download='pfa-unsaved-recovery.sqlite3';a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);text.textContent='已导出研究数据库。新取得原件若云端上传失败，仍需从来源重新获取。';}catch(e){text.textContent=e.message;}
 };
 window.fetch=async(input,options={})=>{
  const url=new URL(typeof input==='string'?input:input.url,location.href);
  if(url.origin===location.origin&&url.pathname.startsWith('/api/')){
   const r=await call({path:url.pathname+url.search,method:options.method||'GET',data:options.body?JSON.parse(options.body):null});
   return new Response(JSON.stringify(r.body),{status:r.status,headers:{'Content-Type':'application/json'}});
  }
  return nativeFetch(input,options);
 };
 window.pfaCloud={controlTests:()=>call({type:'control-tests'})};
 async function script(src){return new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=src;s.onload=resolve;s.onerror=()=>reject(new Error('界面脚本加载失败'));document.head.append(s);});}
 call({type:'init'}).then(async()=>{ready=true;verify.hidden=false;for(const src of ['/workspace.js','/evolution.js','/app.js'])await script(src);}).catch(error=>{text.textContent='加载未完成：'+error.message;reload.hidden=false;signin.hidden=!error.message.includes('登录');});
 window.addEventListener('beforeunload',event=>{if(waiting.size&&ready){event.preventDefault();event.returnValue='';}});
})();
