"""Place transparent Latin point labels clear of supplied line segments.

Coordinates are diagram units; scale_cm is their printed cm/unit. Font boxes are
conservative estimates, so inspect the final PDF. Supply arc samples as segments.
No masking or third-party geometry package is used. If local placement fails,
raise instead of silently drawing a colliding label.
"""
import math
import re

PT_PER_CM = 72.27 / 2.54
DIRECTIONS = ((1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1), (0,-1), (1,-1))


def segment_hits_box(a, b, box, margin=0):
    """Liang-Barsky intersection with a padded text rectangle (including touch)."""
    x0, y0, x1, y1 = box
    x0 -= margin; y0 -= margin; x1 += margin; y1 += margin
    dx, dy = b[0]-a[0], b[1]-a[1]
    lo, hi = 0.0, 1.0
    for p, q in ((-dx,a[0]-x0), (dx,x1-a[0]), (-dy,a[1]-y0), (dy,y1-a[1])):
        if abs(p) < 1e-12:
            if q < 0:
                return False
        else:
            r = q/p
            if p < 0:
                lo = max(lo,r)
            else:
                hi = min(hi,r)
            if lo > hi:
                return False
    return True


def boxes_overlap(a, b, margin=0):
    return not (a[2]+margin < b[0] or b[2]+margin < a[0]
                or a[3]+margin < b[1] or b[3]+margin < a[1])


def place_labels(points, segments, scale_cm=1, font_pt=12, gap_pt=1.5, obstacles=()):
    """Return label centers and boxes; obstacles are extra boxes in printed points.

    segments contains endpoint names or pairs of numeric coordinate tuples.
    Label crowded/intersection points first, then place other labels around them.
    """
    if scale_cm <= 0 or font_pt <= 0:
        raise ValueError('scale_cm and font_pt must be positive')
    if not points:
        return {}
    if any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9]*', name) for name in points):
        raise ValueError('point label names must be simple Latin identifiers')
    unit = scale_cm*PT_PER_CM
    printed = {k:(v[0]*unit,v[1]*unit) for k,v in points.items()}
    def endpoint(p):
        return printed[p] if isinstance(p,str) else (p[0]*unit,p[1]*unit)
    lines = [(endpoint(a),endpoint(b)) for a,b in segments]
    cx = sum(p[0] for p in printed.values())/len(printed)
    cy = sum(p[1] for p in printed.values())/len(printed)
    # A point may lie inside a segment, as O and H do in the example.
    def degree(name):
        x,y = printed[name]
        return sum(segment_hits_box(a,b,(x-.02,y-.02,x+.02,y+.02)) for a,b in lines)
    ordered = sorted(points, key=lambda name:(-degree(name),name))
    occupied = list(obstacles)
    placed = {}
    for name in ordered:
        px,py = printed[name]
        hw = font_pt*.40*len(name)  # conservative italic-cap width
        hh = font_pt*.425
        vx,vy = px-cx,py-cy
        length = math.hypot(vx,vy) or 1
        vx,vy = vx/length,vy/length
        candidates=[]
        for dx,dy in DIRECTIONS:
            for gap in (2,4,6,8,12,16,24):
                for tangent in (-4,0,4):
                    ox = dx*(hw+gap) - dy*tangent
                    oy = dy*(hh+gap) + dx*tangent
                    box=(px+ox-hw,py+oy-hh,px+ox+hw,py+oy+hh)
                    if any(segment_hits_box(a,b,box,gap_pt) for a,b in lines):
                        continue
                    if any(boxes_overlap(box,other,gap_pt) for other in occupied):
                        continue
                    distance=math.hypot(ox,oy)
                    outward=(ox*vx+oy*vy)/(distance or 1)
                    candidates.append((distance+3*(1-outward),px+ox,py+oy,box))
        if not candidates:
            raise ValueError(f'No clear local label position for {name}; enlarge/reframe the diagram')
        _,x,y,box=min(candidates)
        occupied.append(box)
        placed[name]={'center':(x/unit,y/unit), 'box_pt':box}
    return placed


def tikz_labels(points, segments, scale_cm=1, font_pt=12, **kwargs):
    """Emit ordinary TikZ nodes; labels remain visible to source-based checkers."""
    placed=place_labels(points,segments,scale_cm,font_pt,**kwargs)
    lines=[]
    for name in points:
        x,y=placed[name]['center']
        lines.append(f'\\node[anchor=center,fill=none,inner sep=0pt,outer sep=0pt] at ({x:.6f},{y:.6f}) {{$'+name+'$};')
    return '\n'.join(lines)+'\n'
