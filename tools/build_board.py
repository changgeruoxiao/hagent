"""Rev 1.1 placement and protected routing, based on AN4938 and SLVS839H.

Run with KiCad Python. Signal routing is restricted to F.Cu/B.Cu. Internal
layers are dedicated to GND and +3V3. Critical local circuits are pre-routed.
"""
import json
import math
import pcbnew as p
from pcb_common import Layout, mm, vec, xy
from project_config import *

PLACE = {
 'U1':(42.5,32.5,0),
 'J1':(42.5,3.2,90),'J2':(42.5,61.8,90),
 'J3':(79,27,90),'J4':(65,12,90),'J5':(10,54,0),'J6':(3.2,48,0),
 'U2':(15,13,0),'L1':(27.5,10.7,0),'D7':(20.6,10.3,90),
 'C23':(15,8.5,0),'C20':(9.8,12.365,180),'C21':(9.5,15,180),'C22':(9.5,18,180),
 'C24':(33.8,11.5,90),'C25':(38,11.5,90),'R14':(35,16.2,0),
 'R15':(17.5,17.3,0),'R16':(17.5,18.8,180),'R17':(23,17,270),'C26':(23,19,270),'C27':(20,15,0),
 'F1':(73,34,0),'D5':(67,36,0),'D6':(9,44,270),
 'U3':(73,26.7,0),'R10':(76.4,34,0),'R11':(79,34,0),'R12':(66,29.7,0),'R13':(66,31.2,0),
 'X1':(28.5,35,90),'C50':(26.3,33.75,180),'C51':(26.3,36.25,180),
 'X2':(28.5,27.5,90),'C52':(26.3,26.25,180),'C53':(26.3,28.75,180),
 'FB1':(23.7,43,0),'R20':(25,38,90),
 'C42':(27,41,180),'C43':(29.6,41.5,270),
 'C44':(27,39.25,180),'C45':(29.6,39.45,270),
 'R21':(26.5,23.8,0),'C48':(29.8,24.8,180),'R22':(31.5,17.5,0),
 'C40':(50.75,46,270),'C41':(55.8,24.75,0),
 'C46':(55.7,32.2,0),'C47':(55.2,30.25,0),
 'C60':(29.8,31.75,180),'C61':(29.8,37.7,180),
 'C62':(34.75,45.2,270),'C63':(41.25,45.2,270),'C64':(46.25,45.2,270),
 'C65':(52.4,44.95,270),'C66':(55.2,35.75,0),'C67':(55.2,22.5,0),
 'C68':(45.25,19.8,90),'C69':(40.25,19.8,90),'C70':(33.75,19.8,90),
 'C71':(37,18.4,0),'C72':(59,38.5,0),
 'SW1':(17,47,0),'C54':(24.5,32,0),'SW2':(71,45,0),'C55':(65,45,0),
 'R23':(13.5,55,0),'R24':(66,52,0),'D8':(69,52,0),'R25':(73,52,0),'D9':(76,52,0),
 'TP1':(62,54,0),'TP2':(60,56.5,0),'TP3':(48,48.5,0),
 'TP4':(23,50,0),'TP5':(17,55,0),'TP6':(41,15,0),
}
DECAP = {'17':'C60','30':'C61','39':'C62','52':'C63','62':'C64','72':'C65',
         '84':'C66','108':'C67','121':'C68','131':'C69','144':'C70','71':'C40','106':'C41','95':'C47'}

def rules_file():
    default={'name':'Default','clearance':.15,'track_width':.15,'via_diameter':.6,'via_drill':.3,
             'diff_pair_width':.2,'diff_pair_gap':.3,'diff_pair_via_gap':.3}
    power=dict(default,name='Power',track_width=.5)
    # A netclass nominal width also becomes the DRC minimum; narrow QFP necks
    # stay Default. High-current nets must satisfy the Power class throughout.
    design={'min_clearance':.15,'min_track_width':.15,'min_through_hole_diameter':.3,
            'min_via_diameter':.6,'min_via_annular_width':.15,'min_hole_clearance':.25,
            'min_hole_to_hole':.25,'min_copper_edge_clearance':.3,
            'min_silk_clearance':.15,'min_text_height':.8,'min_text_thickness':.12}
    severities={k:'error' for k in ['clearance','shorting_items','unconnected_items','hole_to_hole',
                  'copper_edge_clearance','courtyards_overlap','net_conflict','footprint_symbol_mismatch']}
    severities.update({'silk_overlap':'warning','silk_over_copper':'warning','via_dangling':'warning'})
    obj={'meta':{'filename':PCB.with_suffix('.kicad_pro').name,'version':3},
         'board':{'design_settings':{'rules':design,'rule_severities':severities}},
         'net_settings':{'classes':[default,power],
         'netclass_patterns':[{'netclass':'Power','pattern':n} for n in ['+5V','/5VIN','/VBUS','/VBUS_F','/3V3_SW','/PH']]}}
    PCB.with_suffix('.kicad_pro').write_text(json.dumps(obj,indent=2),encoding='utf-8')

def critical_routes(l):
    # MCU local decoupling; every pin has a short direct capacitor connection.
    for pin,cap in DECAP.items(): l.connect('U1',pin,cap,'1',.2)
    l.connect('C47','1','C46','1',.3,via_points=[(54.4,31.2)])
    l.connect('C40','1','TP3','1',.25,via_points=[(48.8,45.225),(48.8,48.25)])
    # Oscillators stay on the front, outside the package, with no signal vias.
    for pins,x,cs in [(('23','24'),'X1',('C50','C51')),(('8','9'),'X2',('C52','C53'))]:
        for pin,xpin,cap in zip(pins,('1','2'),cs):
            target=l.at(x,xpin);src=l.at('U1',pin)
            elbow=(30.6,src[1])
            l.connect('U1',pin,x,xpin,.2,via_points=[elbow,(29.6,target[1])])
            l.connect(x,xpin,cap,'1',.2)
    # Analog supply and reference remain beside pins 32/33.
    for cap,pin in [('C43','33'),('C45','32'),('C48','6')]: l.connect('U1',pin,cap,'1',.2)
    l.connect('C45','1','C44','1',.25,allow_back=True)
    l.connect('C43','1','C42','1',.25,allow_back=True)
    l.connect('FB1','2','C42','1',.3)
    l.connect('C42','1','R20','1',.25,via_points=[(26.2,42.2),(23.2,42.2),(23.2,38.485)])
    l.connect('R20','2','C44','1',.25,via_points=[(25,37),(27.775,37)])
    l.connect('R21','2','C48','1',.2)
    # USB FS pair, front only. The small connector fanout is verified separately.
    l.connect('U1','104','U3','1',.2)
    l.connect('U1','103','U3','3',.2,via_points=[(69,26.25),(70.4,27.65)])
    # Power stage: place catch diode and inductor next to PH; no remote PH testpoint.
    l.connect('U2','8','D7','1',1.0,via_points=[(19,11.095)])
    l.connect('D7','1','L1','1',1.0)
    l.connect('U2','1','C23','1',.2,via_points=[(12.525,8.5)])
    l.connect('C23','2','U2','8',.2,via_points=[(17.475,8.5)])
    l.connect('U2','2','C20','1',.5)
    l.connect('U2','2','C21','1',.5,via_points=[(11.8,12.365),(11.8,15)])
    l.connect('C21','1','C22','1',.5)
    l.connect('L1','2','C24','1',1.0,via_points=[(28.8,12.25)])
    l.connect('C24','1','C25','1',1.0)
    l.connect('C25','1','R14','1',.6,via_points=[(33.5,13.3),(31.1,13.3)])
    l.connect('R14','1','TP6','1',.5,via_points=[(31.05,16.5),(35,16.5)])
    l.connect('U2','5','R15','2',.2,via_points=[(18.01,16)])
    l.connect('R15','2','R16','1',.2)
    l.connect('U2','6','C27','1',.2,via_points=[(18.8,13.635),(18.8,15)])
    l.connect('C27','1','R17','1',.2)
    l.connect('R17','2','C26','1',.2)
    l.connect('C24','1','R15','1',.5,allow_back=True)

def main():
    l=Layout()
    missing=set(l.comps)-set(PLACE)
    if missing: raise ValueError(f'Unplaced: {missing}')
    for ref,pos in PLACE.items(): l.place(ref,*pos)
    for i,pos in enumerate([(6,33),(79,38),(30,55),(55,55)],1):
        l.place('H'+str(i),*pos,fp_id='MountingHole:MountingHole_3.2mm_M3_Pad')
    l.assign_nets(); l.save();rules_file()
    try:critical_routes(l)
    finally:l.save()
    # Local ground vias: two for every decoupling capacitor, one for other pads.
    for ref in ['C'+str(n) for n in range(60,73)]+['C40','C41','C42','C43','C44','C45','C46','C47','C48','C50','C51','C52','C53']:
        l.fanout(ref,'2',2)
    # Plane connections at every SMD rail pin. Connected capacitor pairs also
    # receive their own power vias so the plane supplies the cap before the MCU.
    for ref,fp in l.fps.items():
        for q in fp.Pads():
            name=q.GetNetname()
            if name=='+3V3' and ref!='U1': l.fanout(ref,q.GetNumber(),1)
            elif name=='GND' and not ref.startswith('C'): l.fanout(ref,q.GetNumber(),1)
    for ref in ['C20','C21','C22','C24','C25','C26','C27','C54','C55']:
        l.fanout(ref,'2',1)
    l.zone(p.In1_Cu,'GND'); l.zone(p.In2_Cu,'+3V3')
    l.save()
    print('Reloading board before filling zones...',flush=True)
    l.board=p.LoadBoard(str(PCB));l.board.BuildConnectivity()
    filler=p.ZONE_FILLER(l.board)
    filler.Fill(list(l.board.Zones()))
    print('Zones filled.',flush=True)
    l.save()
    if not p.ExportSpecctraDSN(l.board,str(DSN)):raise RuntimeError('DSN export failed')
    print(f'Placed {len(l.fps)} footprints; protected {len(list(l.board.GetTracks()))} tracks/vias.',flush=True)

if __name__=='__main__':main()
