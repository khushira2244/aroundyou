import io,json,wave
from PIL import Image
from tests.test_group4 import run,report,state,review
from tests.test_group3 import scenario
from app.execution.storage import LocalPrivateStorage

class FakeMedia:
    model_profile='test-only'
    def __init__(self):self.calls=[]
    def transcribe(self,raw):self.calls.append('voice');return {'transcript':'Original machine words','model':'test-only'}
    def send(self,path,**kwargs):
        self.calls.append(path)
        if path=='/responses':return {'status':'completed','output':[{'content':[{'type':'output_text','text':'<0f>0<|box;x1=1;y1=1;x2=10;y2=10;w=16;h=16|><|mask;x=0;y=0;data=test|>'}]}]}
        return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'observations':['A region is visible'],'categories':['missing_or_unclear'],'uncertainty':['Does not prove completion'],'follow_up_questions':['What activity occurred?'],'requires_human_review':True})}}]}

def attach(s,r,raw,kind,mime,name):
    data=s.call('/evidence/uploads',{'report_id':r['id'],'report_revision':r['revision'],'kind':kind,'name':name,'mime':mime,'size':len(raw)},s.subject)
    version=s.client.get('/v1/events/'+s.id+'/participation/me',headers=s.headers(s.subject)).json()['meta']['version']
    response=s.client.put('/v1/events/'+s.id+'/evidence/'+data['asset']['id']+'/content',content=raw,headers=s.headers(s.subject,key=name,version=str(version)))
    assert response.status_code==200,response.text
    return response.json()['data']['asset'],data['report_revision']

def test_original_audio_corrected_transcript_and_idempotency(run,app,tmp_path):
    s=run;app.state.evidence_storage=LocalPrivateStorage(tmp_path);adapter=FakeMedia();app.state.planning_adapter=adapter
    raw=io.BytesIO()
    with wave.open(raw,'wb') as wav:wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(b'\0\0'*1600)
    a,rev=attach(s,report(s),raw.getvalue(),'audio','audio/wav','voice.wav');path='/v1/events/'+s.id+'/media/'+a['id']
    for _ in range(2):
        result=s.client.post(path+'/transcription-runs',json={},headers=s.headers(s.subject,key='same-voice'))
        assert result.status_code==200,result.text
        assert result.json()['data']['status']=='succeeded',result.text
    assert adapter.calls==['voice']
    saved=state(s,s.subject)['evidence'][0]
    corrected=s.client.post(path+'/transcript-review',json={'expected_revision':saved['revision'],'text':'Participant corrected words'},headers=s.headers(s.subject,key='review-text'))
    assert corrected.status_code==200,corrected.text
    restored=state(s,s.subject)['evidence'][0]
    assert restored['transcript']=='Participant corrected words' and restored['voice_result']['transcript']=='Original machine words'
    assert s.client.get('/v1/events/'+s.id+'/evidence/'+a['id']+'/content',headers=s.headers(s.subject)).content==raw.getvalue()
    assert state(s)['work'][0]['verified_percent']==0

def test_source_linked_visual_advisory_and_human_review(run,app,tmp_path):
    s=run;app.state.evidence_storage=LocalPrivateStorage(tmp_path);adapter=FakeMedia();app.state.planning_adapter=adapter
    image=io.BytesIO();Image.new('RGB',(16,16),'green').save(image,format='PNG')
    r=report(s);a,rev=attach(s,r,image.getvalue(),'image','image/png','source.png')
    r=s.call('/reports/'+r['id']+'/submit',{'report_revision':rev},s.subject)['report']
    path='/v1/events/'+s.id+'/media/'+a['id']+'/segmentation-runs'
    assert s.client.post(path,json={'concept':'trees'},headers=s.headers(s.subject,key='denied')).status_code==404
    for _ in range(2):
        response=s.client.post(path,json={'concept':'trees'},headers=s.headers(key='same-image'))
        assert response.status_code==200,response.text
        assert response.json()['data']['status']=='succeeded',response.text
    assert adapter.calls==['/responses','/chat/completions']
    saved=state(s)['evidence'][0];assert saved['visual_result']['sha256']==saved['sha256']
    assert state(s)['work'][0]['verified_percent']==0
    a=s.call('/evidence/'+a['id']+'/inspection',{'expected_revision':saved['revision'],'decision':'accept_for_review','note':'Human inspected source'})['asset']
    review(s,r,40,versions={a['id']:a['revision']});assert state(s)['work'][0]['verified_percent']==40

def test_provider_failure_keeps_private_original(run,app,tmp_path):
    s=run;app.state.evidence_storage=LocalPrivateStorage(tmp_path)
    class Failed(FakeMedia):
        def send(self,*args,**kwargs):raise ValueError('test-only invalid response')
    app.state.planning_adapter=Failed();image=io.BytesIO();Image.new('RGB',(16,16)).save(image,format='PNG')
    r=report(s);a,rev=attach(s,r,image.getvalue(),'image','image/png','original.png');s.call('/reports/'+r['id']+'/submit',{'report_revision':rev},s.subject)
    response=s.client.post('/v1/events/'+s.id+'/media/'+a['id']+'/segmentation-runs',json={'concept':'chairs'},headers=s.headers(key='failed-image'))
    assert response.json()['data']['status']=='failed'
    assert s.client.get('/v1/events/'+s.id+'/evidence/'+a['id']+'/content',headers=s.headers(s.subject)).content==image.getvalue()
    assert state(s)['work'][0]['verified_percent']==0
