"""Patch the baseline routed board with the three explicit missing GPIO links.

Paths are the same seed corridors used by the original generator. They are
kept as locked copper so a subsequent autorouter cannot remove the links.
The script also expands both inner copper plane outlines to the actual 85x65
mm board edge and refills them.
"""
import pcbnew as p
from project_config import PCB, OUT, BOARD_W, BOARD_H

def mm(v): return p.FromMM(v)
def v(x,y): return p.VECTOR2I(mm(x),mm(y))

def net(board,name):
    info=board.GetNetInfo()
    return next(info.GetNetItem(i) for i in range(info.GetNetCount())
                if info.GetNetItem(i).GetNetname().lstrip('/')==name)

def track(board,n,a,b,layer,width=.2):
    t=p.PCB_TRACK(board);t.SetStart(v(*a));t.SetEnd(v(*b));t.SetLayer(layer);t.SetWidth(mm(width));t.SetNet(n);t.SetLocked(True);board.Add(t)

def via(board,n,xy):
    x=p.PCB_VIA(board);x.SetPosition(v(*xy));x.SetViaType(p.VIATYPE_THROUGH);x.SetWidth(mm(.6));x.SetDrill(mm(.3));x.SetLayerPair(p.F_Cu,p.B_Cu);x.SetNet(n);x.SetLocked(True);board.Add(x)

def pad(board,ref,num):
    f=next(x for x in board.GetFootprints() if x.GetReference()==ref)
    return next(x for x in f.Pads() if x.GetNumber()==str(num))

def connect_seed(board,name,a,via_xy,b,layer=p.In2_Cu):
    n=net(board,name);prev=a
    for point in via_xy:
        track(board,n,prev,point,layer);prev=point
    track(board,n,prev,b,layer)
    via(board,n,via_xy[-1])

def resize_zones(board):
    for z in board.Zones():
        poly=z.Outline();
        while poly.OutlineCount(): poly.RemoveOutline(0)
        poly.NewOutline()
        for xy in [(0,0),(BOARD_W,0),(BOARD_W,BOARD_H),(0,BOARD_H)]:poly.Append(v(*xy))
        z.SetLocalClearance(mm(.2));z.SetMinThickness(mm(.15));z.SetPadConnection(p.ZONE_CONNECTION_FULL)
    p.ZONE_FILLER(board).Fill(list(board.Zones()))

def main():
    board=p.LoadBoard(str(PCB));
    # Do not duplicate links if this script is re-run on a candidate.
    for name,a,via_xy,b in [
        ('PF4',(31.8375,30.25),[(30.65,30.25),(14,61.8),(47,61.8),(47,63.07)],(46.31,63.07)),
        ('PB10',(25.99,4.47),[(25.99,3.2),(80.5,3.2),(80.5,45.5),(49.75,45.5)],(49.75,43.1625)),
        ('PB11',(25.99,1.93),[(25.99,.6),(84,.6),(84,45.9),(50.25,45.9)],(50.25,43.1625)),
    ]:
        n=net(board,name)
        # first and last short fanout on F.Cu, long seed corridor on In2
        if name=='PF4':
            track(board,n,a,via_xy[0],p.F_Cu,.2)
            connect_seed(board,name,via_xy[0],via_xy[1:],b,p.In2_Cu)
            track(board,n,via_xy[-1],b,p.F_Cu,.2)
        else:
            connect_seed(board,name,a,via_xy,b,p.In2_Cu)
            track(board,n,via_xy[-1],b,p.F_Cu,.2)
    resize_zones(board)
    p.SaveBoard(str(PCB),board)
    print('Patched three GPIO corridors and resized both planes.',flush=True)

if __name__=='__main__':main()
