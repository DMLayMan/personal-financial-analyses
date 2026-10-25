import { env } from 'cloudflare:workers';
import { allowedUrl, validateManifest, validateMutation, boundedBody, sha256, shaPattern, MAX_BLOB } from './cloud-policy.mjs';
const workspace='owner-private';
const json=(body:any,status=200)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});

export async function cloud(request:Request, path:string[]) {
  const admin=path[0]==='admin';if(admin)path=path.slice(1);
  // /admin is a service-import path behind the owner-private Sites boundary.
  // It requires the consumed Sites bypass credential or owner sign-in upstream.
  // Ordinary research APIs additionally require an authenticated visitor.
  if(!admin&&!request.headers.get('oai-authenticated-user-id'))return json({error:'请登录此私有站点后访问研究空间'},401);
  if(!env.DB||!env.BUCKET)return json({error:'云端持久化绑定尚未就绪'},503);
  const db=env.DB,bucket=env.BUCKET;
  try {
    const write=!['GET','HEAD'].includes(request.method);
    if(write)validateMutation(request);
    if(path[0]==='state'&&request.method==='GET'){
      const head=await db.prepare('SELECT * FROM research_heads WHERE workspace=?').bind(workspace).first();
      return json(head?{...head,files:JSON.parse(String(head.manifest)),mode:'private_cloud',continuous_monitoring:false}:{version:0,files:[],mode:'private_cloud',continuous_monitoring:false});
    }
    if(path[0]==='revisions'&&request.method==='GET'){
      return json((await db.prepare('SELECT id,version,previous_version,sha256,created_at FROM research_revisions WHERE workspace=? ORDER BY version DESC LIMIT 40').bind(workspace).all()).results);
    }
    if(path[0]==='blobs'&&path.length===2&&shaPattern.test(path[1])){
      const key='blobs/'+path[1];
      if(request.method==='GET'){
        const object=await bucket.get(key);if(!object)return json({error:'原件或数据库快照不存在'},404);
        return new Response(object.body,{headers:{'Content-Type':'application/octet-stream','Content-Length':String(object.size),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','X-PFA-SHA256':path[1]}});
      }
      if(request.method==='PUT'){
        const bytes=await boundedBody(request,MAX_BLOB);
        if(await sha256(bytes)!==path[1])return json({error:'上传内容与摘要不一致'},400);
        // Content addressing makes retries idempotent and prevents overwriting
        // an immutable revision's bytes with different bytes.
        if(!await bucket.head(key))await bucket.put(key,bytes,{httpMetadata:{contentType:'application/octet-stream'}});
        return json({sha256:path[1],bytes:bytes.length});
      }
    }
    if(path[0]==='commit'&&request.method==='POST'){
      const bytes=await boundedBody(request,150000);const data=JSON.parse(new TextDecoder().decode(bytes));
      const files=validateManifest(data.files);
      if(!Number.isSafeInteger(data.expectedVersion)||data.expectedVersion<0||!shaPattern.test(data.sha256))throw new Error('保存版本或数据库摘要无效');
      const object=await bucket.get('blobs/'+data.sha256);if(!object||object.size>16*1024*1024)throw new Error('数据库快照缺失或超过16MB');
      const body=new Uint8Array(await object.arrayBuffer());
      if(new TextDecoder().decode(body.slice(0,16))!=='SQLite format 3\u0000'||await sha256(body)!==data.sha256)throw new Error('数据库格式或摘要不匹配');
      for(let i=0;i<files.length;i+=8){
        const valid=await Promise.all(files.slice(i,i+8).map(async(f:any)=>{const h=await bucket.head('blobs/'+f.sha256);return h?.size===f.bytes;}));
        if(valid.some(v=>!v))throw new Error('有原件尚未完整上传；本轮数据库未提交');
      }
      const version=data.expectedVersion+1,stamp=new Date().toISOString(),key=crypto.randomUUID(),manifest=JSON.stringify(files);
      const update=data.expectedVersion===0?
        db.prepare('INSERT INTO research_heads(workspace,version,state_key,sha256,manifest,updated_at) VALUES (?,?,?,?,?,?) ON CONFLICT(workspace) DO NOTHING').bind(workspace,version,key,data.sha256,manifest,stamp):
        db.prepare('UPDATE research_heads SET version=?,state_key=?,sha256=?,manifest=?,updated_at=? WHERE workspace=? AND version=?').bind(version,key,data.sha256,manifest,stamp,workspace,data.expectedVersion);
      const result=await db.batch([update,
        db.prepare('INSERT INTO research_revisions(id,workspace,version,previous_version,state_key,sha256,manifest,created_at) SELECT ?,workspace,version,?,state_key,sha256,manifest,updated_at FROM research_heads WHERE workspace=? AND state_key=?').bind(key,data.expectedVersion,workspace,key)]);
      if(result[0].meta.changes!==1)return json({error:'其他设备已保存新版本。本轮未覆盖；请导出未保存记录后重新载入。',conflict:true},409);
      return json({version,sha256:data.sha256,updated_at:stamp});
    }
    if(path[0]==='retrieve'&&request.method==='POST'&&!admin){
      const data=JSON.parse(new TextDecoder().decode(await boundedBody(request,20000)));
      let url=allowedUrl(data.url);let response:Response|undefined;
      const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),25000);
      try{
        for(let step=0;step<5;step++){
          response=await fetch(url,{redirect:'manual',signal:controller.signal,headers:{'User-Agent':'PersonalFinancialAnalyses/0.6 (personal public-source research)','Accept':'application/pdf,text/html,application/json,text/csv,application/xml'}});
          if(response.status>=300&&response.status<400){const loc=response.headers.get('Location');await response.body?.cancel();if(!loc)throw new Error('来源重定向缺少地址');url=allowedUrl(new URL(loc,url).href);continue;}break;
        }
        if(!response?.ok)throw new Error('公开来源返回 HTTP '+response?.status);
        const body=await boundedBody(response);
        return new Response(body,{headers:{'Content-Type':'application/octet-stream','Cache-Control':'no-store','X-PFA-Content-Type':response.headers.get('Content-Type')||'application/octet-stream','X-PFA-Resolved':encodeURIComponent(url)}});
      }finally{clearTimeout(timeout);}
    }
    return json({error:'云端地址或请求方法不存在'},404);
  } catch(error) {return json({error:error instanceof Error?error.message:'云端操作失败；没有提交新版本'},400);}
}
