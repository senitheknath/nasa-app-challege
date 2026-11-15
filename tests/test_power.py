from copy import deepcopy
from datetime import date
import json
import pytest
import requests
from agroshift.power import DataError,PowerClient,parse_payload,request_parameters,unpack

@pytest.fixture
def response_data():
    p=json.load(open("preparation/evidence/anuradhapura_20250101_20250107.json"))
    q=request_parameters(8.3114,80.4037,date(2025,1,1),date(2025,1,7))
    return p,q

class Response:
    status_code=200
    headers={}
    url="https://power.larc.nasa.gov/api/temporal/daily/point"
    def __init__(self,payload,status=200):self.payload,self.status_code=payload,status
    def json(self):return self.payload

class Session:
    def __init__(self,responses):self.responses=iter(responses);self.calls=0
    def get(self,*args,**kwargs):
        self.calls+=1
        value=next(self.responses)
        if isinstance(value,Exception):raise value
        return value

@pytest.mark.parametrize("lat,lon",[(91,0),(0,181),(float('nan'),0),(0,float('inf')),(True,1)])
def test_bad_coordinates(lat,lon):
    with pytest.raises(DataError):request_parameters(lat,lon,date(2020,1,1),date(2020,1,2))

def test_unknown_parameter():
    with pytest.raises(DataError):request_parameters(0,0,date(2020,1,1),date(2020,1,2),("fake",))

def test_sentinel_and_missing_date(response_data):
    p,q=response_data
    p['properties']['parameter']['PRECTOTCORR']['20250101']=-999
    del p['properties']['parameter']['T2M']['20250102']
    frame,issues=parse_payload(p,q)
    assert frame.PRECTOTCORR.isna().sum()==1
    assert frame.T2M.isna().sum()==1
    assert len(frame)==7

def test_solar_conversion(response_data):
    p,q=response_data
    original=p['properties']['parameter']['ALLSKY_SFC_SW_DWN']['20250101']
    p['parameters']['ALLSKY_SFC_SW_DWN']['units']='kWh/m^2/day'
    frame,issues=parse_payload(p,q)
    assert frame.ALLSKY_SFC_SW_DWN.iloc[0]==pytest.approx(original*3.6)
    assert issues

def test_bad_units(response_data):
    p,q=response_data;p['parameters']['PRECTOTCORR']['units']='mm/hour'
    with pytest.raises(DataError,match="unit"):parse_payload(p,q)

def test_empty_dataset(response_data):
    p,q=response_data
    for k in p['properties']['parameter']:p['properties']['parameter'][k]={}
    with pytest.raises(DataError,match="no usable"):parse_payload(p,q)

def test_unexpected_payload(response_data):
    with pytest.raises(DataError):parse_payload({'wrong':1},response_data[1])

def test_invalid_measurement(response_data):
    p,q=response_data;p['properties']['parameter']['RH2M']['20250101']=110
    frame,issues=parse_payload(p,q)
    assert frame.RH2M.isna().iloc[0] and issues

def fetch(client,**kwargs):return client.fetch(8.3114,80.4037,date(2025,1,1),date(2025,1,7),**kwargs)

def test_success_and_cached_no_request(tmp_path,response_data):
    session=Session([Response(response_data[0])]);client=PowerClient(tmp_path,session=session,sleep=lambda _:None)
    assert fetch(client).provenance['mode']=='live NASA request'
    assert fetch(client).provenance['mode']=='local cache'
    assert session.calls==1

def test_bounded_retry(tmp_path,response_data):
    session=Session([requests.Timeout(),Response({},503),Response(response_data[0])])
    result=fetch(PowerClient(tmp_path,session=session,sleep=lambda _:None))
    assert session.calls==3 and len(result.frame)==7

def test_reject_4xx_no_retry(tmp_path):
    session=Session([Response({},422)])
    with pytest.raises(DataError,match="422"):fetch(PowerClient(tmp_path,session=session))
    assert session.calls==1

def test_outage_without_cache(tmp_path):
    session=Session([requests.Timeout()]*3)
    with pytest.raises(DataError,match="connection failed"):fetch(PowerClient(tmp_path,session=session,sleep=lambda _:None))
    assert session.calls==3

def test_matching_stale_fallback(tmp_path,response_data):
    session=Session([Response(response_data[0]),requests.Timeout(),requests.Timeout(),requests.Timeout()])
    client=PowerClient(tmp_path,session=session,sleep=lambda _:None)
    fetch(client)
    result=fetch(client,force=True)
    assert result.provenance['mode']=='stale cache after NASA outage' and result.issues

def test_wrong_location_not_reused(tmp_path,response_data):
    client=PowerClient(tmp_path,session=Session([Response(response_data[0]),*[requests.Timeout()]*3]),sleep=lambda _:None)
    fetch(client)
    with pytest.raises(DataError):client.fetch(-1.29,36.82,date(2025,1,1),date(2025,1,7))

def test_cache_integrity(tmp_path,response_data):
    client=PowerClient(tmp_path,session=Session([Response(response_data[0])]))
    fetch(client)
    envelope=json.loads(next(tmp_path.glob('*.json')).read_text())
    envelope['payload']['header']['title']='tampered'
    with pytest.raises(DataError,match="integrity"):unpack(envelope,'test')
