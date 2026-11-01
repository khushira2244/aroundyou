import {eventImages} from '../../shared/eventImages';
import {Link} from 'react-router-dom';
import {Layout} from '../../app/layout';
import type {DemoEvent} from '../../services/contracts';
import type {RelativeSchedule} from '../../services/planning-contracts';
import {CalendarDays,MapPin,Leaf} from 'lucide-react';
export const clock=(n:number)=>`${String(Math.floor(n/60)).padStart(2,'0')}:${String(n%60).padStart(2,'0')}`;
export function dayLabel(e:DemoEvent,day:number){if(!e.schedule.anchor_date)return `Day ${day}`;const date=new Date(`${e.schedule.anchor_date}T00:00:00Z`);date.setUTCDate(date.getUTCDate()+day-1);return date.toLocaleDateString('en-IN',{month:'short',day:'numeric',timeZone:'UTC'});}
export const scheduleLabel=(e:DemoEvent,s:RelativeSchedule)=>`${dayLabel(e,s.start_day)} ${clock(s.start_minute)}–${clock(s.end_minute)} · ${s.timezone}`;
export function ParticipationLoading({problem}:{problem:string}){return <Layout><main className="page card"><h1>{problem?'Participation unavailable':'Loading participation…'}</h1><p role={problem?'alert':'status'}>{problem||'Checking the selected event and your private participation records.'}</p><Link to="/join-events">Return to Join Events</Link></main></Layout>}
export function ParticipationEventSummary({event:e}:{event:DemoEvent}){return <div className="participation-event-summary"><div className="participation-event-art">{eventImages(e)?<img className="event-thumbnail-image" src={eventImages(e)!.thumbnail} alt="Canary Hill destination"/>:<><Leaf size={40}/><small>No event photo supplied</small></>}</div><div><h2>{e.title}</h2><p><CalendarDays size={19}/>{e.schedule.anchor_date??'Relative days · calendar dates unconfirmed'}{e.schedule.end_date?` – ${e.schedule.end_date}`:''}</p><p><MapPin size={19}/>{e.location.label}</p></div></div>}
