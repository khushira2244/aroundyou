import {createContext,useCallback,useContext,useEffect,useState,type ReactNode} from 'react';
import {createMockAdapter} from '../services/mock-adapter';
import {HttpAdapter} from '../services/http-adapter';
const HTTP_MODE=import.meta.env.VITE_AROUNDYOU_MODE==='http';
import type {AroundYouService,CreationForm,CreationState,Identity} from '../services/contracts';
import {DEFAULT_FORM} from '../features/event-creation/model';
interface AppState {service:AroundYouService|null;identity:Identity|null;enterDemo:(i:Identity)=>void;form:CreationForm;setForm:React.Dispatch<React.SetStateAction<CreationForm>>;creation:CreationState|null;setCreation:(s:CreationState)=>void;startDraft:()=>Promise<void>;busy:boolean;error:string;clearError:()=>void;perform:<T>(action:()=>Promise<T>)=>Promise<T|undefined>;saved:boolean;reset:()=>void}
const Context=createContext<AppState|null>(null);
export function AppProvider({children,providedService}:{children:ReactNode;providedService?:AroundYouService}){
  const [service,setService]=useState<AroundYouService|null>(providedService??null),[identity,setIdentity]=useState<Identity|null>(()=>{try{return HTTP_MODE?null:JSON.parse(sessionStorage.getItem('aroundyou.demo.identity')??'null') as Identity|null}catch{return null}}),[form,setForm]=useState<CreationForm>({...DEFAULT_FORM}),[creation,setCreation]=useState<CreationState|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[saved,setSaved]=useState(false);
  useEffect(()=>{if(providedService)return;let cancelled=false;if(HTTP_MODE){const http=new HttpAdapter({baseUrl:import.meta.env.VITE_AROUNDYOU_API_URL??'http://127.0.0.1:8000',token:()=>sessionStorage.getItem('aroundyou.http.token'),storage:sessionStorage});http.initialize().then(i=>{if(!cancelled){setIdentity(i);setService(http)}}).catch(e=>setError(String(e)));}else createMockAdapter().then(s=>{if(!cancelled)setService(s)}).catch(e=>setError(String(e)));return()=>{cancelled=true}},[providedService]);
  useEffect(()=>{if(service&&identity)service.setIdentity(identity)},[service,identity]);
  const enterDemo=(i:Identity)=>{if(HTTP_MODE)return;setIdentity(i);service?.setIdentity(i);sessionStorage.setItem('aroundyou.demo.identity',JSON.stringify(i))};
  const perform=useCallback(async<T,>(action:()=>Promise<T>)=>{setBusy(true);setError('');try{return await action()}catch(e){setError(e instanceof Error?e.message:'Something went wrong. Please retry.');return undefined}finally{setBusy(false)}},[]);
  const startDraft=useCallback(async()=>{if(!service)return;const s=await perform(()=>service.startCreation());if(s){setCreation(s);const stored=s.runtime.draft.creation_details as Partial<CreationForm>|undefined;setForm({...DEFAULT_FORM,...stored});setSaved(!!stored)}},[service,perform]);
  const updateCreation=(s:CreationState)=>{setCreation(s);setSaved(true)};
  const reset=()=>{service?.reset();setCreation(null);setForm({...DEFAULT_FORM});setSaved(false);setError('')};
  return <Context.Provider value={{service,identity,enterDemo,form,setForm,creation,setCreation:updateCreation,startDraft,busy,error,clearError:()=>setError(''),perform,saved,reset}}>{children}</Context.Provider>;
}
export function useApp(){const c=useContext(Context);if(!c)throw new Error('AppProvider missing');return c;}

export function useOptionalApp(){return useContext(Context);}
