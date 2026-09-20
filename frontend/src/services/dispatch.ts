const BASE=(import.meta as any).env?.VITE_API_URL||'/api';
export async function responseApi(path:string,body?:any,method?:string){
 const key=sessionStorage.getItem('operations-token');
 const r=await fetch(BASE+'/dispatch'+path,{method:method||(body?'POST':'GET'),credentials:'include',cache:'no-store',headers:{'Content-Type':'application/json',...(key?{'X-Operations-Key':key}:{})},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(25000)});
 const d=await r.json();if(!r.ok)throw new Error(typeof d.detail==='string'?d.detail:Array.isArray(d.detail)?d.detail.map((x:any)=>x.msg).join('; '):'Request failed');return d;
}
export function openResponseDraft(data:any){sessionStorage.setItem('response-draft',JSON.stringify(data));window.dispatchEvent(new Event('open-response'));}
export function exportResponse(name:string,data:any){const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
