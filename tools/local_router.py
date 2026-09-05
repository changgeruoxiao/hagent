"""Short front-layer connections with conservative geometric A* clearance.

Raster search proposes a route; KiCad DRC is the independent acceptance test.
There are no anchor exemptions and no deletion of another net's copper.
"""
import heapq
import math
import numpy as np
import pcbnew as p


COPPER_LAYERS = (p.F_Cu, p.In1_Cu, p.In2_Cu, p.B_Cu)


def exact_clear(board, points, netcode, layer, width=0.20, clearance=0.15):
    """Exact KiCad shape check for a proposed track path.

    The raster mask is deliberately conservative, but it is still a grid
    approximation.  This second check catches rotated pads and via annular
    rings at sub-grid positions before any copper is written.
    """
    for a, b in zip(points, points[1:]):
        if math.dist(a, b) < 1e-6:
            continue
        shape = p.SHAPE_SEGMENT(
            p.VECTOR2I(p.FromMM(a[0]), p.FromMM(a[1])),
            p.VECTOR2I(p.FromMM(b[0]), p.FromMM(b[1])),
            p.FromMM(width),
        )
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetCode() == netcode or not pad.IsOnLayer(layer):
                    continue
                if pad.GetEffectiveShape(layer).Collide(shape, p.FromMM(clearance)):
                    return False
        for track in board.GetTracks():
            if track.GetNetCode() == netcode or not track.IsOnLayer(layer):
                continue
            if track.GetEffectiveShape(layer).Collide(shape, p.FromMM(clearance)):
                return False
    return True


def exact_via_clear(board, point, netcode, diameter=0.60, clearance=0.15):
    """Check a through-via against copper on every board layer."""
    shape = p.SHAPE_CIRCLE(
        p.VECTOR2I(p.FromMM(point[0]), p.FromMM(point[1])),
        p.FromMM(diameter / 2.0),
    )
    for layer in COPPER_LAYERS:
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetCode() == netcode or not pad.IsOnLayer(layer):
                    continue
                if pad.GetEffectiveShape(layer).Collide(shape, p.FromMM(clearance)):
                    return False
        for track in board.GetTracks():
            if track.GetNetCode() == netcode or not track.IsOnLayer(layer):
                continue
            if track.GetEffectiveShape(layer).Collide(shape, p.FromMM(clearance)):
                return False
    return True

def route(board, netcode, start, end, width, layer, margin=4.0, step=.10):
    lo=np.floor((np.minimum(start,end)-margin)/step)*step
    hi=np.ceil((np.maximum(start,end)+margin)/step)*step
    lo=np.maximum(lo,(.5,.5));hi=np.minimum(hi,(84.5,64.5))
    xs=np.arange(lo[0],hi[0]+step/2,step);ys=np.arange(lo[1],hi[1]+step/2,step)
    blocked=np.zeros((len(ys),len(xs)),dtype=bool)
    # +0.04 covers the sub-grid uncertainty; final exact checks remain mandatory.
    grow=.15+width/2+.04
    def mask_box(bounds,fn):
        x1,y1,x2,y2=bounds
        ix0=max(0,int(math.floor((x1-lo[0])/step)));ix1=min(len(xs),int(math.ceil((x2-lo[0])/step))+1)
        iy0=max(0,int(math.floor((y1-lo[1])/step)));iy1=min(len(ys),int(math.ceil((y2-lo[1])/step))+1)
        if ix1<=ix0 or iy1<=iy0:return
        xx=xs[None,ix0:ix1];yy=ys[iy0:iy1,None]
        blocked[iy0:iy1,ix0:ix1] |= fn(xx,yy)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode()==netcode or not pad.IsOnLayer(layer):continue
            cx,cy=pad.GetPosition().x/1e6,pad.GetPosition().y/1e6
            sx,sy=pad.GetSize().x/2e6,pad.GetSize().y/2e6
            ang=math.radians(pad.GetOrientationDegrees());co,si=math.cos(ang),math.sin(ang)
            radius=math.hypot(sx,sy)+grow
            if pad.GetShape()==p.PAD_SHAPE_CIRCLE:
                fn=lambda x,y,cx=cx,cy=cy,sx=sx:(x-cx)**2+(y-cy)**2 <= (sx+grow)**2
            else:
                fn=lambda x,y,cx=cx,cy=cy,co=co,si=si,sx=sx,sy=sy: (
                    np.maximum(np.abs((x-cx)*co-(y-cy)*si)-sx,0)**2+
                    np.maximum(np.abs((x-cx)*si+(y-cy)*co)-sy,0)**2<=grow**2)
            mask_box((cx-radius,cy-radius,cx+radius,cy+radius),fn)
    for t in board.GetTracks():
        if t.GetNetCode()==netcode or not t.IsOnLayer(layer):continue
        ax,ay=t.GetStart().x/1e6,t.GetStart().y/1e6
        bx,by=t.GetEnd().x/1e6,t.GetEnd().y/1e6
        tw=(t.GetWidth(p.F_Cu) if t.Type()==p.PCB_VIA_T else t.GetWidth())
        radius=tw/2e6+grow;dx,dy=bx-ax,by-ay;length2=dx*dx+dy*dy
        def fn(x,y,ax=ax,ay=ay,dx=dx,dy=dy,length2=length2,radius=radius):
            f=0 if length2==0 else np.clip(((x-ax)*dx+(y-ay)*dy)/length2,0,1)
            return (x-ax-f*dx)**2+(y-ay-f*dy)**2<=radius*radius
        mask_box((min(ax,bx)-radius,min(ay,by)-radius,max(ax,bx)+radius,max(ay,by)+radius),fn)
    def index(pt):return (int(round((pt[0]-lo[0])/step)),int(round((pt[1]-lo[1])/step)))
    s=index(start);target=index(end)
    if blocked[s[1],s[0]] or blocked[target[1],target[0]]:return None
    heap=[(math.dist(s,target),0,s)];dist={s:0};parents={}
    moves=[(1,0,1),(-1,0,1),(0,1,1),(0,-1,1),(1,1,math.sqrt(2)),(-1,1,math.sqrt(2)),(1,-1,math.sqrt(2)),(-1,-1,math.sqrt(2))]
    while heap:
        _,g,u=heapq.heappop(heap)
        if g>dist.get(u,math.inf)+1e-9:continue
        if u==target:
            chain=[u]
            while u!=s:u=parents[u];chain.append(u)
            chain.reverse()
            corners=[chain[0]]
            for a,b,c in zip(chain,chain[1:],chain[2:]):
                if (b[0]-a[0],b[1]-a[1])!=(c[0]-b[0],c[1]-b[1]):corners.append(b)
            corners.append(chain[-1])
            points=[(float(xs[x]),float(ys[y])) for x,y in corners]
            return [start,*points,end]
        for dx,dy,cost in moves:
            v=(u[0]+dx,u[1]+dy)
            if not (0<=v[0]<len(xs) and 0<=v[1]<len(ys)) or blocked[v[1],v[0]]:continue
            if dx and dy and (blocked[u[1],v[0]] or blocked[v[1],u[0]]):continue
            ng=g+cost
            if ng<dist.get(v,math.inf)-1e-9:
                dist[v]=ng;parents[v]=u
                heapq.heappush(heap,(ng+math.dist(v,target),ng,v))
    return None
