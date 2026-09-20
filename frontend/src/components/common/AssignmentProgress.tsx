import React from 'react';

// Mirrors the existing server transitions. Server validation remains authoritative.
export const nextStatuses:Record<string,string[]>={AWAITING:['ACCEPTED','DECLINED','UNAVAILABLE'],ACCEPTED:['EN_ROUTE','ACCEPTED','UNAVAILABLE'],EN_ROUTE:['ARRIVED','EN_ROUTE','UNAVAILABLE'],ARRIVED:['COMPLETED','ARRIVED','UNAVAILABLE']};
const labels:Record<string,string>={ACCEPTED:'Accept assignment',EN_ROUTE:'On the way',ARRIVED:'Arrived at site',COMPLETED:'Complete assignment',DECLINED:'Decline assignment',UNAVAILABLE:'Report unavailable',CANCELLED:'Cancel assignment'};
export function AssignmentProgress({status,coordinator,inputClass}:{status:string;coordinator:boolean;inputClass:string}){
 const options=[...(nextStatuses[status]||[]),...(coordinator&&!['COMPLETED','CANCELLED'].includes(status)?['CANCELLED']:[])];
 const stages=['AWAITING','ACCEPTED','EN_ROUTE','ARRIVED','COMPLETED'];
 return <>
  <ol className="assignment-steps sm:col-span-2" aria-label="Assignment progress">{stages.map((s,i)=><li key={s} className={i<=stages.indexOf(status)?'step-done':''} aria-current={s===status?'step':undefined}><span>{i+1}</span>{s==='AWAITING'?'Awaiting':s==='EN_ROUTE'?'On the way':s.charAt(0)+s.slice(1).toLowerCase()}</li>)}</ol>
  <label>Next action<select key={status} name="status" className={inputClass} defaultValue={options[0]}>{options.map(s=><option key={s} value={s}>{s===status?'Keep status · update note / ETA':labels[s]||s}</option>)}</select><small className="form-hint">Accept first, then report travel, arrival and completion.</small></label>
 </>;
}
