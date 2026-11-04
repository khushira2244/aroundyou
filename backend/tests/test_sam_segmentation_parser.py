"""Offline contract checks only; these are not live detections."""
import base64,io
import pytest
from PIL import Image
from app.execution.media import segment
from app.api.errors import DomainError

def image():
    output=io.BytesIO();Image.new('RGB',(16,16)).save(output,format='PNG');return output.getvalue()

class Response:
    def __init__(self,text):self.text=text;self.calls=0
    def send(self,path,**kwargs):
        self.calls+=1;assert path=='/responses'
        payload=kwargs['json'];assert payload['model']=='sam-3.1'
        assert payload['input'][0]['content'][0]['text']=='garbage bag'
        assert base64.b64decode(payload['input'][0]['content'][1]['image_url'].split(',',1)[1])==image()
        return {'id':'offline-only','model':'sam-3.1','status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':self.text}]}]}

def test_inclusive_boxes_full_frame_and_single_pixel():
    adapter=Response('<0f>0<|box;x1=0;y1=0;x2=15;y2=15;w=16;h=16|><|mask;x=0;y=0;data=16,16,~test|>,2<|box;x1=2;y1=3;x2=2;y2=3;w=16;h=16|><|mask;x=0;y=0;data=1,1,~test|>')
    result,_=segment(adapter,image(),'image/png','garbage bag')
    assert adapter.calls==1 and len(result['boxes'])==2 and result['mask_records']==2
    assert result['boxes'][0]['width']==1 and result['boxes'][0]['height']==1
    assert result['boxes'][1]['width']==1/16 and result['boxes'][1]['height']==1/16
    assert result['wire_output']==adapter.text

def test_empty_lane_is_zero_matches():
    result,_=segment(Response(''),image(),'image/png','garbage bag');assert result['boxes']==[] and result['mask_records']==0

def test_out_of_frame_coordinates_are_rejected():
    with pytest.raises(DomainError):segment(Response('<0f>0<|box;x1=0;y1=0;x2=16;y2=15;w=16;h=16|>'),image(),'image/png','garbage bag')
