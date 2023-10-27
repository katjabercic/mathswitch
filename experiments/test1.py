from typing import Optional

import requests

MATHWORLD_ID = 'P2812'

def fetch_wikidata(params):
    url = 'https://www.wikidata.org/w/api.php'
    try:
        return requests.get(url, params=params)
    except:
        return 'There was and error'

id1 = 'Q11518'

params = {
        'action': 'wbgetentities',
        'ids': id1,
        'format': 'json',
        'languages': 'en'
    }

# Fetch API
data = fetch_wikidata(params)

#show response as JSON
data = data.json()

def getMathWorldID(entity) -> Optional[str]:
    if MATHWORLD_ID not in entity['claims']:
        return None
    claims = entity['claims'][MATHWORLD_ID]
    dataItem = map(
        lambda x: x['mainsnak']['datavalue']['value'], 
        filter(lambda x: ('mainsnak' in x), claims)
        )
    return next(dataItem, None)


print(getMathWorldID(data['entities'][id1]))

# {'snaktype': 'value', 'property': 'P2812', 'hash': 'ff6856aa41b46b7af589897e7ad1e06476f2c4c1', 'datavalue': {'value': 'PythagoreanTheorem', 'type': 'string'}, 'datatype': 'external-id'}
