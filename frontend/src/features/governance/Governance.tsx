import {useEffect,useState,type ChangeEvent} from 'react';

import {Link,useNavigate} from 'react-router-dom';

import {ArrowLeft,ArrowRight,ShieldCheck,FileText,Lightbulb,Upload} from 'lucide-react';

import {Layout} from '../../app/layout';

import {usePlanning} from '../planning/usePlanning';

import {PlanningLoading} from '../planning/PlanningLayout';

import {Guidance} from '../event-creation/Guidance';

import {Field} from '../../shared/ui';

import {Modal} from '../../shared/Modal';

import type {GovernanceState,GovernanceItem} from '../../services/planning-contracts';

export function Governance({ticketView=false}:{ticketView?:boolean}){const {state,problem,act,service,busy}=usePlanning(),navigate=useNavigate(),[governance,setGovernance]=useState<GovernanceState|null>(null),[edits,setEdits]=useState<Record<string,GovernanceItem[]>>({}),[uploading,setUploading]=useState(false),[documentType,setDocumentType]=useState('safety'),[loadError,setLoadError]=useState(''),[notice,setNotice]=useState('');

 const [documents,setDocuments]=useState<{name:string;document_type:string;size:number;mime:string;file:File}[]>([]);
 const [documentError,setDocumentError]=useState('');
 useEffect(()=>{if(!service||!state)return;let alive=true;service.governanceState().then(g=>{if(alive)setGovernance(g)}).catch(e=>{if(alive)setLoadError(String(e))});return()=>{alive=false}},[service,state?.event.id]);

 async function reload(){if(service)setGovernance(await service.governanceState())}

 if(!state)return <PlanningLoading problem={problem}/>;if(!governance)return <PlanningLoading problem={loadError}/>;const e=state.event,ticket=governance.ticket;

 const governancePath='/events/'+e.id+'/governance';
 const requirements=governance.items.filter(item=>item.classification!=='not_applicable');
 const reviewed=service?.mode!=='http'||governance.guidance.status==='human_reviewed_advice';

 const pending=governance.proposals?.find(proposal=>proposal.status==='pending');

 async function nextToDocuments(){
   if(!reviewed){
     if(!pending)return;
     const result=await act('reviewGovernanceAdvisory',{
       proposalId:pending.id,digest:pending.digest,decision:'accept',
       ...(edits[pending.id]?{correctedGovernance:{items:edits[pending.id]}}:{}),
     });
     if(!result)return;
     await reload();
   }
   navigate(governancePath+'/ticket');
 }

 async function startTicket(){
   const files=new FormData();
   for(const document of documents)files.append(document.document_type,document.file);
   const result=await act('startGovernanceTicket',documents.length?{files}:{});
   if(result){await reload();setDocuments([]);}
 }

 function upload(event:ChangeEvent<HTMLInputElement>){
   const file=event.target.files?.[0];
   if(!file)return;
   if(!file.size||file.size>10485760||documents.length>=20||documents.reduce((total,doc)=>total+doc.size,file.size)>52428800||!['application/pdf','image/png','image/jpeg','image/webp'].includes(file.type)){
     setDocumentError('Choose a nonempty PDF, PNG, JPEG or WebP up to 10 MB. The limit is 20 files and 50 MB total.');
     return;
   }
   setDocuments(current=>[...current,{name:file.name,document_type:documentType,size:file.size,mime:file.type,file}]);
   setUploading(false);
 }

 async function download(ticketId:string,documentId:string,name:string){
   const blob=await act<Blob>('downloadGovernanceDocument',{ticketId,documentId});
   if(!blob)return;
   const url=URL.createObjectURL(blob);
   const link=document.createElement('a');
   link.href=url;
   link.download=name;
   link.click();
   setTimeout(()=>URL.revokeObjectURL(url),1000);
 }

 if(ticket)return <Layout><main className="governance-page page">
   <section className="card governance-ticket">
     <h1>Governance Ticket Created</h1>
     <p>Your governance considerations have been recorded for this event.</p>
     <p>Internal record {ticket.id}. Government and platform approval and document verification are separate.</p>
     {!!ticket.documents.length&&<ul>{ticket.documents.map(doc=><li key={doc.id}>
       {doc.name}{doc.storage==='private_backend'?<> · Uploaded <button className="text-link" onClick={()=>void download(ticket.id,doc.id,doc.name)}>Download</button></>:' · Reference only'}
     </li>)}</ul>}
     <div className="button-row">
       <Link className="button primary" to={'/events/'+e.id+'/planning'}>Continue to Stage Planning</Link>
       <Link className="button secondary" to={'/events/'+e.id+'/manage'}>Back to Event Dashboard</Link>
     </div>
   </section>
 </main></Layout>;

 if(ticketView)return <Layout><main className="governance-page page">
   <Link className="back-link" to={governancePath}>Back to Governance Check</Link>
   <section className="card governance-documents">
     <h1>Document Upload</h1>
     <p>Supporting documents are optional. Missing items can remain pending.</p>
     <p className="field-note">Selected files upload privately when you confirm the ticket.</p>
     {requirements.map(item=><div className="outstanding-item" key={item.id}>
       <strong>{item.title}</strong>
       <span>{documents.filter(doc=>doc.document_type===item.id).map(doc=>doc.name).join(', ')||'Pending'}</span>
       <button className="text-link" onClick={()=>{setDocumentType(item.id);setDocumentError('');setUploading(true)}}><Upload size={16}/> Attach document</button>
     </div>)}
     <button className="button primary" disabled={busy||!reviewed} onClick={()=>void startTicket()}>Confirm &amp; Create Governance Ticket</button>
   </section>
   {uploading&&<Modal title="Add governance document" onClose={()=>setUploading(false)}>
     <Field label="Choose PDF, PNG, JPEG or WebP (up to 10 MB)"><input type="file" accept="application/pdf,image/png,image/jpeg,image/webp" onChange={upload}/></Field>
     {documentError&&<p role="alert">{documentError}</p>}
   </Modal>}
 </main></Layout>;
 return <Layout><main className="governance-page page"><button className="back-link" onClick={()=>navigate(`/events/${e.id}/created`)}><ArrowLeft size={16}/>Back to Dashboard</button><h1>{ticketView?'Governance Ticket & Documents':'AI Governance Check'}</h1><p className="governance-subtitle">{ticketView?'Track internal follow-up and submitted information. This is not legal approval and does not confirm authorization.':'Advisory guidance on site access, coordination, safety and handover for your event.'}</p><div className="governance-assessment-layout"><aside><section className="card governance-context"><h2><FileText/>Event Context</h2><dl><dt>Event Name</dt><dd>{e.title}</dd><dt>Category</dt><dd>{e.category}</dd><dt>Event Format</dt><dd>{e.format.replace('_','-')}</dd><dt>Date &amp; Time</dt><dd>{e.creation_details?.startDate??'Unanchored relative schedule'} · {e.creation_details?.startTime??'09:00'}–{e.creation_details?.endTime??'12:00'}<br/>{e.schedule.timezone}</dd><dt>Location</dt><dd>{e.location.label}</dd><dt>Projected Participation</dt><dd>{e.creation_details?.expectedVolunteers||'Unknown'} volunteers (not commitments)</dd><dt>Work Scope</dt><dd>{e.creation_details?.workScope??e.goal}</dd></dl><details><summary>Original execution explanation</summary><blockquote className="source-text">{state.context.execution_intent?.text??state.context.original_text}</blockquote></details></section><Guidance step={3}/></aside><div><div className="tip governance-disclaimer"><Lightbulb/><div><strong>AI guidance only — not legal approval</strong><p>{service?.mode==='http'?'Server-side advisory workflow. No legal determination, official filing or permission is claimed. A configured model is required to generate advice.':'Fixture-backed advisory content. No live AI assessment, legal determination, official filing or permission is claimed. Confirm applicable conditions with the responsible authority.'}</p></div></div><section className="card governance-assessment"><div className="section-heading"><h2><ShieldCheck/>Document Checklist &amp; Safety Measures</h2><span className="demo-pill">{governance.guidance.status.replaceAll('_',' ')}</span></div><p className="muted">Optional considerations; incomplete guidance does not block ordinary planning.</p><button className="button primary compact" disabled={busy} onClick={()=>void act('generateGovernanceAdvisory').then(async r=>{if(r){await reload();setNotice(service?.mode==='http'?'Proposal saved for organizer review. No government permission granted.':'Advisory guidance generated from fixtures. No government permission granted.')}})}>Governance Check</button>{service?.mode==='http'&&governance.proposals?.map(p=><section className="proposal" key={p.id}><h3>Pending governance advice · {p.status}</h3>{(edits[p.id]??p.items).map((item,index)=><div key={item.id}><strong>{item.title}</strong><p>{item.classification?.replaceAll('_',' ')} · {item.detail}</p><p>{item.rationale}</p><p>{item.recommendation_type?.replaceAll('_',' ')} · Responsible: {item.responsible_party||'Organizer to decide'}</p><p>Applies when: {item.applicability_conditions?.join('; ')||'Confirm applicability'}</p><p>Prepare: {item.preparation_information?.join('; ')||'Confirm with responsible party'}</p>{edits[p.id]&&<Field label={'Edit advice: '+item.title}><textarea value={item.detail} onChange={ev=>setEdits({...edits,[p.id]:edits[p.id].map((x,i)=>i===index?{...x,detail:ev.target.value}:x)})}/><button className="text-link" onClick={()=>setEdits({...edits,[p.id]:edits[p.id].filter((_,i)=>i!==index)})}>Dismiss this advice</button></Field>}<p>Supporting event facts: {item.supporting_event_facts?.join('; ')||'Not supplied'}</p><p>Uncertainty: {item.uncertainty?.join('; ')||'Confirm with the responsible authority'}</p><p>Next action: {item.next_action||'Review applicability'}</p><p>Verified rule source: none verified in this integration.</p></div>)}<div className="button-row"><button className="button secondary compact" disabled={busy||p.status!=='pending'} onClick={()=>setEdits({...edits,[p.id]:structuredClone(p.items)})}>Edit advice</button><button className="button primary compact" disabled={busy||p.status!=='pending'} onClick={()=>void act('reviewGovernanceAdvisory',{proposalId:p.id,digest:p.digest,decision:'accept',...(edits[p.id]?{correctedGovernance:{items:edits[p.id]}}:{})}).then(r=>{if(r)void reload()})}>Accept advisory assessment</button><button className="button danger compact" disabled={busy||p.status!=='pending'} onClick={()=>void act('reviewGovernanceAdvisory',{proposalId:p.id,digest:p.digest,decision:'reject'}).then(r=>{if(r)void reload()})}>Reject advisory assessment</button></div></section>)}{governance.items.map(item=><details className="governance-item" key={item.id}><summary><span className="help-icon"><ShieldCheck size={22}/></span><span><strong>{item.title}</strong><small>{item.detail}</small></span><span className="status-pill">{item.status}</span></summary><p>{item.detail}</p><p>{item.rationale}</p><p>Applies when: {item.applicability_conditions?.join('; ')||'Confirm applicability'}</p><p>Responsible: {item.responsible_party||'Organizer to decide'}</p><p>Prepare: {item.preparation_information?.join('; ')}</p><p>Uncertainty: {item.uncertainty?.join('; ')}</p><p className="field-note">Internal follow-up only. Responsible authority, safe access, resource availability and recipient confirmation remain subject to verification.</p></details>)}</section></div></div>{notice&&<p className="notice" role="status">{notice}</p>}</main><footer className="wizard-footer"><button className="button secondary" onClick={()=>navigate(`/events/${e.id}/${ticketView?'governance':'created'}`)}><ArrowLeft size={16}/>{ticketView?'Back to Governance Assessment':'Back to Dashboard'}</button><div><button className="button secondary" onClick={()=>navigate(`/events/${e.id}/created`)}>Save &amp; Exit</button><button className="button secondary" onClick={()=>navigate(`/events/${e.id}/planning`)}>{ticketView?'Upload Documents Later':'Skip for now'}</button> <button className="button primary" disabled={busy||(!reviewed&&!pending)} onClick={()=>void nextToDocuments()}>Next: Document Upload<ArrowRight size={16}/></button></div></footer></Layout>;
}


