import {useState} from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {VoiceInput} from '../src/features/event-creation/VoiceInput';
import {HttpAdapter} from '../src/services/http-adapter';
import type {AroundYouService} from '../src/services/contracts';

afterEach(()=>{cleanup();vi.unstubAllGlobals()});
it('captures microphone audio only after a click and stops its tracks',async()=>{
 const stop=vi.fn();const getUserMedia=vi.fn(async()=>({getTracks:()=>[{stop}]}));
 Object.defineProperty(navigator,'mediaDevices',{value:{getUserMedia},configurable:true});
 class Recorder {
  state='inactive';mimeType='audio/webm';ondataavailable:((event:{data:Blob})=>void)|null=null;onstop:(()=>void)|null=null;
  start(){this.state='recording'}
  stop(){this.state='inactive';this.ondataavailable?.({data:new Blob(['captured audio'])});this.onstop?.()}
 }
 vi.stubGlobal('MediaRecorder',Recorder);const transcribeAudio=vi.fn(async()=>({id:'run',transcript:'Spoken intent'}));
 function Form(){const [value,setValue]=useState('');return <><textarea aria-label="Execution explanation" value={value} onChange={e=>setValue(e.target.value)}/><VoiceInput service={{transcribeAudio} as unknown as AroundYouService} onUse={setValue}/></>}
 render(<Form/>);
 expect(getUserMedia).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Record voice'}));
 expect(await screen.findByRole('dialog',{name:'Recording...'})).toBeVisible();expect(screen.getByRole('timer')).toHaveTextContent('00:00');fireEvent.click(screen.getByRole('button',{name:'Stop recording'}));expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(screen.getByText('Transcribing...')).toBeVisible();expect(stop).toHaveBeenCalled();
 await waitFor(()=>expect(screen.getByLabelText('Execution explanation')).toHaveValue('Spoken intent'));expect(transcribeAudio).toHaveBeenCalledOnce();
 fireEvent.change(screen.getByLabelText('Execution explanation'),{target:{value:'Reviewed execution plan'}});expect(screen.getByLabelText('Execution explanation')).toHaveValue('Reviewed execution plan');
});
it('requires explicit transcription and organizer application of corrected words',async()=>{
 const transcribeAudio=vi.fn(async()=>({id:'speech-run',transcript:'Original recognized words'})),onUse=vi.fn();
 render(<VoiceInput service={{transcribeAudio} as unknown as AroundYouService} onUse={onUse}/>);
 fireEvent.click(screen.getByRole('button',{name:'Upload audio'}));
 fireEvent.change(screen.getByLabelText('Upload audio'),{target:{files:[new File(['audio'],'speech.wav',{type:'audio/wav'})]}});
 expect(transcribeAudio).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Transcribe / Retry'}));
 const input=await screen.findByLabelText('Review and edit transcript');expect(input).toHaveValue('Original recognized words');expect(onUse).toHaveBeenCalledWith('Original recognized words');
 fireEvent.change(input,{target:{value:'Organizer corrected words'}});fireEvent.click(screen.getByRole('button',{name:'Use as Event Context'}));expect(onUse).toHaveBeenCalledWith('Organizer corrected words');
});
it('shows a real failure without substituting a sample transcript',async()=>{
 const transcribeAudio=vi.fn(async()=>{throw new Error('Meta unavailable; retry explicitly')});
 render(<VoiceInput service={{transcribeAudio} as unknown as AroundYouService} onUse={()=>{}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Upload audio'}));fireEvent.change(screen.getByLabelText('Upload audio'),{target:{files:[new File(['audio'],'speech.wav')]}});fireEvent.click(screen.getByRole('button',{name:'Transcribe / Retry'}));
 await screen.findByText('Meta unavailable; retry explicitly');expect(screen.queryByLabelText('Review and edit transcript')).not.toBeInTheDocument();expect(transcribeAudio).toHaveBeenCalledOnce();
});
it('sends audio through the authenticated HTTP boundary and links reviewed source',async()=>{
 const requests:{url:string;init:RequestInit}[]=[];
 vi.stubGlobal('fetch',vi.fn(async(url:string,init:RequestInit)=>{requests.push({url,init});return new Response(JSON.stringify({data:url.endsWith('/voice-transcriptions')?{id:'voice-1',transcript:'Actual adapter response'}:init.method==='GET'?{version:1}:{event:{id:'event-1'},runtime:{revision:2}},meta:{version:1}}),{status:200})}));
 const service=new HttpAdapter({baseUrl:'http://localhost:8001',token:()=>null,eventId:()=> 'event-1'});
 await service.transcribeAudio(new Blob(['audio']));expect(requests[0].init.body).toBeInstanceOf(FormData);expect(requests[0].init.credentials).toBe('include');expect(requests[0].init.headers).not.toHaveProperty('Content-Type');
 await service.saveIntent('Corrected words','reviewed_transcript');expect(JSON.parse(String(requests.at(-1)?.init.body))).toMatchObject({transcript_run_id:'voice-1',text:'Corrected words'});
 await waitFor(()=>expect(requests.filter(r=>r.url.endsWith('/voice-transcriptions'))).toHaveLength(1));
});

it('shows permission denial and does not send audio',async()=>{
 Object.defineProperty(navigator,'mediaDevices',{value:{getUserMedia:vi.fn().mockRejectedValue(new DOMException('Denied','NotAllowedError'))},configurable:true});
 vi.stubGlobal('MediaRecorder',class {});const transcribeAudio=vi.fn();
 render(<VoiceInput service={{transcribeAudio} as unknown as AroundYouService} onUse={()=>{}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Record voice'}));await screen.findByText(/Microphone permission denied/);expect(transcribeAudio).not.toHaveBeenCalled();expect(screen.getByRole('button',{name:'Record voice'})).toBeEnabled();
});
it('rejects empty capture without a transcription request',async()=>{
 Object.defineProperty(navigator,'mediaDevices',{value:{getUserMedia:vi.fn(async()=>({getTracks:()=>[{stop:vi.fn()}]}))},configurable:true});
 class EmptyRecorder {state='inactive';mimeType='audio/webm';onstop:(()=>void)|null=null;start(){this.state='recording'}stop(){this.state='inactive';this.onstop?.()}}
 vi.stubGlobal('MediaRecorder',EmptyRecorder);const transcribeAudio=vi.fn();
 render(<VoiceInput service={{transcribeAudio} as unknown as AroundYouService} onUse={()=>{}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Record voice'}));fireEvent.click(await screen.findByRole('button',{name:'Stop recording'}));await screen.findByText(/No audio was recorded/);expect(transcribeAudio).not.toHaveBeenCalled();
});


