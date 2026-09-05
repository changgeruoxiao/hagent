"""CLI wrapper: preserve full diagnostics on disk, show compact actionable output."""
import collections
import json
import subprocess
import sys
from project_config import *

def run(args):
    r=subprocess.run([str(KI/'kicad-cli.exe'),*map(str,args)],capture_output=True,text=True,encoding='utf-8',errors='replace')
    if r.returncode:
        print(r.stdout); print(r.stderr[-2000:]); raise RuntimeError(f'kicad-cli exit {r.returncode}')
    return r

def drc(details=False):
    path=OUT/'drc.json'
    run(['pcb','drc','--format','json','--schematic-parity','--output',path,PCB])
    data=json.loads(path.read_text(encoding='utf-8'))
    for key in ['violations','unconnected_items','schematic_parity']:
        items=data.get(key,[])
        print(key,len(items),dict(collections.Counter((x['severity'],x['type']) for x in items)))
        if details and key!='unconnected_items':
            for v in items[:120]:
                if v['severity']!='error':continue
                print(v['type'],v['description'])
                for i in v.get('items',[]):print('  ',i['description'],i.get('pos'),i.get('uuid'))
    return data

if __name__=='__main__':
    drc('--details' in sys.argv)
