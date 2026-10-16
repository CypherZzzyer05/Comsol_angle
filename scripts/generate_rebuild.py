"""Generate a self-contained COMSOL 6.3 Java model from the source MPH definitions.

Reads model data, never executes source comments or embedded application methods.
No internal archive version fields are changed.
"""
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
with zipfile.ZipFile(ROOT / 'models/NUMBER37_original.mph') as archive:
    xml = ET.fromstring(archive.read('dmodel.xml'))


def q(value):
    return json.dumps(str(value), ensure_ascii=True)


def values(encoded):
    return [re.sub(r'\\(.)', r'\1', s) for s in re.findall(r"'((?:\\.|[^'])*)'", encoded)]


def arr(seq, kind='String'):
    return 'new ' + kind + '[]{' + ','.join(q(v) if kind == 'String' else str(v) for v in seq) + '}'


def expression(encoded):
    v = values(encoded)
    return q(v[0]) if len(v) == 1 else arr(v)


out = ['''import com.comsol.model.*;
import com.comsol.model.util.*;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

/** Generated from the geometry and material definitions of NUMBER37 XIE.mph. */
public class RebuildNumber37 {
  private static final String PROJECT_ROOT = __PROJECT_ROOT__;
  public static Model run() throws Exception {
    Model model=ModelUtil.create("Number37_63");
    model.label("NUMBER37_COMSOL63_angle_wavelength.mph");
    model.component().create("comp1",true);
    model.component("comp1").geom().create("geom1",3);
    model.component("comp1").geom("geom1").lengthUnit("nm");
    model.component("comp1").geom("geom1").geomRep("cadps");
''']


def emit(line):
    out.append('    ' + line)


for p in xml.findall('./ModelParam/expressions'):
    emit(f'model.param().set({q(p.get("name"))},{q(p.get("expr"))});')
emit('model.param().set("theta_inc","1[deg]","Incidence angle from the port normal");')
emit('model.param().set("phi_inc","0[deg]","Azimuth in the original periodic port frame");')

geometry = xml.find('./GeomList/GeomSequence[@tag="geom1"]')
for f in geometry.findall('./GeomFeatureList/GeomFeature'):
    tag, op = f.get('tag'), f.get('op')
    base = f'model.component("comp1").geom("geom1").feature({q(tag)})'
    if op in ('Block', 'Cylinder'):
        emit(f'model.component("comp1").geom("geom1").create({q(tag)},{q(op)});')
        props = {p.get('name')[2:]: p for p in f.findall('./propertyValue')}
        keys = ('size', 'base', 'pos') if op == 'Block' else ('r', 'h', 'pos')
        for key in keys:
            p = props[key]
            val = expression(p.get('valueMatrix')) if p.get('valueMatrix') else q(p.get('value'))
            emit(f'{base}.set({q(key)},{val});')
    elif op == 'Difference':
        emit(f'model.component("comp1").geom("geom1").create({q(tag)},"Difference");')
        for key in ('input', 'input2'):
            objs = [n.get('feature').split('/')[-1] for n in f.findall(f'./propertyValue[@name="p:{key}"]/Selection/object')]
            emit(f'{base}.selection({q(key)}).set({arr(objs)});')
        emit(f'{base}.set("keepsubtract",true);')
        emit(f'{base}.set("designbool",true);')
emit('model.component("comp1").geom("geom1").run();')
emit('StringBuilder audit=new StringBuilder("COMSOL "+ModelUtil.getComsolVersion()+"\\n");')
emit('audit.append("Geometry entities [vertices,edges,boundaries,domains]="+Arrays.toString(model.component("comp1").geom("geom1").getNEntities())+"\\n");')
emit('if (model.component("comp1").geom("geom1").getNDomains()!=41 || model.component("comp1").geom("geom1").getNBoundaries()!=243) throw new IllegalStateException("Geometry topology differs from source; do not reuse selections.");')
out.append('''    // Verify the physical meaning of every reused layer and port selection.
    int[] layerDomains={1,2,3,4,5};
    double[][] layerZ={{-2000,-1200},{-1200,0},{0,1200},{1200,2000},{0,220}};
    for(int i=0;i<layerDomains.length;i++) {
      model.component("comp1").geom("geom1").measureFinal().selection().geom(3);
      model.component("comp1").geom("geom1").measureFinal().selection().set(new int[]{layerDomains[i]});
      double[] b=model.component("comp1").geom("geom1").measureFinal().getBoundingBox();
      audit.append("Domain "+layerDomains[i]+" bbox="+Arrays.toString(b)+"\\n");
      if(Math.abs(b[4]-layerZ[i][0])>0.01 || Math.abs(b[5]-layerZ[i][1])>0.01) throw new IllegalStateException("Layer domain numbering differs from source");
    }
    for(int id:new int[]{6,12}) {
      model.component("comp1").geom("geom1").measureFinal().selection().geom(2);
      model.component("comp1").geom("geom1").measureFinal().selection().set(new int[]{id});
      double[] b=model.component("comp1").geom("geom1").measureFinal().getBoundingBox();
      audit.append("Port boundary "+id+" bbox="+Arrays.toString(b)+"\\n");
      double z=id==6 ? -1200:1200;
      if(Math.abs(b[4]-z)>0.01 || Math.abs(b[5]-z)>0.01) throw new IllegalStateException("Port boundary numbering differs from source");
    }
    System.out.println(audit.toString());
''')

for material in xml.findall('./MaterialList/Material'):
    tag=material.get('tag')
    base=f'model.component("comp1").material({q(tag)})'
    emit(f'model.component("comp1").material().create({q(tag)},"Common");')
    emit(f'{base}.label({q(material.get("name"))});')
    sel=material.find('./selection/explicit').get('entities')
    if sel:
        emit(f'{base}.selection().set({arr([int(n) for n in sel.split(",")[1:]], "int")});')
    else:
        emit(f'{base}.selection().all();')
    for group in material.findall('./MaterialModelList/MaterialModel'):
        gtag=group.get('tag')
        if gtag not in ('def','RefractiveIndex','DispersionModelSellmeierModified2'):
            continue
        gb=base+f'.propertyGroup({q(gtag)})'
        if gtag!='def':
            emit(f'{base}.propertyGroup().create({q(gtag)},{q(group.get("op"))});')
        for f in group.findall('./FunctionFeatureList/FunctionFeature'):
            ftag=f.get('tag')
            fb=gb+f'.func({q(ftag)})'
            emit(f'{gb}.func().create({q(ftag)},{q(f.get("op"))});')
            for p in f.findall('./propertyValue'):
                key=p.get('name')[2:]
                if key not in ('funcname','arg','pieces','argunit','fununit','table','interp','extrap','source'):
                    continue
                if p.get('valueMatrix'):
                    encoded=p.get('valueMatrix')
                    if key in ('table','pieces'):
                        rows=[]
                        for row in encoded.split('|')[1:]:
                            rows.append(arr(values(row)))
                        val='new String[][]{'+','.join(rows)+'}'
                    else:
                        val=expression(encoded)
                elif p.get('value') is not None:
                    val=q(p.get('value'))
                else:
                    continue
                emit(f'{fb}.set({q(key)},{val});')
        for p in group.findall('./param'):
            key=p.get('param')
            if key.startswith('INFO_PREFIX:'):
                continue
            emit(f'{gb}.set({q(key)},{expression(p.get("value"))});')
        for inp in group.findall('./input'):
            emit(f'{gb}.addInput({q(inp.text)});')

emit('model.component("comp1").physics().create("ewfd","ElectromagneticWavesFrequencyDomain","geom1");')
emit('model.component("comp1").physics("ewfd").feature("wee1").set("DisplacementFieldModel","RefractiveIndex");')
for feature in xml.findall('./PhysicsList/Physics/PhysicsFeatureList/PhysicsFeature'):
    tag=feature.get('tag')
    if tag not in ('pc1','pc2','port1','port2'):
        continue
    base=f'model.component("comp1").physics("ewfd").feature({q(tag)})'
    emit(f'model.component("comp1").physics("ewfd").create({q(tag)},{q(feature.get("op"))},2);')
    entities=[int(n) for n in feature.find('./selection/explicit').get('entities').split(',')[2:]]
    emit(f'{base}.selection().set({arr(entities,"int")});')
    allowed=('PortType','PortName','PortExcitation','Pin','PortSlit','SlitType','PortOrientation',
             'Polarization','InputType','Eampl','Hampl','alpha1_inc','alpha2_inc')
    for p in feature.findall('./param'):
        if p.get('param') in allowed:
            emit(f'{base}.set({q(p.get("param"))},{expression(p.get("value"))});')
    if tag.startswith('pc'):
        emit(f'{base}.set("PeriodicType","Floquet");')
        emit(f'{base}.set("Floquet_source","FromPeriodicPort");')
emit('model.component("comp1").physics("ewfd").feature("port1").set("alpha1_inc","theta_inc");')
emit('model.component("comp1").physics("ewfd").feature("port1").set("alpha2_inc","phi_inc");')
emit('model.component("comp1").coordSystem().create("pml1","PML");')
emit('model.component("comp1").coordSystem("pml1").selection().set(new int[]{1,4});')
emit('model.component("comp1").coordSystem("pml1").set("wavelengthSource","ewfd");')
out.append('''    model.study().create("std_angle");
    model.study("std_angle").label("Angles 1-5 deg; wavelength 1000-1500 nm");
    model.study("std_angle").create("param","Parametric");
    model.study("std_angle").feature("param").set("pname",new String[]{"theta_inc","lambda0"});
    model.study("std_angle").feature("param").set("plistarr",new String[]{"range(1,1,5)","range(1000,5,1500)"});
    model.study("std_angle").feature("param").set("punit",new String[]{"deg","nm"});
    model.study("std_angle").feature("param").set("sweeptype","filled");
    model.study("std_angle").feature("param").set("keepsol","all");
    model.study("std_angle").create("freq","Frequency");
    model.study("std_angle").feature("freq").set("plist","c_const/lambda0");
    model.study("std_angle").feature("freq").set("punit","Hz");
    model.component("comp1").mesh().create("mesh3");
''')
mesh=xml.find('./MeshList/MeshSequence[@tag="mesh3"]')


def mesh_feature(f, parent):
    tag,op=f.get('tag'),f.get('op')
    # 6.4 merges local face copying into Copy; 6.3 uses CopyFace.
    if op == 'Copy':
        op = 'CopyFace'
    base=parent+f'.feature({q(tag)})'
    if tag!='size':
        emit(f'{parent}.create({q(tag)},{q(op)});')
    sel=f.find('./selection/explicit')
    if sel is not None:
        entities=sel.get('entities','').split(',')
        start=1 if sel.get('dim')=='3' else 2
        emit(f'{base}.selection().geom("geom1",{sel.get("dim")});')
        emit(f'{base}.selection().set({arr([int(i) for i in entities[start:] if i],"int")});')
    properties = f.findall('./propertyValue')
    if op in ('Size', 'MeshSizeDefault'):
        # hauto/custom setters reset size values in 6.3, so set presets first.
        properties = sorted(properties, key=lambda p: {'p:hauto':0,'p:custom':1}.get(p.get('name'),2))
    for p in properties:
        key=p.get('name')[2:]
        if key.startswith('build') or key in ('geomrep','remeshsource'):
            continue
        if op == 'CopyFace' and key in ('mesh', 'dimension'):
            continue
        s=p.find('./Selection/explicit')
        if s is not None:
            entities=s.get('entities','').split(',')
            start=1 if s.get('dim')=='3' else 2
            emit(f'{base}.selection({q(key)}).set({arr([int(i) for i in entities[start:] if i],"int")});')
        elif p.get('value') is not None:
            emit(f'{base}.set({q(key)},{q(p.get("value"))});')
        elif p.get('valueMatrix') is not None:
            emit(f'{base}.set({q(key)},{expression(p.get("valueMatrix"))});')
    if op == 'Size':
        emit(f'{base}.set("hmaxactive",true);')
        emit(f'{base}.set("hminactive",true);')
    for child in f.findall('./MeshFeatureList/MeshFeature'):
        mesh_feature(child,base)


for f in mesh.findall('./MeshFeatureList/MeshFeature'):
    mesh_feature(f,'model.component("comp1").mesh("mesh3")')
out.append('''    model.modelPath(PROJECT_ROOT+"/models");
    model.save(PROJECT_ROOT+"/models/NUMBER37_COMSOL63_angle_wavelength.mph");
    model.component("comp1").mesh("mesh3").run();
    audit.append("Mesh elements="+model.component("comp1").mesh("mesh3").getNumElem()+"\\n");
    audit.append("Mesh min quality="+model.component("comp1").mesh("mesh3").getMinQuality()+"\\n");
    model.study("std_angle").createAutoSequences("all");
    int configuredSolvers=0;
    for(String sol:model.sol().tags()) {
      if(Arrays.asList(model.sol(sol).feature().tags()).contains("s1")) {
        model.sol(sol).feature("s1").feature("i1").active(true);
        model.sol(sol).feature("s1").feature("i1").set("itrestart",300);
        model.sol(sol).feature("s1").feature("fc1").set("linsolver","i1");
        configuredSolvers++;
      }
    }
    if(configuredSolvers==0) throw new IllegalStateException("No iterative solver was configured");
    model.result().table().create("tblrt","Table");
    model.result().table("tblrt").label("Port reflection and transmission");
    model.result().numerical().create("gevrt","EvalGlobal");
    model.result().numerical("gevrt").set("expr",new String[]{"ewfd.Rport_1","ewfd.Rtotal","ewfd.Tport_2","ewfd.Ttotal","ewfd.RTtotal","ewfd.Atotal"});
    model.result().numerical("gevrt").set("table","tblrt");
    for(String data:model.result().dataset().tags()) {
      if("Solution".equals(model.result().dataset(data).getType())) model.result().numerical("gevrt").set("data",data);
    }
    audit.append("Linear solver=GMRES with the generated wave-optics multigrid preconditioner\\n");
    audit.append("Angle sweep=1,2,3,4,5 deg\\nWavelength=1000:5:1500 nm\\nCombinations=505\\nSOLVED=false\\n");
    model.save(PROJECT_ROOT+"/models/NUMBER37_COMSOL63_angle_wavelength.mph");
    System.out.println(audit.toString());
    System.out.println("NUMBER37_REBUILD_OK");
    return model;
  }
  public static void main(String[] args) throws Exception {run();}
}
''')
(ROOT/'scripts/RebuildNumber37.java').write_text('\n'.join(out).replace('__PROJECT_ROOT__',q(ROOT.as_posix())),encoding='ascii')
print('Generated scripts/RebuildNumber37.java with exact source geometry, optical properties, and mesh settings.')
