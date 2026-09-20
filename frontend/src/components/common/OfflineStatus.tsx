import React,{useEffect,useState} from 'react';
import {outbox,syncReports} from '../../services/offline';
export function OfflineStatus(){
 const [online,setOnline]=useState(navigator.onLine),[count,setCount]=useState(0),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{const update=()=>{setOnline(navigator.onLine);outbox().all().then((items:any[])=>setCount(items.length)).catch(()=>setError('Device storage is unavailable.'));};update();window.addEventListener('online',update);window.addEventListener('offline',update);window.addEventListener('ner-outbox-changed',update);return()=>{window.removeEventListener('online',update);window.removeEventListener('offline',update);window.removeEventListener('ner-outbox-changed',update);};},[]);
 if(online&&!count&&!error)return null;
 return <div role="status" className="border-b border-amber-700 bg-amber-950 px-4 py-2 text-sm flex flex-wrap gap-3 items-center"><span>{online?'Online':'Offline — cached information is not live; map tiles require internet.'} · {count} saved reports pending</span>{online&&count>0&&<button disabled={busy} className="underline disabled:opacity-50" onClick={async()=>{setBusy(true);setError('');try{await syncReports();}catch(e:any){setError(e.message);}finally{setBusy(false);}}}>{busy?'Syncing…':'Sync saved reports'}</button>}{error&&<span>{error}</span>}</div>;
}
