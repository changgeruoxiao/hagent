"""KiCad geometry helpers. All clearance decisions use KiCad shapes, in nm."""
import math
import pcbnew as p
from project_config import *
from sch_build import parse

def mm(v):
    return p.FromMM(v)

def vec(xy):
    return p.VECTOR2I(mm(xy[0]), mm(xy[1]))

def xy(point):
    return (point.x / 1e6, point.y / 1e6)

def child(e, name, default=None):
    return next((x for x in e if isinstance(x,list) and x and x[0]==name), default)

def read_netlist():
    data=parse(NET.read_text(encoding='utf-8'))
    comps={}
    for c in child(data,'components')[1:]:
        ref=child(c,'ref')[1]
        fields={}
        comps[ref]={'value':child(c,'value',['',''])[1], 'footprint':child(c,'footprint',['',''])[1],
                    'uuid':child(c,'tstamps',['',''])[1],
                    'path':child(child(c,'sheetpath',[]),'tstamps',['','/'])[1],
                    'dnp': any(x[0]=='property' and child(x,'name',['',''])[1]=='dnp' for x in c if isinstance(x,list)),
                    'fields':fields}
    nets={}
    for n in child(data,'nets')[1:]:
        name=child(n,'name')[1]
        nets[name]=[(child(x,'ref')[1],child(x,'pin')[1]) for x in n if isinstance(x,list) and x[0]=='node']
    return comps,nets

class Layout:
    def __init__(self):
        self.board=p.BOARD(); self.board.GetDesignSettings().SetCopperLayerCount(4)
        ds=self.board.GetDesignSettings();nc=ds.m_NetSettings.GetDefaultNetclass()
        nc.SetClearance(mm(.15));nc.SetTrackWidth(mm(.2));nc.SetViaDiameter(mm(.6));nc.SetViaDrill(mm(.3))
        ds.m_MinTrackWidth=mm(.15);ds.m_CopperEdgeClearance=mm(.3)
        self.board.SetLayerType(p.In1_Cu,p.LT_POWER)
        self.board.SetLayerType(p.In2_Cu,p.LT_POWER)
        self.comps,self.nodes=read_netlist(); self.fps={}; self.nets={}
        for name in self.nodes:
            n=p.NETINFO_ITEM(self.board,name); self.board.Add(n); self.nets[name.lstrip('/')]=n
        edge=p.PCB_SHAPE(self.board);edge.SetShape(p.SHAPE_T_RECT)
        edge.SetStart(vec((0,0)));edge.SetEnd(vec((BOARD_W,BOARD_H)));edge.SetLayer(p.Edge_Cuts)
        self.board.Add(edge)

    def place(self,ref,x,y,angle=0,fp_id=None,value=None):
        c=self.comps.get(ref,{})
        fp_id=fp_id or c['footprint']; lib,name=fp_id.split(':')
        fp=p.FootprintLoad(str(FOOTPRINTS/(lib+'.pretty')),name)
        if fp is None: raise RuntimeError(fp_id)
        fp.SetFPID(p.LIB_ID(lib,name))
        fp.SetReference(ref);fp.SetValue(value or c.get('value','M3'))
        fp.SetOrientationDegrees(angle)
        pads=[q for q in fp.Pads() if q.GetNumber()]
        xs=[q.GetPosition().x for q in pads];ys=[q.GetPosition().y for q in pads]
        fp.SetPosition(p.VECTOR2I(int(mm(x)-(min(xs)+max(xs))/2),int(mm(y)-(min(ys)+max(ys))/2)))
        if c:
            fp.SetAttributes(fp.GetAttributes() & ~p.FP_EXCLUDE_FROM_BOM)
            path=p.KIID_PATH()
            from sch_build import u5
            for k in [u5('root'),c['uuid']]: path.push_back(p.KIID(k))
            fp.SetPath(path)
            if c['dnp']: fp.SetAttributes(fp.GetAttributes()|p.FP_DNP)
        else:
            fp.SetAttributes(fp.GetAttributes()|p.FP_BOARD_ONLY|p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES)
        fp.Value().SetVisible(False)
        fp.Reference().SetTextSize(vec((0.8,0.8)));fp.Reference().SetTextThickness(mm(0.12))
        self.board.Add(fp);self.fps[ref]=fp
        return fp

    def assign_nets(self):
        for name,nodes in self.nodes.items():
            for ref,pin in nodes:
                aliases=['SH','S1','S2'] if ref=='J3' and pin=='SH' else [pin]
                pads=[q for q in self.fps[ref].Pads() if q.GetNumber() in aliases]
                if not pads: raise RuntimeError(f'Missing pad {ref}.{pin}')
                for q in pads: q.SetNet(self.nets[name.lstrip('/')])
        for ref,fp in self.fps.items():
            if ref.startswith('H'):
                for q in fp.Pads(): q.SetNet(self.nets['GND'])

    def pad(self,ref,pin='1'):
        q=self.fps[ref].FindPadByNumber(pin)
        if q is None: raise ValueError((ref,pin))
        return q

    def at(self,ref,pin='1'):
        return xy(self.pad(ref,pin).GetPosition())

    def track(self,net,points,width=0.2,layer=p.F_Cu,locked=True):
        n=self.nets[net]
        for a,b in zip(points,points[1:]):
            if math.dist(a,b)<0.000001: continue
            t=p.PCB_TRACK(self.board);t.SetStart(vec(a));t.SetEnd(vec(b));t.SetWidth(mm(width))
            t.SetLayer(layer);t.SetNet(n);t.SetLocked(locked);self.board.Add(t)

    def connect(self,ref1,pin1,ref2,pin2,width=0.2,via_points=(),layer=p.F_Cu,allow_back=False):
        q=self.pad(ref1,pin1);r=self.pad(ref2,pin2)
        assert q.GetNetCode()==r.GetNetCode(), (ref1,pin1,ref2,pin2)
        net=q.GetNetname().lstrip('/')
        points=[self.at(ref1,pin1),*via_points,self.at(ref2,pin2)]
        if not all(self.free(p.SHAPE_SEGMENT(vec(a),vec(b),mm(width)),net,(layer,)) for a,b in zip(points,points[1:])):
            from local_router import route
            for margin in [3,6,10]:
                points=route(self.board,q.GetNetCode(),self.at(ref1,pin1),self.at(ref2,pin2),width,layer,margin)
                if points is not None:break
            if points is None and allow_back:
                va=self.fanout(ref1,pin1)[0];vb=self.fanout(ref2,pin2)[0]
                points=route(self.board,q.GetNetCode(),va,vb,width,p.B_Cu,10)
                layer=p.B_Cu
            if points is None: raise RuntimeError(f'Local route blocked: {ref1}.{pin1} -> {ref2}.{pin2}, {net}')
        self.track(net,points,width,layer)

    def via(self,net,point):
        v=p.PCB_VIA(self.board);v.SetPosition(vec(point));v.SetViaType(p.VIATYPE_THROUGH)
        v.SetWidth(mm(VIA_DIAMETER));v.SetDrill(mm(VIA_DRILL));v.SetLayerPair(p.F_Cu,p.B_Cu)
        v.SetNet(self.nets[net]);v.SetLocked(True);self.board.Add(v)
        return v

    def free(self,shape,net,layers=(p.F_Cu,p.In1_Cu,p.In2_Cu,p.B_Cu),clearance=0.16):
        code=self.nets[net].GetNetCode()
        for fp in self.board.GetFootprints():
            for q in fp.Pads():
                if q.GetNetCode()==code: continue
                for layer in layers:
                    if q.IsOnLayer(layer) and q.GetEffectiveShape(layer).Collide(shape,mm(clearance)):
                        return False
        for t in self.board.GetTracks():
            if t.GetNetCode()==code: continue
            for layer in layers:
                if t.IsOnLayer(layer) and t.GetEffectiveShape(layer).Collide(shape,mm(clearance)):
                    return False
        return True

    def fanout(self,ref,pin='1',count=1):
        q=self.pad(ref,pin);pos=self.at(ref,pin);net=q.GetNetname().lstrip('/')
        if q.GetAttribute()!=p.PAD_ATTRIB_SMD: return []
        result=[]
        for radius in (0.55,0.75,0.95,1.2,1.5,1.8,2.1):
            for angle in range(0,360,30):
                a=math.radians(angle);pt=(pos[0]+radius*math.cos(a),pos[1]+radius*math.sin(a))
                if not (.65<pt[0]<BOARD_W-.65 and .65<pt[1]<BOARD_H-.65): continue
                if any(math.dist(pt,x)<.8 for x in result):continue
                sh=p.SHAPE_CIRCLE(vec(pt),mm(VIA_DIAMETER/2))
                seg=p.SHAPE_SEGMENT(vec(pos),vec(pt),mm(.2))
                if self.free(sh,net) and self.free(seg,net,(p.F_Cu,)):
                    self.track(net,[pos,pt],.2);self.via(net,pt);result.append(pt)
                    if len(result)==count:return result
        self.save()
        raise RuntimeError(f'Cannot place {count} plane vias for {ref}.{pin} ({net})')

    def zone(self,layer,net):
        z=p.ZONE(self.board);z.SetLayer(layer);z.SetNet(self.nets[net])
        poly=z.Outline();poly.NewOutline()
        for pt in [(0,0),(BOARD_W,0),(BOARD_W,BOARD_H),(0,BOARD_H)]:poly.Append(vec(pt))
        z.SetLocalClearance(mm(.2));z.SetMinThickness(mm(.15));z.SetPadConnection(p.ZONE_CONNECTION_FULL)
        self.board.Add(z)
        return z

    def save(self):
        OUT.mkdir(parents=True,exist_ok=True)
        pro=PCB.with_suffix('.kicad_pro')
        previous=pro.read_bytes() if pro.exists() else None
        p.SaveBoard(str(PCB),self.board)
        # SaveBoard serializes its in-memory default project too. Preserve the
        # explicitly configured JSON rules instead of silently restoring defaults.
        if previous is not None:pro.write_bytes(previous)
