"""Prepare immutable routing inputs and run Freerouting with 2 signal layers."""
import argparse, hashlib, json, re, subprocess
from project_config import *

ROUTE_DSN=OUT/(STEM+'.routing.dsn')
POWER_NETS={'+5V','/VBUS','/VBUS_F','/5VIN','/3V3_SW','/PH'}

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def prepare():
    s=DSN.read_text(encoding='utf-8');start=s.index('(class kicad_default');depth=0
    for m in re.finditer(r'"(?:[^"\\]|\\.)*"|[()]',s[start:]):
        if m.group()=='(':depth+=1
        elif m.group()==')':
            depth-=1
            if depth==0:end=start+m.end();break
    else:raise ValueError('Unbalanced DSN class')
    block=s[start:end];a=block.index('(circuit')
    names=re.findall(r'"(?:[^"\\]|\\.)*"|[^\s()]+',block[:a])[2:]
    assert POWER_NETS.issubset(set(names))
    power='(class Power '+' '.join(sorted(POWER_NETS))+'\n'+block[a:block.index('(rule')]+'(rule (width 500) (clearance 150)))'
    result=s[:start]+'(class kicad_default '+' '.join(n for n in names if n not in POWER_NETS)+'\n'+block[a:]+'\n'+power+s[end:]
    result=result.replace('(clearance 37.5 (type smd_smd))','(clearance 150 (type smd_smd))')
    ROUTE_DSN.write_text(result,encoding='utf-8')
    (OUT/'routing_inputs.json').write_text(json.dumps({p.name:digest(p) for p in [SCH,NET,PCB,PCB.with_suffix('.kicad_pro'),DSN,ROUTE_DSN]},indent=2),encoding='utf-8')

def run(passes=8):
    prepare()
    if SES.exists():
        SES.with_suffix('.previous.ses').write_bytes(SES.read_bytes());SES.unlink()
    fr=WS/'tools/freerouting'
    cmd=[str(fr/'jdk-25.0.4.1+1-jre/bin/java.exe'),'-jar',str(fr/'freerouting.jar'),'-de',str(ROUTE_DSN),'-do',str(SES),'-mp',str(passes),'-mt','1','-l','en']
    print('Freerouting started; log:',OUT/'freerouting.log',flush=True)
    with (OUT/'freerouting.log').open('w',encoding='utf-8') as log:
        subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=str(fr),check=True,timeout=5400)
    if not SES.exists() or SES.stat().st_size<100:raise RuntimeError('No fresh SES produced')
    print('Fresh SES written. DRC and hardware checks still required.',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--max-passes',type=int,default=8)
    run(ap.parse_args().max_passes)
