from typing import Optional

import requests
from concept import Concept

id1 = "Q11518"

# show response as JSON
data = data.json()

# def getMathWorldID(entity) -> Optional[str]:
#     if MATHWORLD_ID not in entity['claims']:
#         return None
#     claims = entity['claims'][MATHWORLD_ID]
#     dataItem = map(
#         lambda x: x['mainsnak']['datavalue']['value'],
#         filter(lambda x: ('mainsnak' in x), claims)
#         )
#     return next(dataItem, None)


print(getMathWorldID(data["entities"][id1]))

# {'snaktype': 'value', 'property': 'P2812', 'hash': 'ff6856aa41b46b7af589897e7ad1e06476f2c4c1', 'datavalue': {'value': 'PythagoreanTheorem', 'type': 'string'}, 'datatype': 'external-id'}


class WikidataAPI:
    API_URL = "https://www.wikidata.org/w/api.php"

    PROPERTY = {"MATHWORLD_ID": "P2812"}

    @staticmethod
    def fetchConcept(wdId: str) -> Optional[Concept]:
        try:
            response = requests.get(
                WikidataAPI.API_URL,
                params={
                    "action": "wbgetentities",
                    "format": "json",
                    "ids": wdId,
                    "props": "labels|descriptions|sitelinks",
                    "languages": "en",
                },
            )
        except:
            return f"Failed retrieving the concept for the identifier {wdId}"
        data = response.json()
