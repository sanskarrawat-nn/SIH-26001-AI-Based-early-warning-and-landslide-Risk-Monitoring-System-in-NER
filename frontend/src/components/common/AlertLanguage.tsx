import React,{useEffect,useState} from 'react';
import languages from '../../data/alert-languages.json';
import {AlertItem} from '../../types';
export function useAlertLanguage(){
 const read=()=>{try{const code=localStorage.getItem('ner-alert-language')||'en';return code in languages?code:'en';}catch{return 'en';}};
 const [language,setLanguage]=useState(read);
 useEffect(()=>{const change=()=>setLanguage(read());window.addEventListener('ner-language',change);return()=>window.removeEventListener('ner-language',change)},[]);
 return language;
}
export function AlertLanguageSelect(){
 const language=useAlertLanguage();
 return <label className="text-sm flex flex-wrap items-center gap-2">Alert language<select aria-label="Alert language" className="bg-slate-900 border border-slate-600 rounded p-2" value={language} onChange={e=>{try{localStorage.setItem('ner-alert-language',e.target.value);window.dispatchEvent(new Event('ner-language'));}catch{}}}>{Object.entries(languages).map(([code,item])=><option value={code} key={code}>{item.name}</option>)}</select></label>;
}
export function LocalizedAlert({alert}:{alert:AlertItem}){
 const language=useAlertLanguage();if(language==='en')return null;
 const text=(languages as any)[language];
 return <div lang={language} className="border border-blue-800 rounded p-3 my-2 text-sm space-y-1"><strong>{text.title} · {text.levels[alert.severity]}</strong><p>{alert.location_name||alert.location_id} · {text.score}: {alert.risk_score.toFixed(1)}/100 · {text.statuses[alert.status]}</p>{alert.status!=='RESOLVED'&&<p>{text.action}</p>}<p className="text-xs text-slate-400">{text.original} ↓</p></div>;
}
