import React, {useState} from 'react';
import {Mountain, Activity, MapPin, Sliders, History, Bell, Settings, ShieldAlert, Volume2, VolumeX, Users, Radio, Menu, X, ChevronLeft, ChevronRight} from 'lucide-react';
interface NavbarProps {
  allowedTabs?: string[]; currentTab: string; onSelectTab: (tab:string)=>void;
  activeAlertCount:number; severeCount:number; soundEnabled:boolean; onToggleSound:()=>void;
}
const items = [
  {id:'dashboard',label:'Dashboard',icon:Activity,group:'Monitor'},
  {id:'map',label:'GIS Explorer',icon:MapPin,group:'Monitor'},
  {id:'predict',label:'Prediction Engine',icon:Sliders,group:'Monitor'},
  {id:'history',label:'Historical Analysis',icon:History,group:'Monitor'},
  {id:'alerts',label:'Early Warnings',icon:Bell,group:'Respond'},
  {id:'operations',label:'Field Operations',icon:MapPin,group:'Respond'},
  {id:'response',label:'Response Coordination',icon:ShieldAlert,group:'Respond'},
  {id:'readiness',label:'Monitoring',icon:Radio,group:'Manage'},
  {id:'accounts',label:'User Accounts',icon:Users,group:'Manage'},
  {id:'admin',label:'Settings',icon:Settings,group:'Manage'},
];
export const Navbar:React.FC<NavbarProps> = ({allowedTabs,currentTab,onSelectTab,activeAlertCount,severeCount,soundEnabled,onToggleSound})=>{
  const [open,setOpen]=useState(false),[compact,setCompact]=useState(false);
  const visible=items.filter(i=>!allowedTabs||allowedTabs.includes(i.id));
  return <>
    <aside className={`command-sidebar ${compact?'is-compact':''}`}>
      <div className="command-brand"><Mountain size={30}/><div className="sidebar-copy"><strong>BHOO-सतर्क</strong><small>Earth-Alert Landslide AI</small></div></div>
      <button className="nav-mobile-toggle" aria-expanded={open} aria-controls="command-links" onClick={()=>setOpen(!open)}>{open?<X size={20}/>:<Menu size={20}/>}<span>{open?'Close navigation':'Explore sections'}</span></button>
      <nav id="command-links" aria-label="Main navigation" className={`command-links ${open?'is-open':''}`}>
        {['Monitor','Respond','Manage'].map(group=><section key={group}>
          {visible.some(i=>i.group===group)&&<h2 className="sidebar-copy">{group}</h2>}
          {visible.filter(i=>i.group===group).map(i=><button key={i.id} title={i.label} aria-label={i.label} aria-current={currentTab===i.id?'page':undefined} onClick={()=>{onSelectTab(i.id);setOpen(false)}}>
            <i.icon size={19}/><span className="sidebar-copy">{i.label}</span>{i.id==='alerts'&&activeAlertCount>0&&<span className={`nav-count ${severeCount?'is-severe':''}`}>{activeAlertCount}</span>}
          </button>)}
        </section>)}
      </nav>
      <div className="sidebar-footer"><span className="sidebar-copy">Preparedness starts here.<small>Monitor · Verify · Coordinate</small></span><button className="nav-collapse" onClick={()=>setCompact(!compact)} aria-label={compact?'Expand navigation':'Collapse navigation'}>{compact?<ChevronRight size={18}/>:<ChevronLeft size={18}/>}</button></div>
    </aside>
    <header className="command-topbar"><div><span className="command-eyebrow">NORTH EASTERN REGION</span><h1>{visible.find(i=>i.id===currentTab)?.label||'Command centre'}</h1></div><button className="sound-control" onClick={onToggleSound} aria-pressed={soundEnabled} title={soundEnabled?'Mute warning siren':'Enable warning siren'}>{soundEnabled?<Volume2 size={18}/>:<VolumeX size={18}/>}<span>Siren {soundEnabled?'on':'off'}</span></button></header>
  </>;
};
