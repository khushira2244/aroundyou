import {useCallback,useEffect,useState} from 'react';
import {useParams} from 'react-router-dom';
import {useApp} from '../../app/provider';
import type {PlanningOperation,PlanningState} from '../../services/planning-contracts';
export function usePlanning(){const {service,perform,busy}=useApp(),{eventId}=useParams();const [state,setState]=useState<PlanningState|null>(null),[problem,setProblem]=useState('');
 useEffect(()=>{if(!service)return;let alive=true;service.openPlanning().then(s=>{if(alive){if(s.event.id!==eventId)setProblem('This route does not match the created event.');else setState(s)}}).catch(e=>{if(alive)setProblem(e instanceof Error?e.message:String(e))});return()=>{alive=false}},[service,eventId]);
 const refresh=useCallback(async()=>{if(service){const s=await service.readPlanning();setState(s);return s}},[service]);
 async function act<T=unknown>(operation:PlanningOperation,input:Record<string,unknown>={}):Promise<T|undefined>{if(!service)return;const result=await perform(()=>service.planningCommand<T>(operation,input));if(result!==undefined)await refresh();return result}
 return {state,setState,problem,act,refresh,busy,service};
}
