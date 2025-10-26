import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import re
from bs4 import BeautifulSoup
from random import choice

DATASET_XML = "datasets/dataset.xml"


def clean_text(text):
    if not text:
        return ""

    text = re.sub(r'\[[0-9]+\]', '', text)

    text = re.sub(r'\([^)]*\)', ' ', text)

    text = re.sub(r'([a-zăâîșț])([A-ZĂÂÎȘȚ])', r'\1 \2', text)

    text = re.sub(r'([0-9])([a-zA-Zăâîșț])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Zăâîșț])([0-9])', r'\1 \2', text)

    text = re.sub(r'\s+', ' ', text).strip()

    return text

def extract_description(info_text):
    if not info_text:
        return ""
    sentences = re.split(r'(?<=[.!?]) +', info_text)
    desc = " ".join(sentences[:3])

    if len(desc) < 200 and len(sentences) > 3:
        desc += " " + " ".join(sentences[3:5])

    desc = clean_text(desc)
    return desc

def enrich_wikipedia_data(monument):
    wiki_url = monument.get("wiki")
    if not wiki_url:
        return monument

    try:
        wiki_url_quoted = urllib.parse.quote(wiki_url, safe=":/?=&")

        print(f"🔎 Obțin informații din: {wiki_url_quoted}")

        req = urllib.request.Request(
            wiki_url_quoted,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )

        html = urllib.request.urlopen(req, timeout=10).read()
        soup = BeautifulSoup(html, "html.parser")

        paragraph = None
        for p in soup.find_all("p"):
            txt = p.get_text(strip=True)
            if len(txt) > 50:
                paragraph = txt
                break

        if paragraph and not monument.get("descriere"):
            monument["descriere"] = extract_description(paragraph)

    except Exception as e:
        print(f"⚠️ Wikipedia fetch fail pentru {monument.get('nume', 'Unknown')}: {e}")

    return monument

def save_monuments(monuments):
    tree = ET.parse(DATASET_XML)
    root = tree.getroot()

    elems = root.findall("atractie")
    for elem, m in zip(elems, monuments):
        if m.get("descriere"):
            node = elem.find("descriere")
            if node is None:
                node = ET.SubElement(elem, "descriere")
            node.text = m["descriere"]
    tree.write(DATASET_XML, encoding="utf-8", xml_declaration=True)
    print("✅ Dataset actualizat cu succes în dataset.xml!")

def load_monuments():
    tree = ET.parse(DATASET_XML)
    root = tree.getroot()

    monuments = []
    for elem in root.findall("atractie"):
        m = {
            "nume": elem.findtext("nume"),
            "localitate": elem.findtext("localitate"),
            "image": elem.findtext("imagine"),
            "wiki": elem.findtext("wikipedia"),
            "descriere": elem.findtext("descriere"),
            "lat": elem.findtext("lat"),
            "lon": elem.findtext("lon"),
        }
        try:
            m["lat"] = float(m["lat"]) if m["lat"] else None
            m["lon"] = float(m["lon"]) if m["lon"] else None
        except:
            m["lat"], m["lon"] = None, None

        monuments.append(m)
    return monuments

def enrich_all():
    monuments = load_monuments()
    updated = []
    for i, m in enumerate(monuments):
        print(f"--- Processing {i+1}/{len(monuments)}: {m.get('nume')}")
        m = enrich_wikipedia_data(m)
        updated.append(m)
    save_monuments(updated)

def match_monument_by_name(name: str):
    name = name.lower()
    list_monuments = load_monuments()
    for m in list_monuments:
        if name in m["nume"].lower():
            return m
    return choice(list_monuments)

if __name__ == "__main__":
    print("🚀 Start Wikipedia enrichment...")
    enrich_all()

    monuments = load_monuments()
    for m in monuments[:2]:
        print("\n--------------------------------")
        print(f"Nume: {m['nume']}")
        print(f"Localitate: {m['localitate']}")
        print(f"Descriere (scurtă): {m.get('descriere','N/A')[:400]}...")
        print(f"Imagine: {m['image']}")
        print(f"Wiki: {m['wiki']}")
