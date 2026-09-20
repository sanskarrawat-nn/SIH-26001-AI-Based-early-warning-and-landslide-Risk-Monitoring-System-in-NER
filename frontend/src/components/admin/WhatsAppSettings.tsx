import React,{useEffect,useState} from 'react';
import languages from '../../data/alert-languages.json';
import {LocationItem} from '../../types';
const BASE=(import.meta as any).env?.VITE_API_URL||'/api';
const input='w-full rounded-lg border border-slate-600 bg-slate-900 p-3 text-white';
export function WhatsAppSettings({locations}:{locations:LocationItem[]}){
 const [status,setStatus]=useState<any>(null),[recipients,setRecipients]=useState<any[]>([]),[deliveries,setDeliveries]=useState<any[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false),[signedIn,setSignedIn]=useState(false),[ready,setReady]=useState(false);
  async function request(path:string,options:RequestInit={}){
    const r=await fetch(`${BASE}/whatsapp${path}`,{...options,credentials:'include',headers:{'Content-Type':'application/json','X-Operations-Key':sessionStorage.getItem('operations-token')||'',...options.headers},signal:AbortSignal.timeout(15000)});
    let data: any = null;
    try { data = await r.json(); } catch { /* non-JSON response */ }
    if(!r.ok) throw new Error((data && (typeof data.detail==='string'?data.detail:Array.isArray(data.detail)?data.detail.map((e:any)=>e.msg).join('; '):data.message)) || `Request failed (${r.status})`);
    return data;
  }
  async function refresh(){
    setError('');
    try {
      try {
        const s = await request('/status');
        setStatus(s);
      } catch {
        // WhatsApp status optional on fresh boot
      }
      const authRes = await fetch(`${BASE}/auth/session`,{credentials:'include',cache:'no-store',signal:AbortSignal.timeout(8000)});
      if (authRes.ok) {
        let auth: any = null;
        try { auth = await authRes.json(); } catch {}
        if (auth) {
          setSignedIn(Boolean(auth.authenticated));
          setReady(Boolean(auth.configured));
          if(auth.authenticated){
            const [r,d]=await Promise.allSettled([request('/recipients'),request('/deliveries')]);
            if (r.status==='fulfilled') setRecipients(r.value || []);
            if (d.status==='fulfilled') setDeliveries(d.value || []);
          }
        }
      } else {
        setReady(true);
      }
    } catch(e:any){
      setError(e.message || 'Unable to connect to backend.');
    }
  }
  useEffect(()=>{refresh()},[]);
  async function add(e:React.FormEvent<HTMLFormElement>){e.preventDefault();const form=e.currentTarget;const data=Object.fromEntries(new FormData(form));setBusy(true);setError('');try{await request('/recipients',{method:'POST',body:JSON.stringify({...data,location_id:data.location_id||null,opted_in:data.opted_in==='on'})});form.reset();await refresh();}catch(e:any){setError(e.message)}finally{setBusy(false)}}
  return <section className="rounded-xl border border-slate-700 bg-[#0c1527] p-4 sm:p-6 space-y-4 text-base"><h2 className="text-xl font-semibold">WhatsApp crisis alerts</h2><p>Send approved Twilio WhatsApp notifications to registered, opted-in recipients when an operational alert becomes HIGH or SEVERE. Demo and simulator alerts are excluded.</p>

  {signedIn?<div className="flex gap-3 items-center"><span>Administrator signed in</span><button className="rounded bg-slate-700 px-4 py-2" onClick={async()=>{try{const r=await fetch(`${BASE}/access/logout`,{method:'POST',credentials:'include'});if(!r.ok)throw new Error('Sign out failed');sessionStorage.removeItem('operations-token');setSignedIn(false);setRecipients([]);setDeliveries([]);window.location.assign('/login')}catch(e:any){setError(e.message)}}}>Sign out</button><button onClick={refresh}>Refresh</button></div>:<form className="space-y-3" onSubmit={async(e)=>{e.preventDefault();const values=Object.fromEntries(new FormData(e.currentTarget));setBusy(true);setError('');try{const r=await fetch(`${BASE}/auth/login`,{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify(values)});let data: any = null; try { data = await r.json(); } catch {} if(!r.ok)throw new Error((data && (typeof data.detail==='string'?data.detail:Array.isArray(data.detail)?data.detail.map((e:any)=>e.msg).join('; '):data.message)) || `Sign in failed (${r.status})`);sessionStorage.removeItem('operations-token');await refresh()}catch(e:any){setError(e.message)}finally{setBusy(false)}}}><h3 className="font-semibold">Administrator login</h3>{!ready&&<p className="text-amber-400 text-sm">Administrator login needs backend setup: ADMIN_USERNAME and ADMIN_PASSWORD.</p>}<label className="block">Username<input className={input} name="username" autoComplete="username" required maxLength={120}/></label><label className="block">Password<input className={input} name="password" type="password" autoComplete="current-password" required maxLength={512}/></label><p className="text-sm text-slate-400">Stay signed in for up to 30 days on this browser. Sign out on shared devices.</p><button disabled={busy||!ready} className="rounded bg-blue-600 px-4 py-3 disabled:opacity-50">{busy?'Signing in…':'Sign in'}</button></form>}

  {error&&<p role="alert" className="rounded border border-rose-700 p-3 text-rose-200">{error}</p>}
 {signedIn&&<><form onSubmit={add} className="space-y-3"><h3 className="font-semibold">Register recipient</h3><div className="grid sm:grid-cols-2 gap-3"><label>Name<input className={input} name="name" required minLength={2} maxLength={120}/></label><label>WhatsApp phone number<input className={input} name="phone" type="tel" placeholder="+919876543210" pattern="\+[1-9][0-9]{7,14}" required/></label></div><label className="block">Alert coverage<select className={input} name="location_id" aria-label="Alert coverage"><option value="">All monitored locations</option>{locations.map(l=><option key={l.location_id} value={l.location_id}>{l.name}</option>)}</select></label><label className="block">Alert language<select className={input} name="language">{Object.entries(languages).map(([code,item])=><option key={code} value={code}>{item.name}{status?.languages?.[code]?.configured?'':' — template setup required'}</option>)}</select></label><label className="block">Consent record/reference<input className={input} name="consent_reference" placeholder="Signed registration form or WhatsApp opt-in reference" required minLength={5} maxLength={300}/></label><label className="flex gap-2"><input type="checkbox" name="opted_in" required/>This person explicitly agreed to receive WhatsApp crisis alerts.</label><button disabled={busy} className="rounded bg-blue-600 px-4 py-3 disabled:opacity-50">{busy?'Saving…':'Add recipient'}</button></form>
 <div className="space-y-2"><h3 className="font-semibold">Registered recipients ({recipients.length})</h3>{recipients.map(r=><div key={r.id} className="flex flex-wrap justify-between gap-2 border-b border-slate-700 py-2"><span>{r.name} · {r.phone} · {r.location_id||'All locations'} · {(languages as any)[r.language||'en']?.name}</span><button className="text-rose-300" onClick={async()=>{if(!confirm(`Remove ${r.name} and cancel pending alerts?`))return;try{await request(`/recipients/${r.id}`,{method:'DELETE'});await refresh()}catch(e:any){setError(e.message)}}}>Remove / opt out</button></div>)}</div>
 <div className="space-y-2"><h3 className="font-semibold">Recent deliveries</h3><p className="text-sm text-slate-400">Queued or sent does not mean delivered. UNKNOWN means the outcome needs checking in Twilio; automatic resend is stopped to avoid duplicates.</p>{!deliveries.length&&<p>No deliveries recorded.</p>}{deliveries.map(d=><div key={d.id} className="border-b border-slate-700 py-2 break-words"><strong>{d.recipient_name} · {d.alert_id} · {d.severity} · {d.language||'en'} · {d.status}</strong><p className="text-sm">Attempts: {d.attempts} {d.twilio_sid&&`· ${d.twilio_sid}`}</p>{d.error&&<p className="text-amber-300 text-sm">{d.error}</p>}</div>)}</div></>}</section>
}
