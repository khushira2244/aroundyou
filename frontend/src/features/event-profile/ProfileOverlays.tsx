import {useState} from 'react';
import './participant-insights.css';
import {Modal} from '../../shared/Modal';
import type {CanonicalProfile} from '../../services/publication-contracts';
export function InsightsOverlay({profile,onClose}:{profile:CanonicalProfile;onClose:()=>void}){
 const data=profile.insights,[selected,setSelected]=useState(data.counts?'overview':data.breakdowns[0]?.key??'');
 const group=data.breakdowns.find(g=>g.key===selected),overview=selected==='overview';
 const labels:Record<string,string>={age_range:'Age',neighborhood:'Neighborhood',experience_level:'Experience',participation_interest:'Interests',participant_tags:'Tags'};
 const statuses=data.counts?[{label:'Requests submitted',value:data.counts.requested,tone:'requests'},{label:'Human-approved applicants',value:data.counts.approved,tone:'approved'},{label:'Accepted participants',value:data.counts.accepted,tone:'accepted'}]:[];
 const bars=overview?statuses:group?.status==='available'?group.buckets.map((b,i)=>({label:b.label,value:b.count,tone:['requests','approved','accepted'][i%3],percent:b.percent})):[];
 const maximum=Math.max(1,...bars.map(b=>b.value)),title=overview?'Participation overview':group?.label??'Participant breakdown';
 return <div className="participant-insights-overlay"><Modal title="Participant Insights" onClose={onClose}>
  <div className="insights-overlay-heading"><h2>Participant Insights</h2><span className="privacy-badge">Aggregated only · individual responses stay private</span></div>
  <p>Based on actual synthetic demo applications and accepted commitments.</p>{!data.counts&&<p className="notice">{data.total_participants} accepted participants · Public aggregate insights</p>}
  <div className="insights-category-buttons" role="group" aria-label="Participant insight categories">{data.counts&&<button type="button" aria-pressed={overview} aria-controls="selected-participant-insight" onClick={()=>setSelected('overview')}>Overview</button>}{data.breakdowns.map(category=><button type="button" key={category.key} aria-pressed={selected===category.key} aria-controls="selected-participant-insight" onClick={()=>setSelected(category.key)}>{labels[category.key]??category.label}</button>)}</div>
  <section id="selected-participant-insight" aria-label={title} aria-live="polite">
   {bars.length>0?<figure key={selected} className="insights-status-chart" aria-label={overview?'Participant status bar chart':`${title} bar chart`}><figcaption>{title}<span>Number of people</span></figcaption><div className="insights-status-plot" style={{gridTemplateColumns:`repeat(${bars.length},minmax(0,1fr))`}}>{bars.map(bar=><div className={`insights-status-column ${bar.tone}`} key={bar.label} aria-label={`${bar.label}: ${bar.value}`}><div className="insights-status-track"><div className="insights-status-bar" style={{height:`${bar.value/maximum*100}%`}}><strong>{bar.value}</strong></div></div><span className="insights-status-label">{bar.label}</span>{'percent' in bar&&<small className="insights-bucket-percent">{String(bar.percent)}%</small>}</div>)}</div></figure>:<div className="insight-breakdown insights-current-breakdown"><h3>{title}</h3><p className="insight-empty">{group?.status==='disabled'?'Not configured':group?'Insufficient data':'No participant breakdowns available.'}</p><small>{group?.reason}</small></div>}
  </section>
  {overview&&<p className="field-note">Status totals overlap and must not be added together. Approval is not an accepted commitment. A participant account alone is not a registration.</p>}
  <div className="notice">{data.reason}</div>
  <p className="field-note">Privacy threshold: at least {data.minimum_group_size} consented accepted participants in the group and every displayed category. No demographic answer is inferred from an account persona or role.</p>
  <button className="button secondary" onClick={onClose}>Close Insights</button>
 </Modal></div>;
}
export function useShareNotice(){const [notice,setNotice]=useState('');async function share(){try{await navigator.clipboard.writeText(window.location.href);setNotice('Event link copied. This local demo URL is reachable only where the app is running.')}catch{setNotice(`Copy this demo link: ${window.location.href}`)}}return {notice,setNotice,share};}
