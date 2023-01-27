import os
from tqdm import tqdm
from acdh_cidoc_pyutils import (
    create_e52,
    normalize_string,
    extract_begin_end,
    make_appelations,
    make_ed42_identifiers,
    make_birth_death_entities
)
from acdh_cidoc_pyutils.namespaces import CIDOC, FRBROO
from acdh_tei_pyutils.tei import TeiReader
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS


domain = "https://sk.acdh.oeaw.ac.at/"
SK = Namespace(domain)

rdf_dir = "./rdf"

os.makedirs(rdf_dir, exist_ok=True)

g = Graph()
doc = TeiReader("./data/indices/listperson.xml")
nsmap = doc.nsmap
items = doc.any_xpath(".//tei:person")
for x in tqdm(items, total=len(items)):
    xml_id = x.attrib["{http://www.w3.org/XML/1998/namespace}id"].lower()
    item_id = f"{SK}{xml_id}"
    subj = URIRef(item_id)
    g.add((subj, RDF.type, CIDOC["E21_Person"]))
    g += make_ed42_identifiers(subj, x, type_domain=f"{SK}types", default_lang="und")
    g += make_appelations(subj, x, type_domain=f"{SK}types", default_lang="und")
    for y in x.xpath(".//tei:occupation", namespaces=nsmap):
        label = y.text
        occupation_id = y.attrib["n"]
        uri = URIRef(f"{SK}{xml_id}/occupation/{occupation_id}")
        g.add((subj, CIDOC["P14i_performed"], uri))
        g.add((uri, RDF.type, FRBROO["F51"]))
        g.add((uri, RDFS.label, Literal(normalize_string(label), lang="de")))
        begin, end = extract_begin_end(y)
        if begin != "" or end != "":
            ts_uri = URIRef(f"{uri}/timestamp")
            g.add((uri, CIDOC["P4_has_time-span"], ts_uri))
            g += create_e52(ts_uri, begin_of_begin=begin, end_of_end=end)
    for y in x.xpath(".//tei:affiliation[@ref]", namespaces=nsmap):
        affiliation_id = y.attrib["ref"][1:].lower()
        end, _ = extract_begin_end(y)
        uri = URIRef(f"{SK}{affiliation_id}")
        join_uri = URIRef(f"{uri}/joining/{xml_id}")
        g.add((join_uri, RDF.type, CIDOC["E85_Joining"]))
        g.add((join_uri, CIDOC["P143_joined"], subj))
        g.add((join_uri, CIDOC["P144_joined_with"], uri))
        if begin != "":
            ts_uri = URIRef(f"{join_uri}/timestamp/{begin}")
            g.add((join_uri, CIDOC["P4_has_time-span"], ts_uri))
            g += create_e52(ts_uri, begin_of_begin=begin, end_of_end=begin)
        try:
            end = y.attrib["notAfter"]
        except KeyError:
            end = ""
        if end != "":
            join_uri = URIRef(f"{uri}/leaving/{xml_id}")
            g.add((join_uri, RDF.type, CIDOC["E86_Leaving"]))
            g.add((join_uri, CIDOC["P145_separated"], subj))
            g.add((join_uri, CIDOC["P146_separated_from"], uri))
            if end != "":
                ts_uri = URIRef(f"{join_uri}/timestamp/{end}")
                g.add((join_uri, CIDOC["P4_has_time-span"], ts_uri))
                g += create_e52(ts_uri, begin_of_begin=end, end_of_end=end)
    try:
        label = x.xpath(
            './/tei:persName[@type="sk"][@subtype="pref"]/text()', namespaces=doc.nsmap
        )[0]
    except IndexError:
        label = None
    # birth
    try:
        birth = x.xpath(".//tei:birth[@when]/@when", namespaces=doc.nsmap)[0]
    except IndexError:
        birth = None
    if birth:
        birth_g, b_uri, birth_timestamp = make_birth_death_entities(subj, x, event_type="birth", verbose=True)
        g += birth_g
        g += create_e52(birth_timestamp, begin_of_begin=birth, end_of_end=birth)
        try:
            place = x.xpath(".//tei:birth/tei:placeName", namespaces=doc.nsmap)[0]
        except IndexError:
            place = None
        if place is not None:
            place_id = place.attrib["key"][1:].lower()
            place_name = place.text
            place_uri = URIRef(f"{SK}{place_id}")
            g.add((b_uri, CIDOC["P7_took_place_at"], place_uri))
            g.add((place_uri, RDF.type, CIDOC["E53_Place"]))
    # death
    try:
        death = x.xpath(".//tei:death[@when]/@when", namespaces=doc.nsmap)[0]
    except IndexError:
        death = None
    if death:
        death_g, b_uri, death_timestamp = make_birth_death_entities(subj, x, event_type="death", verbose=True, default_prefix="Tod von")
        g += death_g
        g += create_e52(death_timestamp, begin_of_begin=death, end_of_end=death)
        try:
            place = x.xpath(".//tei:death/tei:placeName", namespaces=doc.nsmap)[0]
        except IndexError:
            place = None
        if place is not None:
            place_id = place.attrib["key"][1:].lower()
            place_name = place.text
            place_uri = URIRef(f"{SK}{place_id}")
            g.add((b_uri, CIDOC["P7_took_place_at"], place_uri))
            g.add((place_uri, RDF.type, CIDOC["E53_Place"]))
doc = TeiReader("./data/indices/listplace.xml")
for x in doc.any_xpath(".//tei:place"):
    xml_id = x.attrib["{http://www.w3.org/XML/1998/namespace}id"].lower()
    item_id = f"{SK}{xml_id}"
    subj = URIRef(item_id)
    g.add((subj, RDF.type, CIDOC["E53_Place"]))
    g += make_appelations(subj, x, type_domain=f"{SK}types/", default_lang="und")
    g += make_ed42_identifiers(subj, x, type_domain=f"{SK}types", default_lang="und")
doc = TeiReader("./data/indices/listorg.xml")
for x in doc.any_xpath(".//tei:org"):
    xml_id = x.attrib["{http://www.w3.org/XML/1998/namespace}id"].lower()
    item_id = f"{SK}{xml_id}"
    subj = URIRef(item_id)
    g.add((subj, RDF.type, CIDOC["E74_Group"]))
    g += make_appelations(subj, x, type_domain=f"{SK}types/", default_lang="und")
    g += make_ed42_identifiers(subj, x, type_domain=f"{SK}types", default_lang="und")
g.serialize(f"{rdf_dir}/data.ttl")
