import {Leaf,PawPrint,HeartPulse,BookOpen,Users,Handshake} from 'lucide-react';
import type {DiscoveryEvent} from '../../services/contracts';
export function categoryIcon(group:string){return ({Pets:PawPrint,Environment:Leaf,Health:HeartPulse,Education:BookOpen,Community:Users,Support:Handshake})[group]??Users;}
// Screen percentages only, not geographic coordinates. Unknown fixture venues remain null.
const LAYOUT:Record<string,[number,number]>={
  'event-canary-hill-001':[44,45],
  'event-discovery-002':[14,28],
  'event-discovery-003':[69,68],
  'event-discovery-004':[53,23],
  'event-discovery-005':[32,68],
  'event-discovery-006':[84,27],
  'event-discovery-007':[15,72],
  'event-discovery-008':[76,46],
  'event-discovery-009':[34,26],
  'event-discovery-010':[53,76],
  'event-discovery-011':[88,72],
};
export function MapMarkers({events,onSelect,selectedId}:{events:DiscoveryEvent[];onSelect:(id:string)=>void;selectedId?:string}){
  return <div className="map-marker-layer" aria-label="Hazaribagh initiative markers">{events.map(event=>{const [x,y]=LAYOUT[event.id]??[50,50];const Icon=categoryIcon(event.filter_group);return <button key={event.id} className={`map-marker category-marker ${selectedId===event.id||(!selectedId&&event.id==='event-canary-hill-001')?'selected':''}`} style={{left:`${x}%`,top:`${y}%`}} aria-label={`Preview ${event.title}`} title={`${event.title} — ${event.category}${event.location.coordinates?'':' · illustrative position; exact venue pending'}`} onClick={()=>onSelect(event.id)}><i className="marker-drop"><Icon size={25} role="img" aria-label={`${event.filter_group} icon`}/></i><span>{event.title}</span></button>})}</div>;
}
