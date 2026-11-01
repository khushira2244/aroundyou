import type {CreationForm} from '../../services/contracts';
export const STEPS=['Event Basics','When & Where','Event Context','Review & Create'];
export const CATEGORIES=['Environment','Health','Pets','Education','Community','Support'];
export const DEFAULT_FORM:CreationForm={title:'',category:'Environment',purpose:'',goal:'',format:'in_person',startDate:'',endDate:'',startTime:'09:00',endTime:'12:00',timezone:'Asia/Kolkata',venue:'',area:'',city:'',state:'',country:'India',reach:'Local area',coordinates:null,locationSource:null,workScope:'',executionIntent:'',intentSource:'written',expectedAttendees:'',expectedVolunteers:'',targetGroups:['Local community'],knownResources:'',constraints:'',outcomes:'',theme:'Standard',onlineDetails:'',confirmAccuracy:false,confirmPlanning:false,confirmContinue:false};
export function validateStep(step:number,f:CreationForm):Record<string,string>{
  const e:Record<string,string>={};const need=(k:keyof CreationForm,label:string)=>{if(typeof f[k]==='string'&&!String(f[k]).trim())e[k]=`${label} is required.`;};
  if(step===1){need('title','Event name');need('purpose','Short purpose');need('goal','Detailed goal');if(f.title.length>120)e.title='Use at most 120 characters.';if(f.goal.length>500)e.goal='Use at most 500 characters.';}
  if(step===2){need('startDate','Start date');need('endDate','End date');if(f.startDate&&f.endDate&&f.endDate<f.startDate)e.endDate='End date cannot be before start date.';if(f.startDate===f.endDate&&f.endTime<=f.startTime)e.endTime='End time must be after start time.';if(f.format!=='online'){need('area','Address / area');need('city','City');}if(f.format!=='in_person')need('onlineDetails','Online access details');}
  if(step===3){need('workScope','Work scope');need('executionIntent','Execution explanation');need('outcomes','Desired outcomes');for(const k of ['expectedAttendees','expectedVolunteers'] as const)if(f[k]&&(!/^\d+$/.test(f[k])||Number(f[k])>100000))e[k]='Use a nonnegative whole number or leave unknown.';}
  if(step===4&&!f.confirmAccuracy)e.confirmAccuracy='Confirm the information before creating.';
  if(step===4&&!f.confirmPlanning)e.confirmPlanning='Acknowledge that planning follows creation.';
  if(step===4&&!f.confirmContinue)e.confirmContinue='Acknowledge that details can be added later.';
  return e;
}
