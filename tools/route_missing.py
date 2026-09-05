"""Route only the three baseline unrouted GPIO nets on B.Cu.

The A* proposal treats every foreign copper shape as a hard obstacle. A path
is written only after exact KiCad shape collision checks; no existing copper is
deleted and inner power planes are left unchanged.
"""
import math, pcbnew as p
from project_config import PCB
from local_router import route

def mm(x):return p.FromMM(x)
def vec(xy):return p.VECTOR2I(mm(xy[0]),mm(xy[1]))
def pad(board,ref,num):
 f=next(f for f in board.GetFootprints() if f.GetReference()==ref)
 return next(q for q in f.Pads() if q.GetNumber()==str(num))
def xy(q):return (q.GetPosition().x/1e6,q.GetPosition().y/1e6)
def add_track(b,n,a,z,layer):
 t=p.PCB_TRACK(b);t.SetStart(vec(a));t.SetEnd(vec(z));t.SetLayer(layer);t.SetWidth(mm(.2));t.SetNet(n);t.SetLocked(True);b.Add(t)
def add_via(b,n,a):
 q=p.PCB_VIA(b);q.SetPosition(vec(a));q.SetViaType(p.VIATYPE_THROUGH);q.SetWidth(mm(.6));q.SetDrill(mm(.3));q.SetLayerPair(p.F_Cu,p.B_Cu);q.SetNet(n);q.SetLocked(True);b.Add(q)
def near_points(pos):
 for r in [.75,1.0,1.25,1.5,1.8,2.2,2.6]:
  for ang in range(0,360,15):
   a=math.radians(ang);yield(pos[0]+r*math.cos(a),pos[1]+r*math.sin(a))
def main():
 b=p.LoadBoard(str(PCB));
 for name,sref,spin,eref,epin in [('PF4','U1','14','J2','31'),('PB11','U1','70','J1','16'),('PB10','U1','69','J1','15')]:
  src=pad(b,sref,spin);dst=pad(b,eref,epin);n=src.GetNet();sp=xy(src);dp=xy(dst);chosen=None
  if name=='PB10':
   direct=route(b,n.GetNetCode(),sp,dp,.2,p.F_Cu,10,.1)
   if direct is not None:
    for a,z in zip(direct,direct[1:]):add_track(b,n,a,z,p.F_Cu)
    print(name,'direct F.Cu segments',len(direct)-1,flush=True);continue
  for vp in near_points(sp):
   if not (.8<vp[0]<84.2 and .8<vp[1]<64.2):continue
   sh=p.SHAPE_CIRCLE(vec(vp),mm(.3));seg=p.SHAPE_SEGMENT(src.GetPosition(),vec(vp),mm(.2))
   if any(q.GetNetCode()!=n.GetNetCode() and q.IsOnLayer(p.F_Cu) and
          (q.GetEffectiveShape(p.F_Cu).Collide(sh,mm(.15)) or q.GetEffectiveShape(p.F_Cu).Collide(seg,mm(.15)))
          for f in b.GetFootprints() for q in f.Pads()):continue
   if any(t.GetNetCode()!=n.GetNetCode() and t.IsOnLayer(p.F_Cu) and
          (t.GetEffectiveShape(p.F_Cu).Collide(sh,mm(.15)) or t.GetEffectiveShape(p.F_Cu).Collide(seg,mm(.15))) for t in b.GetTracks()):continue
   path=route(b,n.GetNetCode(),vp,dp,.2,p.B_Cu,10,.1)
   if path is not None:
    chosen=(vp,path);break
  if chosen is None: raise RuntimeError('no route '+name)
  vp,path=chosen;add_track(b,n,sp,vp,p.F_Cu);add_via(b,n,vp)
  for a,z in zip(path,path[1:]):add_track(b,n,a,z,p.B_Cu)
  print(name,'via',vp,'segments',len(path)-1,flush=True)
 p.SaveBoard(str(PCB),b)
if __name__=='__main__':main()
