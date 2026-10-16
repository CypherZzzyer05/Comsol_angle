"""Read MPH metadata without modifying the COMSOL archive."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'models' / 'NUMBER37_original.mph'


def props(node, tag='propertyValue', key='name'):
    return [{**p.attrib, 'text': p.text} for p in node.findall('./' + tag)]


def inspect():
    with zipfile.ZipFile(MODEL) as archive:
        root = ET.fromstring(archive.read('dmodel.xml'))
        info = ET.fromstring(archive.read('modelinfo.xml'))
        version = archive.read('fileversion').decode().strip()
    parameters = [n.attrib for n in root.findall('./ModelParam/expressions')]
    physics = []
    for n in root.findall('.//PhysicsFeature'):
        physics.append({**n.attrib, 'settings': props(n, 'param'),
                        'selection': ET.tostring(n.find('selection'), encoding='unicode')
                        if n.find('selection') is not None else None})
    geometry = [{**n.attrib, 'settings': props(n)} for n in root.findall('.//GeomFeature')]
    meshes = []
    for n in root.findall('.//MeshSequence'):
        meshes.append({**n.attrib, 'geom': n.findtext('geom'),
                       'features': [{**f.attrib, 'settings': props(f)}
                                    for f in n.findall('.//MeshFeature')]})
    studies = [{**n.attrib, 'settings': props(n)} for n in root.findall('.//StudyFeature')]
    materials = [{**n.attrib, 'selection': ET.tostring(n.find('selection'), encoding='unicode')
                  if n.find('selection') is not None else None}
                 for n in root.findall('.//Material')]
    geometry_nodes = [{**n.attrib, 'units': [(c.tag, c.text) for c in n
                      if 'unit' in c.tag.lower()]}
                      for n in root.iter() if n.tag in ('Geometry', 'GeomSequence')]
    report = {'source_file': MODEL.name, 'sha256': hashlib.sha256(MODEL.read_bytes()).hexdigest(),
              'version': version, 'info': info.attrib, 'parameters': parameters,
              'physics': physics, 'geometry': geometry, 'geometry_nodes': geometry_nodes,
              'meshes': meshes, 'studies': studies, 'materials': materials}
    output = ROOT / 'docs' / 'model_inventory.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'version': version, 'parameters': parameters,
                      'geometry_nodes': geometry_nodes,
                      'mesh_features': [{ 'tag': m['tag'], 'features':
                       [{'tag': f.get('tag'), 'op': f.get('op')} for f in m['features']]}
                       for m in meshes]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    inspect()
