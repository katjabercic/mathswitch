# mathswitch

`pip install django Pillow requests`

To prepare database migrations:
`python manage.py createmigrations`

To update the database with the new model:
`python manage.py migrate`

Manage Wikidata imported data:
```
python manage.py clear_wikidata
python manage.py import_wikidata
```

## WD query examples

```
  ?item ?image
  ?item_EN ?item_desc_EN
  ?item_NL ?item_desc_NL
  ?item_SI ?item_desc_SI
  ?mathworldID ?encyclopediaofmathematicsID ?nlabID ?proofwikiID
WHERE {
  # anything part of a topic that is studied by mathmatics!
  ?item wdt:P31 ?topic .
  ?topic wdt:P2579 wd:Q395 .
  OPTIONAL
  { ?item wdt:P18 ?image . }
  OPTIONAL
  { ?item wdt:P2812 ?mathworldID . }
  OPTIONAL
  { ?item wdt:7554 ?encyclopediaofmathematicsID . }
  OPTIONAL
  { ?item wdt:4215 ?nlabID . }
  OPTIONAL
  { ?item wdt:6781 ?proofwikiID . }
  
  # except for natural numbers
  filter(?topic != wd:Q21199) .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en".
    ?item rdfs:label ?item_EN.
    ?item schema:description ?item_desc_EN.
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "nl".
    ?item rdfs:label ?item_NL.
    ?item schema:description ?item_desc_NL.
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "si".
    ?item rdfs:label ?item_SI.
    ?item schema:description ?item_desc_SI.
  }
}
```




```
SELECT ?art WHERE {
  # an article in the english wikipedia with a corresponding wikidata entry
  ?art rdf:type schema:Article;
       schema:isPartOf <https://en.wikipedia.org/>;
       schema:about ?entry .

  # anything part of a topic that is studied by mathmatics!
  ?entry wdt:P31 ?topic .
  ?topic wdt:P2579 wd:Q395 .

  # except for natural numbers
  filter(?topic != wd:Q21199) .
}
```


```
SELECT ?itemLabel ?descriptionLabel ?areaLabel ?mathworld
WHERE
{
  BIND(wd:Q11518 AS ?item)
  ?item schema:description ?description.
  ?item wdt:P361 ?area.
  ?item wdt:P2812 ?mathworld.
#  wdt:P2812 wdt:1630 ?mathworld_formatter
  FILTER(LANG(?description) = "en")
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE]". }
}
```