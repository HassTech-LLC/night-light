"""Explicit, one-shot postal lookup; never called by the scheduler."""
import json
import re
from urllib.parse import quote
from urllib.request import Request, urlopen
from smart_mode import coordinates


def lookup_postal(country,postal,opener=urlopen):
    country=country.strip().lower();postal=postal.strip()
    if not re.fullmatch('[a-z]{2}',country) or not re.fullmatch(r'[A-Za-z0-9 -]{2,12}',postal):
        raise ValueError('Enter a two-letter country code and a valid postal code.')
    request=Request(f'https://api.zippopotam.us/{country}/{quote(postal,safe="")}',headers={'User-Agent':'NightLightByHT/0.1'})
    with opener(request,timeout=10) as response:
        payload=response.read(65537)
    if len(payload)>65536: raise ValueError('Location response too large.')
    data=json.loads(payload)
    places=data.get('places',[])
    if not places: raise ValueError('No location found; enter coordinates instead.')
    # Postal areas may have several centroids; return choices for user review.
    result=[]
    for item in places[:50]:
        lat,lon=coordinates(item['latitude'],item['longitude'])
        result.append({'latitude':lat,'longitude':lon,'label':str(item.get('place name','Postal area'))[:100]})
    return result
