import {Modal} from '../../shared/Modal';
import {useEffect,useState} from 'react';
import {Link,useNavigate} from 'react-router-dom';
import {CalendarDays,MapPin,Trash2} from 'lucide-react';
import {Layout} from '../../app/layout';
import {useApp} from '../../app/provider';
import type {MyEvent} from '../../services/participant-contracts';

export function OrganizerEvents(){
 const {service,identity}=useApp(),navigate=useNavigate();
 const [items,setItems]=useState<MyEvent[]>([]),[problem,setProblem]=useState(''),[loading,setLoading]=useState(true),[deleting,setDeleting]=useState<MyEvent|null>(null),[busyDelete,setBusyDelete]=useState(false);
 // AROUNDYOU EVENT DELETE: explicit confirmation before an owner-only server action.
 async function removeEvent(){if(!deleting||!service?.deleteEvent||busyDelete)return;setBusyDelete(true);setProblem('');try{const result=await service.deleteEvent(deleting.event.id);if(!result.deleted)throw new Error('Event was not deleted. Please reload and try again.');setItems(rows=>rows.filter(r=>r.event.id!==deleting.event.id));setDeleting(null)}catch(e){setProblem(e instanceof Error?e.message:'Unable to delete this event.')}finally{setBusyDelete(false)}}
 useEffect(()=>{let active=true;setLoading(true);setItems([]);setProblem('');setDeleting(null);service?.myEvents().then(rows=>{if(active)setItems(rows.filter(r=>r.organizer))}).catch(e=>{if(active)setProblem(e.message)}).finally(()=>{if(active)setLoading(false)});return()=>{active=false}},[service,identity?.accountId]);
 return <Layout><main className="page"><header className="section-heading"><div><h1>My Events</h1><p>Your organized events and saved drafts.</p></div><Link className="button secondary" to="/my-participation">My Participation</Link></header>{problem&&!deleting&&<p role="alert">{problem}</p>}{loading?<p role="status">Loading your events…</p>:<div className="my-events-grid">{items.map(item=>{const {event:e,resume_path}=item;return <article key={e.id} className="card my-event-card"><h2><Link to={resume_path??`/events/${e.id}/${e.lifecycle==='published'?'manage/overview':'planning'}`} onClick={()=>service?.selectEvent?.(e.id)}>{e.title||'Untitled event'}</Link></h2><span className="demo-pill">{(e.lifecycle??'draft').replaceAll('_',' ')}</span><p><MapPin size={16}/> {e.location.label||'Location not set'}</p><p><CalendarDays size={16}/> {e.schedule.anchor_date||'Date not set'} · {e.schedule.timezone}</p><div className="button-row"><button className="button primary compact" onClick={()=>{service?.selectEvent?.(e.id);navigate(resume_path??`/events/${e.id}/${e.lifecycle==='published'?'manage/overview':'planning'}`)}}>{e.lifecycle==='draft'?'Resume Draft':e.lifecycle==='published'?'Manage Event':'Continue Planning'}</button>{service?.deleteEvent&&item.can_delete!==false&&<button className="button secondary compact" aria-label={`Delete ${e.title||'Untitled event'}`} onClick={()=>{setProblem('');setDeleting(item)}}><Trash2 size={15}/>Delete</button>}</div></article>})}</div>}{!loading&&!items.length&&<p className="notice">You have no organized events yet.</p>}{deleting&&<Modal title="Delete event" onClose={()=>{if(!busyDelete)setDeleting(null)}}><h2>Delete {deleting.event.title||'Untitled event'}?</h2><p>This removes the event from My Events and public listings. Linked plans, evidence and history are retained for audit. Participant access to this event will stop.</p>{problem&&<p role="alert">{problem}</p>}<div className="button-row"><button className="button secondary" disabled={busyDelete} onClick={()=>setDeleting(null)}>Cancel</button><button className="button primary" disabled={busyDelete} onClick={()=>void removeEvent()}>{busyDelete?'Deleting…':'Delete Event'}</button></div></Modal>}</main></Layout>
}



