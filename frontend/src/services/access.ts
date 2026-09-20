export const roles = {
 admin: {title:'Administrator', description:'Manage accounts, permissions and system settings.'},
 coordinator: {title:'Government / disaster coordinator', description:'Review warnings and field reports, approve dispatch and coordinate resources.'},
 field: {title:'Field officer', description:'Submit observations, photographs and location reports; track review status.'},
 rescue: {title:'Rescue / evacuation team', description:'Accept assignments, update response progress and request resources.'},
 medical: {title:'Hospital / ambulance team', description:'Manage medical response assignments, beds and ambulance availability.'},
 police: {title:'Police', description:'Coordinate assigned incidents and update road access conditions.'},
 public: {title:'Public user', description:'Read area warnings and submit observations to the response coordinator.'},
};
export type Role = keyof typeof roles;
export type Identity = {role:Role|'guest';name?:string;user_id?:string;team_id?:string};
export async function accessApi(path:string,body?:unknown,method?:string):Promise<any>{
 const base=(import.meta as any).env?.VITE_API_URL||'/api';
 const r=await fetch(base+path,{method:method||(body===undefined?'GET':'POST'),credentials:'include',cache:'no-store',headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(25000)});
 const d=await r.json();if(!r.ok)throw new Error(typeof d.detail==='string'?d.detail:Array.isArray(d.detail)?d.detail.map((x:any)=>x.msg).join('; '):'Request failed');return d;
}
