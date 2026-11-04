import {useEffect,useRef,useState} from 'react';
import {Mic,X} from 'lucide-react';
import {Field} from '../../shared/ui';
import type {AroundYouService} from '../../services/contracts';
import './voice-input.css';

export function VoiceInput({service,onUse}:{service:AroundYouService;onUse:(text:string)=>void}){
 const [open,setOpen]=useState(false),[status,setStatus]=useState(''),[recording,setRecording]=useState(false),[requesting,setRequesting]=useState(false),[processing,setProcessing]=useState(false),[seconds,setSeconds]=useState(0),[text,setText]=useState(''),[audio,setAudio]=useState<Blob|null>(null);
 const recorder=useRef<MediaRecorder|null>(null),stream=useRef<MediaStream|null>(null),timer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined),clock=useRef<ReturnType<typeof setInterval>|undefined>(undefined),mounted=useRef(true),generation=useRef(0);
 function release(){clearTimeout(timer.current);clearInterval(clock.current);stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;}
 function stop(){if(recorder.current?.state==='recording')recorder.current.stop();release();setRecording(false);}
 useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;generation.current++;if(recorder.current){recorder.current.onstop=null;if(recorder.current.state==='recording')recorder.current.stop()}release()}},[]);
 async function transcribe(blob:Blob,apply=false){
  if(!blob.size){setStatus('No audio was recorded. Please record again and speak into your microphone.');return}
  if(blob.size>10*1024*1024){setStatus('Audio must be at most 10 MB.');return}
  if(!service.transcribeAudio){setStatus('Voice transcription is unavailable. Please enter your explanation manually.');return}
  setProcessing(true);setStatus('Transcribing...');
  try{const result=await service.transcribeAudio(blob);if(!mounted.current)return;if(!result.transcript?.trim())throw new Error('No speech was recognized. Please record again.');setText(result.transcript);if(apply)onUse(result.transcript);setStatus(apply?'Transcript added to Execution explanation. Review and edit it before continuing.':'Transcript ready. Review and edit before using it.');}
  catch(e){if(mounted.current)setStatus(e instanceof Error?e.message:'Transcription failed. Please retry or enter text manually.')}
  finally{if(mounted.current)setProcessing(false)}
 }
 async function capture(){
  const current=++generation.current;setOpen(true);setRequesting(true);setStatus('Allow microphone access in your browser to start recording.');setText('');setAudio(null);setSeconds(0);
  try{
   if(!navigator.mediaDevices?.getUserMedia||typeof MediaRecorder==='undefined')throw new Error('Microphone recording is unavailable. Use localhost or HTTPS, upload audio, or enter text.');
   const acquired=await navigator.mediaDevices.getUserMedia({audio:true});
   if(!mounted.current||current!==generation.current){acquired.getTracks().forEach(t=>t.stop());return}
   stream.current=acquired;const r=new MediaRecorder(acquired);recorder.current=r;const chunks:BlobPart[]=[];
   r.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
   r.onerror=()=>{r.onstop=null;release();setRecording(false);setStatus('Audio capture failed. Please check your microphone and try again.')};
   r.onstop=()=>{release();if(!mounted.current)return;setRecording(false);const blob=new Blob(chunks,{type:r.mimeType});setAudio(blob);void transcribe(blob,true)};
   r.start();setRecording(true);setStatus('Recording. Speak your execution explanation, then select Stop recording.');
   const started=Date.now();clock.current=setInterval(()=>setSeconds(Math.floor((Date.now()-started)/1000)),250);timer.current=setTimeout(stop,55000);
  }catch(e){release();setRecording(false);setStatus(typeof e==='object'&&e!==null&&'name' in e&&e.name==='NotAllowedError'?'Microphone permission denied. Allow microphone access in the browser site settings, then try again.':typeof e==='object'&&e!==null&&'name' in e&&e.name==='NotFoundError'?'No microphone found. Connect a microphone or upload audio.':e instanceof Error?e.message:'Microphone access failed.')}
  finally{if(mounted.current)setRequesting(false)}
 }
 return <>
  {(recording||requesting)&&<dialog className="voice-recording-dialog" aria-labelledby="voice-recording-title" ref={node=>{if(node&&!node.open){if(typeof node.showModal==='function')node.showModal();else node.open=true}}} onCancel={e=>{e.preventDefault();if(recording)stop();else{generation.current++;setRequesting(false);setStatus('Microphone request cancelled.')}}}>
   <div className={recording?'voice-mic voice-mic-active':'voice-mic'}><Mic size={32} aria-hidden="true"/></div>
   <h2 id="voice-recording-title">{recording?'Recording...':'Waiting for microphone access'}</h2>
   {recording?<><p className="voice-timer" role="timer">{String(Math.floor(seconds/60)).padStart(2,'0')}:{String(seconds%60).padStart(2,'0')}</p><button type="button" className="button primary" onClick={stop}>Stop recording</button></>:<p>Allow microphone access in your browser to begin.</p>}
  </dialog>}
  <button type="button" className="button secondary compact" disabled={recording||processing||requesting} onClick={()=>void capture()}><Mic size={17}/>Record voice</button>
  <button type="button" className="button secondary compact" disabled={recording||processing||requesting} onClick={()=>setOpen(true)}>Upload audio</button>
  {open&&!recording&&!requesting&&<div className="voice-panel"><div className="section-heading"><strong><Mic size={17}/>Voice execution intent</strong><button type="button" className="icon-button" disabled={recording||processing||requesting} aria-label="Close voice input" onClick={()=>setOpen(false)}><X size={17}/></button></div>
   <p className="muted">Up to 55 seconds / 10 MB. Stopping sends your recording for transcription. Review the explanation before continuing.</p>
   {status&&<p role="status">{status}</p>}
   {!recording&&!requesting&&<><Field label="Upload audio"><input type="file" accept="audio/*,.webm,.m4a" disabled={processing} onChange={e=>{const f=e.target.files?.[0];if(!f)return;if(!f.size||f.size>10*1024*1024){setAudio(null);setStatus('Audio must be nonempty and at most 10 MB.');return}setAudio(f);setText('');setStatus('Audio ready for transcription.')}}/></Field><button type="button" className="button secondary compact" disabled={!audio||processing} onClick={()=>audio&&void transcribe(audio,true)}>Transcribe / Retry</button></>}
   {text&&<><Field label="Review and edit transcript"><textarea rows={4} value={text} onChange={e=>setText(e.target.value)}/></Field><button type="button" className="button primary compact" disabled={!text.trim()||processing} onClick={()=>{onUse(text);setOpen(false)}}>Use as Event Context</button></>}
  </div>}
 </>;
}



