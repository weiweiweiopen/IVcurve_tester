"""Export/check the two hardware snapshots without changing their design files.

Requires KiCad 10 CLI. Override KICAD_CLI on non-macOS installations.
"""
from pathlib import Path
import collections
import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
CLI=os.environ.get('KICAD_CLI') or shutil.which('kicad-cli') or '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(args,cwd):
    result=subprocess.run([CLI]+[str(a) for a in args],cwd=cwd,capture_output=True,text=True,timeout=180)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)

def build(name):
    project=ROOT/'hardware'/name;pcb=project/'Marc_USB.kicad_pcb';sch=project/'Marc_USB.kicad_sch'
    checks=project/'checks';out=project/'fabrication'
    initial={p.name:sha(p) for p in project.iterdir() if p.suffix in ('.kicad_pro','.kicad_pcb','.kicad_sch','.kicad_dru')}
    with tempfile.TemporaryDirectory(prefix='ivcurve-export-') as td:
        temp=Path(td);gerbers=temp/'gerbers';gerbers.mkdir()
        command(['sch','erc','--format','json','--output',checks/'erc.json',sch],project)
        command(['pcb','drc','--format','json','--schematic-parity','--output',checks/'drc.json',pcb],project)
        erc=json.loads((checks/'erc.json').read_text());drc=json.loads((checks/'drc.json').read_text())
        violations=[v for sheet in erc['sheets'] for v in sheet['violations']]
        assert not violations,('ERC',name,violations)
        assert not drc['unconnected_items'] and not drc['schematic_parity'],('Connectivity/parity',name)
        blocking=[v for v in drc['violations'] if v['severity']=='error' and v['type']!='courtyards_overlap']
        assert not blocking,('Non-courtyard DRC error',name,blocking)
        command(['sch','export','netlist','--format','kicadxml','--output',temp/'native.xml',sch],project)
        netlist=ET.parse(temp/'native.xml')
        groups=collections.defaultdict(list)
        for c in netlist.findall('./components/comp'):
            if c.attrib['ref'].startswith('#'):continue
            fields={f.attrib['name']:f.text or '' for f in c.findall('./fields/field')}
            groups[(c.findtext('value',''),c.findtext('footprint',''),fields.get('MPN',''))].append(c.attrib['ref'])
        with (project/'BOM.csv').open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(['Designators','Quantity','Value','Footprint','MPN'])
            for (value,fp,mpn),refs in sorted(groups.items()):writer.writerow([','.join(refs),len(refs),value,fp,mpn])
        with (checks/'pin-map.csv').open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(['Reference','Pin','Net'])
            for net in netlist.findall('./nets/net'):
                for node in net.findall('node'):writer.writerow([node.attrib['ref'],node.attrib['pin'],net.attrib['name']])
        command(['pcb','export','gerbers','--layers','F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts','--output',str(gerbers)+os.sep,pcb],project)
        command(['pcb','export','drill','--format','excellon','--excellon-units','mm','--excellon-separate-th','--output',str(gerbers)+os.sep,pcb],project)
        archive=out/('basic-JLCPCB.zip' if name=='basic' else 'charging-PROTOTYPE-JLCPCB.zip')
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for f in sorted(gerbers.iterdir()):
                if f.suffix in ('.gtl','.gbl','.gts','.gbs','.gto','.gbo','.gm1','.drl','.gbrjob'):z.write(f,f.name)
        with zipfile.ZipFile(archive) as z:assert z.testzip() is None and len(z.namelist())==10
        command(['sch','export','pdf','--output',project/'schematic.pdf',sch],project)
        command(['pcb','render','--output',project/'preview.png','--width','1000','--height','1400','--side','top','--background','opaque','--quality','high','--zoom','.8',pcb],project)
    assert initial=={p.name:sha(p) for p in project.iterdir() if p.suffix in ('.kicad_pro','.kicad_pcb','.kicad_sch','.kicad_dru')}
    summary={'board':name,'status':'prototype','pcb_sha256':sha(pcb),'fabrication_zip':archive.name,'fabrication_zip_sha256':sha(archive),
        'ERC_violations':len(violations),'unconnected':len(drc['unconnected_items']),'schematic_parity':len(drc['schematic_parity']),
        'DRC_by_type':dict(collections.Counter(v['type'] for v in drc['violations'])),
        'DRC_by_severity':dict(collections.Counter(v['severity'] for v in drc['violations'])),
        'core_design_files_unchanged':True,'hardware_test':'Not performed; courtyard/stack-height assumptions and complete harvesting/measurement cycle remain unverified.'}
    (checks/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    for variant in ('basic','charging'):build(variant)
