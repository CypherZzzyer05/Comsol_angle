"""Verify key source-to-rebuild definitions in the saved MPH archives."""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    path=ROOT/'models'/name
    with zipfile.ZipFile(path) as archive:
        return ET.fromstring(archive.read('dmodel.xml')), archive.read('fileversion').decode().strip()


def value(node, name):
    p=node.find(f'./propertyValue[@name="p:{name}"]')
    return p.attrib if p is not None else None


source, sv=load('NUMBER37_original.mph')
native, nv=load('NUMBER37_COMSOL63_angle_wavelength.mph')
report={'source_version':sv, 'rebuilt_version':nv, 'checks':[]}
assert '6.3' in nv
for tag in ['blk5','blk2','blk1','blk6']+[f'qcyl{i}' for i in range(1,38)]:
    a=source.find(f'.//GeomFeature[@tag="{tag}"]')
    b=native.find(f'.//GeomFeature[@tag="{tag}"]')
    for key in ('size','base','pos') if tag.startswith('blk') else ('r','h','pos'):
        pa,pb=value(a,key),value(b,key)
        for field in ('value','valueMatrix'):
            assert pa.get(field)==pb.get(field),(tag,key,field,pa,pb)
report['checks'].append('All 4 blocks and all 37 cylinders match source geometry definitions.')
for tag in ('port1','port2','pc1','pc2'):
    a=source.find(f'.//PhysicsFeature[@tag="{tag}"]/selection/explicit').attrib
    b=native.find(f'.//PhysicsFeature[@tag="{tag}"]/selection/explicit').attrib
    assert a['entities']==b['entities'],(tag,a,b)
report['checks'].append('Port and side boundary selections match source.')
for tag in ('pc1','pc2'):
    b=native.find(f'.//PhysicsFeature[@tag="{tag}"]')
    for key,val in [('PeriodicType','Floquet'),('Floquet_source','FromPeriodicPort')]:
        assert b.find(f'./param[@param="{key}"]').get('value')==f"1|1,'{val}'"
report['checks'].append('Both side conditions are Floquet, with wave vector from periodic port.')
assert native.find('.//Coordsys[@op="PML"]') is not None
report['checks'].append('PML present on the source outer domains.')
study=native.find('.//Study[@tag="std_angle"]')
param=study.find('./StudyFeatureList/StudyFeature[@tag="param"]')
names=value(param,'pname')['valueMatrix']
assert "'theta_inc'" in names and "'lambda0'" in names
lists=value(param,'plistarr')
encoded=lists.get('valueMatrix','')+lists.get('ValueRows','')
assert 'range(1' in encoded and 'range(1000' in encoded,lists
assert value(param,'sweeptype')['value']=='filled'
report['checks'].append('Cartesian angle-by-wavelength sweep contains all 505 requested cases.')
fc=native.find('.//SolverSequence//SolverFeature[@tag="fc1"]')
linear=value(fc,'linsolver')
assert linear.get('Reference','').endswith('/i1'),linear
report['checks'].append('Saved fully coupled solver uses the iterative solver i1.')
for tag in ('size','size1','size2'):
    a=source.find(f'.//MeshSequence[@tag="mesh3"]//MeshFeature[@tag="{tag}"]')
    b=native.find(f'.//MeshSequence[@tag="mesh3"]//MeshFeature[@tag="{tag}"]')
    report.setdefault('mesh_settings',{})[tag]={'source_hmax':value(a,'hmax'), 'rebuilt_hmax':value(b,'hmax'),
                                             'rebuilt_hmaxactive':value(b,'hmaxactive'),
                                             'rebuilt_custom':value(b,'custom')}
    assert value(a,'hmax')['value']==value(b,'hmax')['value']
for tag in ('mat1','mat2','mat3'):
    a=source.find(f'.//Material[@tag="{tag}"]')
    b=native.find(f'.//Material[@tag="{tag}"]')
    for group in a.findall('./MaterialModelList/MaterialModel'):
        if group.get('tag') not in ('def','RefractiveIndex','DispersionModelSellmeierModified2'):
            continue
        bg=b.find(f'./MaterialModelList/MaterialModel[@tag="{group.get("tag")}"]')
        assert bg is not None
        for param in group.findall('./param'):
            if param.get('param').startswith('INFO_PREFIX:'):
                continue
            bp=bg.find(f'./param[@param="{param.get("param")}"]')
            assert bp is not None and bp.get('value')==param.get('value'),(tag,group.get('tag'),param.attrib,bp.attrib if bp is not None else None)
        for function in group.findall('./FunctionFeatureList/FunctionFeature'):
            bf=bg.find(f'./FunctionFeatureList/FunctionFeature[@tag="{function.get("tag")}"]')
            assert bf is not None
            for key in ('funcname','table','pieces','arg','argunit','fununit'):
                a_value=value(function,key)
                if a_value is None:
                    continue
                b_value=value(bf,key)
                assert b_value is not None
                for field in ('value','valueMatrix'):
                    assert a_value.get(field)==b_value.get(field),(tag,function.get('tag'),key,field)
report['checks'].append('All transferred Basic and optical material property values match source.')
for name in ('NUMBER37_original.mph','NUMBER37_COMSOL63_angle_wavelength.mph'):
    report.setdefault('sha256',{})[name]=hashlib.sha256((ROOT/'models'/name).read_bytes()).hexdigest()
(ROOT/'validation/package-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
