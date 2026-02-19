import pygame
import osmnx as ox
import networkx as nx
import math
import sys
import threading
import time
import random
from geopy.geocoders import Nominatim

# ── CONFIG ───────────────────────────────────────────────────────────────────
BASE_PLACE    = "Awka, Nigeria"
SCREEN_W      = 1280
SCREEN_H      = 720
TARGET_FPS    = 60
SIM_SPEED_KMH = 50.0
SIM_SPEED_MPS = SIM_SPEED_KMH / 3.6
AWKA_LAT      = 6.2107

# ── COLOURS ──────────────────────────────────────────────────────────────────
C_BG        = (15,  20,  30)
C_ROAD      = (50,  55,  68)
C_ROAD_LINE = (90,  95, 110)
C_ROUTE     = (255, 200,   0)
C_CAR_BODY  = (220,  50,  50)
C_CAR_ROOF  = (170,  25,  25)
C_WHEEL     = (20,   20,  20)
C_TEXT      = (230, 230, 230)
C_ACCENT    = (255, 200,   0)
C_GREEN     = (60,  220, 120)
C_RED       = (220,  60,  60)
C_BLUE      = (80,  160, 255)

# ── STATE ────────────────────────────────────────────────────────────────────
state = {
    "graph":        None,
    "nodes":        [],
    "route":        [],
    "route_px":     [],
    "total_m":      0.0,
    "remaining_m":  0.0,
    "elapsed":      0.0,
    "car_x":        0.0,
    "car_y":        0.0,
    "car_angle":    0.0,
    "step":         0,
    "moving":       False,
    "loading":      True,
    "load_error":   False,
    "status":       "Starting up…",
    "dest_name":    "",
    "input_active": False,
    "input_text":   "",
    "origin_x":     0.0,
    "origin_y":     0.0,
    "scale":        1.0,
    "cam_x":        0.0,
    "cam_y":        0.0,
    "road_surf":    None,
    "road_off_x":   0,
    "road_off_y":   0,
}

# ── PYGAME INIT ───────────────────────────────────────────────────────────────
pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Awka Navigator")
clock  = pygame.time.Clock()

try:
    font_big   = pygame.font.SysFont("segoeui", 38, bold=True)
    font_med   = pygame.font.SysFont("segoeui", 22)
    font_small = pygame.font.SysFont("segoeui", 16)
    font_mono  = pygame.font.SysFont("couriernew", 20, bold=True)
except Exception:
    font_big   = pygame.font.SysFont(None, 38, bold=True)
    font_med   = pygame.font.SysFont(None, 22)
    font_small = pygame.font.SysFont(None, 16)
    font_mono  = pygame.font.SysFont(None, 20, bold=True)

# ── PROJECTION ────────────────────────────────────────────────────────────────
def lon_lat_to_px(lon, lat):
    s = state
    return (lon - s["origin_x"]) * s["scale"], (s["origin_y"] - lat) * s["scale"]

def world_to_screen(wx, wy):
    return wx - state["cam_x"] + SCREEN_W // 2, wy - state["cam_y"] + SCREEN_H // 2

def px_to_latlon(px, py):
    s = state
    return s["origin_y"] - py / s["scale"], px / s["scale"] + s["origin_x"]

def node_px(n):
    d = state["graph"].nodes[n]
    return lon_lat_to_px(d["x"], d["y"])

# ── MAP LOAD THREAD ───────────────────────────────────────────────────────────
def build_road_surface():
    s = state
    g = s["graph"]
    nodes = s["nodes"]
    all_px = [lon_lat_to_px(g.nodes[n]["x"], g.nodes[n]["y"]) for n in nodes]
    xs = [p[0] for p in all_px]
    ys = [p[1] for p in all_px]
    pad = 120
    off_x = int(min(xs)) - pad
    off_y = int(min(ys)) - pad
    W = int(max(xs)) - off_x + pad
    H = int(max(ys)) - off_y + pad
    surf = pygame.Surface((W, H))
    surf.fill(C_BG)
    hw_width = {"motorway":9,"trunk":8,"primary":7,"secondary":6,
                "tertiary":4,"residential":3,"unclassified":3}
    for u, v, data in g.edges(data=True):
        ux, uy = lon_lat_to_px(g.nodes[u]["x"], g.nodes[u]["y"])
        vx, vy = lon_lat_to_px(g.nodes[v]["x"], g.nodes[v]["y"])
        ux -= off_x; uy -= off_y
        vx -= off_x; vy -= off_y
        hw = data.get("highway", "residential")
        if isinstance(hw, list): hw = hw[0]
        w = hw_width.get(hw, 2)
        pygame.draw.line(surf, C_ROAD,      (int(ux),int(uy)), (int(vx),int(vy)), w+4)
        pygame.draw.line(surf, C_ROAD_LINE, (int(ux),int(uy)), (int(vx),int(vy)), max(1,w-2))
    s["road_surf"]  = surf
    s["road_off_x"] = off_x
    s["road_off_y"] = off_y

def load_map_thread():
    s = state
    try:
        s["status"] = "Geocoding base place…"
        geo = Nominatim(user_agent="awka-navigator")
        res = geo.geocode(BASE_PLACE, exactly_one=True, timeout=15)
        if not res:
            raise RuntimeError(f"Nominatim did not find '{BASE_PLACE}'")
        center_lat, center_lon = res.latitude, res.longitude

        s["status"] = "Downloading road network around base place…"
        import osmnx as ox
        # use a radius around the geocoded point instead of graph_from_place
        g = ox.graph_from_point((center_lat, center_lon), dist=12000, network_type="drive", simplify=True)

        if g is None or len(g) == 0:
            raise RuntimeError("osmnx returned an empty graph")

        nodes = list(g.nodes)
        xs = [g.nodes[n]["x"] for n in nodes]
        ys = [g.nodes[n]["y"] for n in nodes]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span = max(max_x - min_x, max_y - min_y)
        if span <= 0:
            raise RuntimeError("Invalid node bounding box")

        s["scale"]    = 3000.0 / span
        s["origin_x"] = min_x
        s["origin_y"] = max_y
        s["graph"]    = g
        s["nodes"]    = nodes

        build_road_surface()
        s["status"]     = "Map loaded."
        s["loading"]    = False
        s["load_error"] = False
    except Exception as e:
        s["status"]     = f"Map load failed: {e}"
        s["loading"]    = False
        s["load_error"] = True

threading.Thread(target=load_map_thread, daemon=True).start()

# ── ROUTING ───────────────────────────────────────────────────────────────────
def haversine_m(lat1, lon1, lat2, lon2):
    # returns metres between two lat/lon points
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def nearest_node(lat, lon):
    s = state
    if not s["graph"] or not s["nodes"]:
        return None
    best = None
    best_d = float("inf")
    for n in s["nodes"]:
        nd = s["graph"].nodes[n]
        d = haversine_m(lat, lon, nd["y"], nd["x"])
        if d < best_d:
            best_d = d
            best = n
    return best

def geocode(name):
    try:
        geo = Nominatim(user_agent="awka-navigator")
        res = geo.geocode(name, exactly_one=True, timeout=10)
        if not res:
            return None
        return res.latitude, res.longitude
    except Exception:
        return None

def do_routing(dest_lat, dest_lon):
    s = state
    g = s["graph"]
    try:
        start_lat, start_lon = px_to_latlon(s["car_x"], s["car_y"])
        start_n = nearest_node(start_lat, start_lon)
        end_n   = nearest_node(dest_lat, dest_lon)
        if start_n == end_n:
            s["status"] = "Already at destination!"; return
        r = nx.shortest_path(g, start_n, end_n, weight="length")
        dist = sum(
            haversine_m(g.nodes[r[i]]["y"], g.nodes[r[i]]["x"],
                        g.nodes[r[i+1]]["y"], g.nodes[r[i+1]]["x"])
            for i in range(len(r)-1))
        s["route"]       = r
        s["route_px"]    = [lon_lat_to_px(g.nodes[n]["x"], g.nodes[n]["y"]) for n in r]
        s["total_m"]     = dist
        s["remaining_m"] = dist
        s["elapsed"]     = 0.0
        s["step"]        = 0
        s["moving"]      = True
        s["status"]      = f"Navigating to {s['dest_name']} — {dist/1000:.2f} km"
    except nx.NetworkXNoPath:
        s["status"] = "No road path found to that place."
    except Exception as e:
        s["status"] = f"Route error: {e}"

def start_routing_thread(name):
    s = state
    s["dest_name"] = name
    s["status"]    = f"Looking up '{name}'…"
    def _run():
        for _ in range(120):
            if s["graph"] is not None: break
            time.sleep(0.5)
        if s["graph"] is None:
            s["status"] = "Map not ready. Please wait and try again."; return
        result = geocode(name)
        if result is None:
            s["status"] = f"Cannot find '{name}'. Try adding ', Awka' to the name."; return
        do_routing(*result)
    threading.Thread(target=_run, daemon=True).start()

# ── CAR DRAWING ───────────────────────────────────────────────────────────────
def draw_car(surf, cx, cy, angle_deg):
    W, H = 20, 36
    ar = math.radians(-angle_deg)
    def rot(dx, dy):
        return (cx + dx*math.cos(ar) - dy*math.sin(ar),
                cy + dx*math.sin(ar) + dy*math.cos(ar))

    sh = pygame.Surface((W+8, H+8), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0,0,0,70), (4,4,W,H), border_radius=5)
    sh_r = pygame.transform.rotate(sh, angle_deg)
    surf.blit(sh_r, sh_r.get_rect(center=(int(cx+3), int(cy+3))))

    body = [rot(-W//2,-H//2), rot(W//2,-H//2), rot(W//2,H//2), rot(-W//2,H//2)]
    pygame.draw.polygon(surf, C_CAR_BODY, [(int(x),int(y)) for x,y in body])
    pygame.draw.polygon(surf, (255,90,90), [(int(x),int(y)) for x,y in body], 2)

    rW, rH = W-6, H//2+2
    roof = [rot(-rW//2,-rH//2), rot(rW//2,-rH//2), rot(rW//2,rH//2), rot(-rW//2,rH//2)]
    pygame.draw.polygon(surf, C_CAR_ROOF, [(int(x),int(y)) for x,y in roof])

    wW = W-8
    ws = [rot(-wW//2,-H//2+2), rot(wW//2,-H//2+2), rot(wW//2,-H//2+8), rot(-wW//2,-H//2+8)]
    pygame.draw.polygon(surf, (160,215,255), [(int(x),int(y)) for x,y in ws])

    for ddx in (-W//2+3, W//2-3):
        lx, ly = rot(ddx, -H//2+2)
        pygame.draw.circle(surf, (255,255,190), (int(lx),int(ly)), 3)
    for ddx in (-W//2+3, W//2-3):
        lx, ly = rot(ddx, H//2-3)
        pygame.draw.circle(surf, (200,20,20), (int(lx),int(ly)), 3)
    for ddx in (-W//2+1, W//2-1):
        for ddy in (-H//2+5, H//2-5):
            wx, wy = rot(ddx, ddy)
            pygame.draw.rect(surf, C_WHEEL, pygame.Rect(int(wx)-3, int(wy)-4, 6, 8))

# ── HUD ───────────────────────────────────────────────────────────────────────
def draw_hud():
    s = state
    pw, ph = 300, 175
    panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
    panel.fill((8,12,22,215))
    pygame.draw.rect(panel, C_ACCENT, (0,0,pw,ph), 2, border_radius=10)
    screen.blit(panel, (18, SCREEN_H-ph-18))
    bx = 28; by = SCREEN_H-ph-8

    spd = font_big.render(f"{int(SIM_SPEED_KMH)}", True, C_ACCENT)
    screen.blit(spd, (bx, by))
    screen.blit(font_small.render("km/h", True, C_TEXT), (bx+spd.get_width()+5, by+16))

    if s["total_m"] > 0:
        screen.blit(font_small.render("DISTANCE REMAINING", True, (140,140,155)), (bx, by+48))
        screen.blit(font_med.render(f"{s['remaining_m']/1000:.2f} km", True, C_GREEN), (bx, by+64))
        if s["moving"] and s["remaining_m"] > 0:
            eta = s["remaining_m"] / SIM_SPEED_MPS
            screen.blit(font_small.render("ETA", True, (140,140,155)), (bx, by+94))
            screen.blit(font_med.render(f"{int(eta//60)}m {int(eta%60):02d}s", True, C_BLUE), (bx, by+110))
        prog = max(0.0, 1.0 - s["remaining_m"]/s["total_m"])
        bar_w = pw - 22
        pygame.draw.rect(screen, (45,50,65), (bx, by+148, bar_w, 10), border_radius=5)
        if prog > 0:
            pygame.draw.rect(screen, C_ACCENT, (bx, by+148, int(bar_w*prog), 10), border_radius=5)
    if s["dest_name"]:
        screen.blit(font_small.render(f"▶  {s['dest_name'][:32]}", True, C_TEXT), (bx, by+165-ph+8))

    if s["elapsed"] > 0:
        em, es = int(s["elapsed"]//60), int(s["elapsed"]%60)
        et = font_mono.render(f"  {em:02d}:{es:02d}", True, C_ACCENT)
        screen.blit(et, (SCREEN_W-et.get_width()-24, 18))

    st = font_small.render(s["status"], True, C_TEXT)
    sx = SCREEN_W//2 - st.get_width()//2
    pygame.draw.rect(screen, (8,12,22,210), (sx-12, 10, st.get_width()+24, 28), border_radius=7)
    screen.blit(st, (sx, 14))

def draw_input():
    s = state
    bw, bh = 520, 44
    bx = SCREEN_W//2 - bw//2
    by = SCREEN_H - 68
    pygame.draw.rect(screen, (18,22,38), (bx, by, bw, bh), border_radius=8)
    border = C_ACCENT if s["input_active"] else (75,75,100)
    pygame.draw.rect(screen, border, (bx, by, bw, bh), 2, border_radius=8)
    screen.blit(font_small.render("DESTINATION:", True, (140,140,155)), (bx+10, by-20))
    cursor = "|" if s["input_active"] else ""
    screen.blit(font_med.render(s["input_text"]+cursor, True, C_TEXT), (bx+12, by+10))
    hint = font_small.render("T = type destination   Enter = go   Esc = quit", True, (90,90,115))
    screen.blit(hint, (SCREEN_W//2-hint.get_width()//2, by+bh+5))

def draw_loading():
    s = state
    overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    overlay.fill((8,12,22,230))
    screen.blit(overlay, (0,0))
    title = font_big.render("AWKA NAVIGATOR", True, C_ACCENT)
    screen.blit(title, (SCREEN_W//2-title.get_width()//2, SCREEN_H//2-70))
    msg = font_med.render(s["status"], True, C_TEXT)
    screen.blit(msg, (SCREEN_W//2-msg.get_width()//2, SCREEN_H//2))
    dots = "." * (int(time.time()*2) % 4)
    sub = font_small.render(f"Please wait{dots}", True, (120,120,140))
    screen.blit(sub, (SCREEN_W//2-sub.get_width()//2, SCREEN_H//2+44))
    if s["load_error"]:
        err = font_small.render("Check internet connection and restart.", True, C_RED)
        screen.blit(err, (SCREEN_W//2-err.get_width()//2, SCREEN_H//2+80))

# ── MAIN LOOP ─────────────────────────────────────────────────────────────────
def main():
    s = state
    last = time.time()

    while True:
        dt = min(time.time()-last, 0.1)   # cap dt to avoid huge jumps
        last = time.time()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.KEYDOWN:
                if s["input_active"]:
                    if event.key == pygame.K_RETURN:
                        txt = s["input_text"].strip()
                        if txt: start_routing_thread(txt)
                        s["input_active"] = False; s["input_text"] = ""
                    elif event.key == pygame.K_ESCAPE:
                        s["input_active"] = False; s["input_text"] = ""
                    elif event.key == pygame.K_BACKSPACE:
                        s["input_text"] = s["input_text"][:-1]
                    else:
                        if len(s["input_text"]) < 60:
                            s["input_text"] += event.unicode
                else:
                    if event.key == pygame.K_t and not s["loading"]:
                        s["input_active"] = True
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit(); sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                # coordinates of the destination input box (adjust if your layout differs)
                box_w, box_h = 500, 44
                bx = SCREEN_W//2 - box_w//2
                by = SCREEN_H - 70
                if bx <= mx <= bx + box_w and by <= my <= by + box_h:
                    state["input_active"] = True
                else:
                    state["input_active"] = False

        # Move car
        if s["moving"] and s["route"] and s["step"] < len(s["route"])-1:
            s["elapsed"] += dt
            next_n = s["route"][s["step"]+1]
            tx, ty = s["route_px"][s["step"]+1]
            dx, dy = tx-s["car_x"], ty-s["car_y"]
            dist_px = math.hypot(dx, dy)
            deg_per_sec  = SIM_SPEED_MPS / (111_320 * math.cos(math.radians(AWKA_LAT)))
            speed_px_s   = deg_per_sec * s["scale"]
            move_px      = speed_px_s * dt
            if dist_px > 0:
                s["car_angle"] = math.degrees(math.atan2(-dy, dx)) - 90
            if move_px >= dist_px:
                s["car_x"], s["car_y"] = tx, ty
                cur_n = s["route"][s["step"]]
                g = s["graph"]
                seg = haversine_m(g.nodes[cur_n]["y"], g.nodes[cur_n]["x"],
                                  g.nodes[next_n]["y"], g.nodes[next_n]["x"])
                s["remaining_m"] = max(0.0, s["remaining_m"]-seg)
                s["step"] += 1
            else:
                s["car_x"] += (dx/dist_px)*move_px
                s["car_y"] += (dy/dist_px)*move_px
        elif s["moving"] and s["step"] >= len(s["route"])-1:
            s["moving"] = False; s["remaining_m"] = 0.0
            s["status"] = f"Arrived at {s['dest_name']}!"

        s["cam_x"] = s["car_x"]; s["cam_y"] = s["car_y"]

        # Draw
        screen.fill(C_BG)

        if s["road_surf"] is not None:
            sx, sy = world_to_screen(s["road_off_x"], s["road_off_y"])
            screen.blit(s["road_surf"], (int(sx), int(sy)))

        if len(s["route_px"]) >= 2:
            pts = [world_to_screen(*p) for p in s["route_px"]]
            pygame.draw.lines(screen, (160,120,0), False, [(int(x),int(y)) for x,y in pts], 6)
            rem = pts[s["step"]:]
            if len(rem) >= 2:
                pygame.draw.lines(screen, C_ROUTE, False, [(int(x),int(y)) for x,y in rem], 4)

        if s["route"]:
            dx2, dy2 = world_to_screen(*s["route_px"][-1])
            pygame.draw.circle(screen, C_RED, (int(dx2),int(dy2)), 11)
            pygame.draw.circle(screen, (255,255,255), (int(dx2),int(dy2)), 11, 2)
            lbl = font_small.render("DEST", True, C_TEXT)
            screen.blit(lbl, (int(dx2)+14, int(dy2)-8))

        # Car always drawn at screen centre (camera follows car)
        draw_car(screen, SCREEN_W//2, SCREEN_H//2, s["car_angle"])

        draw_hud()
        draw_input()
        if s["loading"]: draw_loading()

        pygame.display.flip()
        clock.tick(TARGET_FPS)

if __name__ == "__main__":
    main()
