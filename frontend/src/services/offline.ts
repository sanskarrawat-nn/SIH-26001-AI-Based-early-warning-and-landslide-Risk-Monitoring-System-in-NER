const base=(import.meta as any).env?.VITE_API_URL || '/api';
export const outbox=()=> (window as any).NEROutbox;
export const endpoint=new URL(`${base}/operations/reports`,window.location.href).href;
export async function registerSync(){
 const registration=await navigator.serviceWorker?.getRegistration();
 if(registration && 'sync' in registration) await (registration as any).sync.register('ner-field-reports');
}
export function changed(){window.dispatchEvent(new Event('ner-outbox-changed'));}
export async function syncReports(manual=true){
 if(!(await outbox().all()).length)return;
 try {await outbox().sync(sessionStorage.getItem('operations-token')||'',true,manual);}
 finally {changed();}
}
export function startOfflineSupport(){
 const start=async(force=false)=>{try{await outbox().migrate(endpoint);if(navigator.onLine)await syncReports(force);}catch{changed();}};
 window.addEventListener('online',()=>start(true));
 window.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')void start();});
 window.setInterval(()=>{if(navigator.onLine)void syncReports(false).catch(()=>{});},30000);
 if('serviceWorker' in navigator && (import.meta as any).env.PROD){
  navigator.serviceWorker.register('/sw.js').then(()=>registerSync()).catch(()=>{});
  navigator.serviceWorker.addEventListener('message',e=>{if(e.data?.type==='ner-outbox-changed')changed();});
 }
 void start();
}
