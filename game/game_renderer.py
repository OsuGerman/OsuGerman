"""High-quality gameplay renderer — layered, cached, polished."""
from __future__ import annotations
import math, random
import pygame
from .types import Lane, ObjectType, ObjectState, Judgement, JUDGEMENT_COLORS
from .entities import GameplayObject
from .gameplay_mgr import GameplayManager

R = 24
HX = 0.15
GY = 0.68
AY = 0.38

_C = {
    'bg0': (6, 2, 18), 'bg1': (12, 5, 32), 'bg2': (20, 10, 48),
    'ground': (255, 60, 130), 'ground_d': (180, 30, 80),
    'air': (0, 210, 255), 'air_d': (0, 140, 190),
    'accent': (200, 50, 240), 'gold': (255, 210, 50),
    'green': (0, 220, 110), 'red': (255, 70, 70),
    'hold': (170, 100, 255), 'obstacle': (255, 50, 50),
    'mash': (255, 170, 30), 'heavy': (255, 40, 200),
    'white': (255, 255, 255), 'text2': (180, 170, 210),
    'text3': (100, 95, 130), 'panel': (20, 10, 48),
}
WC = [(255,210,50),(255,170,40),(255,100,50),(200,50,240),(0,255,200)]


class Particle:
    __slots__=('x','y','vx','vy','life','ml','col','sz','kind')
    def __init__(s,x,y,col,sz=4,kind='dot'):
        a=random.uniform(0,math.tau); sp=random.uniform(2,6)
        s.x,s.y=x,y; s.vx=math.cos(a)*sp; s.vy=math.sin(a)*sp-2
        s.life=s.ml=random.uniform(0.25,0.5); s.col=col; s.sz=sz; s.kind=kind


class Pop:
    __slots__=('txt','col','x','y','life','sc')
    def __init__(s,t,c,x,y): s.txt,s.col,s.x,s.y=t,c,x,y; s.life=0.7; s.sc=1.6


class GameRenderer:
    def __init__(s, scr: pygame.Surface):
        s.scr=scr; s.parts: list[Particle]=[]; s.pops: list[Pop]=[]
        s.shake=0.; s.cf=0; s.ct=0.; s.ca=''; s.cat=0.; s.char_state='run'; s.char_hurt_t=0.
        s._fc: dict[tuple,pygame.font.Font]={}
        s._gc: dict[tuple,pygame.Surface]={}
        s._bgc=None; s._bgsz=(0,0); s._scroll=0.
        s._stars=[(random.random(),random.random(),random.uniform(0.8,2.5)) for _ in range(70)]
        s._stars2=[(random.random(),random.random(),random.uniform(0.5,1.5)) for _ in range(30)]

    def _f(s,sz,b=False):
        k=(sz,b)
        if k not in s._fc: s._fc[k]=pygame.font.SysFont('segoe ui,arial,sans-serif',sz,bold=b)
        return s._fc[k]

    def update(s,dt):
        s.shake*=0.82; s._scroll+=dt*50
        s.ct+=dt
        if s.ct>0.1: s.cf=(s.cf+1)%4; s.ct=0
        if s.cat>0: s.cat-=dt
        else: s.ca=''
        for p in s.parts[:]:
            p.x+=p.vx*dt*60; p.y+=p.vy*dt*60; p.vy+=0.12; p.life-=dt
            if p.life<=0: s.parts.remove(p)
        for j in s.pops[:]:
            j.life-=dt; j.y-=dt*35; j.sc*=0.97
            if j.life<=0: s.pops.remove(j)

    def spawn_particles(s,x,y,col,n=14,sz=5):
        for _ in range(n): s.parts.append(Particle(x,y,col,random.uniform(2,sz)))

    def add_popup(s,t,c,lane):
        w,h=s.scr.get_size()
        x=w*HX+70; y=(h*AY if lane==Lane.AIR else h*GY)-35
        s.pops.append(Pop(t,c,x,y))

    def trigger_hit(s,lane,j,wlv):
        w,h=s.scr.get_size()
        hx=w*HX; y=h*AY if lane==Lane.AIR else h*GY
        col=JUDGEMENT_COLORS[j]
        n=14+wlv*6
        s.spawn_particles(hx,y,col,n,5+wlv*2)
        if j==Judgement.PERFECT:
            for _ in range(6): s.parts.append(Particle(hx+random.randint(-20,20),y+random.randint(-20,20),_C['gold'],random.uniform(3,9),'spark'))
        s.add_popup(j.value+'!',col,lane)
        s.ca='air' if lane==Lane.AIR else 'gnd'; s.cat=0.18
        s.char_state='air_attack' if lane==Lane.AIR else 'ground_attack'
        s.shake=7 if j==Judgement.PERFECT else 3.5

    def trigger_miss(s, lane):
        s.char_state='hurt'; s.char_hurt_t=0.3
        s.shake=2

    def render_frame(s,gm: GameplayManager):
        w,h=s.scr.get_size()
        ox=int((random.random()-0.5)*s.shake*2)
        oy=int((random.random()-0.5)*s.shake*2)

        s._bg(w,h)
        s._parallax(w,h)

        if gm.screen_flash>0 and not getattr(gm,'_reduce_flash',False):
            fl=pygame.Surface((w,h),pygame.SRCALPHA)
            fl.fill((255,255,255,int(min(60,gm.screen_flash*70))))
            s.scr.blit(fl,(0,0))

        s._platform(w,h)
        s._lanes(w,h)
        s._receptors(w,h,gm.beat_pulse)
        s._entities(gm,w,h)
        s._character(w,h,gm.state.weapon_level)
        s._draw_parts()
        s._draw_pops()
        s._hud(w,h,gm)

        if gm.started and gm.song_time < 5000:
            s.render_tutorial(w, h, gm.song_time)

        if not gm.started: s._countdown(w,h,gm.countdown)
        if gm.paused: s._overlay(w,h,"PAUSE","ESC fortsetzen · R retry · Q beenden",(200,200,200))
        if gm.failed:
            s._overlay(w,h,"FAILED","R nochmal · ESC zurück",(255,70,70))
            if hasattr(gm,'_auto_retry') and gm._auto_retry:
                t=s._f(12).render("Auto-Retry aktiv...",True,_C['gold'])
                s.scr.blit(t,(w//2-t.get_width()//2,h//2+50))

    def render_debug(s, gm, fps):
        w,h=s.scr.get_size()
        lines = [
            f"FPS: {fps:.0f}",
            f"SongTime: {gm.song_time:.1f}ms",
            f"Active: {len(gm.active_objects)}",
            f"Spawned: {gm.spawn_mgr._spawn_cursor}/{len(gm.spawn_mgr.objects)}",
            f"HP: {gm.state.hp:.0f}  Combo: {gm.state.combo}  Score: {gm.state.score}",
            f"P:{gm.state.perfect_count} G:{gm.state.great_count} OK:{gm.state.good_count} M:{gm.state.miss_count}",
            f"Acc: {gm.state.accuracy:.1f}%  UR: {s._calc_ur(gm):.1f}",
            f"BPM: {gm._bpm}  Speed: {gm._note_speed}  Offset: {gm.audio_offset}ms",
        ]
        dp=pygame.Surface((280,len(lines)*16+8),pygame.SRCALPHA)
        dp.fill((0,0,0,180))
        s.scr.blit(dp,(w-284,50))
        for i,l in enumerate(lines):
            t=s._f(12).render(l,True,_C['green'] if i==0 else _C['text2'])
            s.scr.blit(t,(w-280,54+i*16))

    def _calc_ur(s,gm):
        if not gm.timing_records: return 0
        errs=[r.error_ms for r in gm.timing_records[-50:]]
        avg=sum(errs)/len(errs)
        var=sum((e-avg)**2 for e in errs)/len(errs)
        return (var**0.5)*10

    # ── Background ──
    def _bg(s,w,h):
        if s._bgc is None or s._bgsz!=(w,h):
            bg=pygame.Surface((w,h))
            for y in range(h):
                t=y/h
                bg.fill((int(6+t*12),int(2+t*5),int(18+t*28)),(0,y,w,1))
            s._bgc=bg; s._bgsz=(w,h)
        s.scr.blit(s._bgc,(0,0))

    def _parallax(s,w,h):
        for xr,yr,sz in s._stars2:
            sx=int((xr*w+s._scroll*0.3*sz)%w)
            sy=int(yr*h)
            pygame.draw.circle(s.scr,(20+int(sz*10),15+int(sz*8),40+int(sz*15)),(sx,sy),max(1,int(sz*1.5)))
        for xr,yr,sz in s._stars:
            sx=int((xr*w+s._scroll*(0.5+sz*0.3))%w)
            sy=int(yr*h)
            a=min(255,int(30+sz*25))
            pygame.draw.circle(s.scr,(a,a,a+10),(sx,sy),max(1,int(sz)))

    def _platform(s,w,h):
        ly=int(h*GY+R+10)
        gh=50
        gs=pygame.Surface((w,gh),pygame.SRCALPHA)
        for y in range(gh):
            a=int(35*(1-y/gh))
            pygame.draw.line(gs,(*_C['ground'],a),(0,y),(w,y))
        s.scr.blit(gs,(0,ly))
        pygame.draw.line(s.scr,_C['ground'],(0,ly),(w,ly),2)
        for i in range(w//80+1):
            lx=int((i*80-s._scroll*1.5)%w)
            ls=pygame.Surface((1,gh),pygame.SRCALPHA)
            ls.fill((255,255,255,10))
            s.scr.blit(ls,(lx,ly))

    def _lanes(s,w,h):
        for yr in (AY,GY):
            ls=pygame.Surface((w,56),pygame.SRCALPHA)
            ls.fill((255,255,255,4))
            s.scr.blit(ls,(0,int(h*yr)-28))

    def _receptors(s,w,h,pulse):
        hx=int(w*HX); sc=1+pulse*0.35; al=int(80+pulse*175)
        for yr,col in [(AY,_C['air']),(GY,_C['ground'])]:
            y=int(h*yr); r=int(R*sc)
            rs=pygame.Surface((r*4,r*4),pygame.SRCALPHA)
            pygame.draw.circle(rs,(*col,al),(r*2,r*2),r,3)
            pygame.draw.circle(rs,(*col,int(al*0.25)),(r*2,r*2),r+10,2)
            s.scr.blit(rs,(hx-r*2,y-r*2))
            if pulse>0.3:
                ps=pygame.Surface((r*6,r*6),pygame.SRCALPHA)
                pygame.draw.circle(ps,(*col,int(pulse*25)),(r*3,r*3),r*3)
                s.scr.blit(ps,(hx-r*3,y-r*3))

    # ── Entities ──
    def _entities(s,gm,w,h):
        hx=w*HX; st=gm.song_time; sp=gm.note_speed; bp=gm.beat_pulse
        for o in gm.active_objects:
            if o.resolved: continue
            x=o.get_screen_x(st,hx,sp)
            if x<-80 or x>w+80: continue
            y=h*AY if o.lane==Lane.AIR else h*GY
            pr=max(0,1-abs(o.hit_time-st)/500)
            pu=1+bp*0.1
            ix,iy=int(x),int(y)
            t=o.obj_type
            if t==ObjectType.GROUND_ENEMY: s._e_ground(ix,iy,pr,pu)
            elif t==ObjectType.AIR_ENEMY: s._e_air(ix,iy,pr,pu)
            elif t==ObjectType.HOLD_NOTE: s._e_hold(ix,iy,o,st,hx,sp)
            elif t==ObjectType.OBSTACLE: s._e_obst(ix,iy,pr,pu)
            elif t==ObjectType.MASH_CHAIN: s._e_mash(ix,iy,pr,pu)
            elif t==ObjectType.HEAVY_ACCENT: s._e_heavy(ix,iy,pr,pu)

    def _glow(s,col,radius=R*2):
        k=(col,radius)
        if k not in s._gc:
            sz=radius*2; sf=pygame.Surface((sz,sz),pygame.SRCALPHA)
            for r in range(radius,radius//4,-2):
                a=int(45*(1-r/radius))
                pygame.draw.circle(sf,(*col,a),(radius,radius),r)
            s._gc[k]=sf
        return s._gc[k]

    def _e_ground(s,x,y,pr,pu):
        r=int((R+pr*5)*pu)
        g=s._glow(_C['ground'],R*2); g.set_alpha(int(25+pr*90))
        s.scr.blit(g,(x-g.get_width()//2,y-g.get_height()//2))
        pygame.draw.circle(s.scr,_C['ground'],(x,y),r)
        pygame.draw.circle(s.scr,_C['ground_d'],(x,y),int(r*0.55))
        eo=int(r*0.22); er=max(2,int(r*0.13))
        for dx in (-eo,eo):
            pygame.draw.circle(s.scr,_C['white'],(x+dx,y-eo),er)
            pygame.draw.circle(s.scr,(20,8,35),(x+dx+1,y-eo),max(1,er-1))
        mw=int(r*0.35)
        pygame.draw.arc(s.scr,(20,8,35),(x-mw//2,y+int(r*0.05),mw,int(r*0.2)),3.14,6.28,2)
        pygame.draw.circle(s.scr,_C['white'],(x,y),r,2)

    def _e_air(s,x,y,pr,pu):
        r=int((R+pr*5)*pu)
        g=s._glow(_C['air'],R*2); g.set_alpha(int(25+pr*90))
        s.scr.blit(g,(x-g.get_width()//2,y-g.get_height()//2))
        pts=[(x,y-r),(x+r,y),(x,y+r),(x-r,y)]
        pygame.draw.polygon(s.scr,_C['air'],pts)
        ir=int(r*0.45)
        pygame.draw.polygon(s.scr,_C['air_d'],[(x,y-ir),(x+ir,y),(x,y+ir),(x-ir,y)])
        er=max(2,int(r*0.11))
        for dx in (-int(r*0.18),int(r*0.18)):
            pygame.draw.circle(s.scr,_C['white'],(x+dx,y-int(r*0.08)),er)
        wh=int(r*0.35)
        pygame.draw.polygon(s.scr,_C['air'],[(x-r,y),(x-r-wh,y-wh),(x-int(r*0.5),y-int(wh*0.5))])
        pygame.draw.polygon(s.scr,_C['air'],[(x+r,y),(x+r+wh,y-wh),(x+int(r*0.5),y-int(wh*0.5))])
        pygame.draw.polygon(s.scr,_C['white'],pts,2)

    def _e_hold(s,x,y,o,st,hx,sp):
        ex=int(hx+(o.hit_time+o.duration-st)*sp)
        bh=12; col=_C['hold']
        pygame.draw.rect(s.scr,col,(min(x,ex),int(y)-bh//2,abs(ex-x)+1,bh),border_radius=6)
        pygame.draw.circle(s.scr,col,(x,int(y)),R-3)
        pygame.draw.circle(s.scr,_C['white'],(x,int(y)),R-3,2)
        t=s._f(11,True).render("HOLD",True,_C['white'])
        s.scr.blit(t,(x-t.get_width()//2,int(y)-t.get_height()//2))

    def _e_obst(s,x,y,pr,pu):
        r=int((R+4)*pu)
        pygame.draw.polygon(s.scr,_C['obstacle'],[(x,y-r-5),(x+r+5,y),(x,y+r+5),(x-r-5,y)])
        pygame.draw.polygon(s.scr,(150,25,25),[(x,y-r),(x+r,y),(x,y+r),(x-r,y)])
        lw=3
        pygame.draw.line(s.scr,_C['white'],(x-int(r*0.3),y-int(r*0.3)),(x+int(r*0.3),y+int(r*0.3)),lw)
        pygame.draw.line(s.scr,_C['white'],(x+int(r*0.3),y-int(r*0.3)),(x-int(r*0.3),y+int(r*0.3)),lw)
        pygame.draw.polygon(s.scr,_C['white'],[(x,y-r-5),(x+r+5,y),(x,y+r+5),(x-r-5,y)],2)

    def _e_mash(s,x,y,pr,pu):
        r=int((R-3)*pu)
        for i in range(3):
            ox=int((i-1)*r*0.9)
            pygame.draw.circle(s.scr,_C['mash'],(x+ox,int(y)),r)
            pygame.draw.circle(s.scr,_C['white'],(x+ox,int(y)),r,2)
        t=s._f(10,True).render("MASH!",True,(80,40,0))
        s.scr.blit(t,(x-t.get_width()//2,int(y)-t.get_height()//2))

    def _e_heavy(s,x,y,pr,pu):
        r=int((R+8)*pu)
        g=s._glow(_C['heavy'],R*3); g.set_alpha(int(50+pr*120))
        s.scr.blit(g,(x-g.get_width()//2,int(y)-g.get_height()//2))
        pygame.draw.circle(s.scr,_C['heavy'],(x,int(y)),r)
        pygame.draw.circle(s.scr,(255,180,230),(x,int(y)),int(r*0.4))
        pygame.draw.circle(s.scr,_C['white'],(x,int(y)),r,3)
        for i in range(6):
            a=pygame.time.get_ticks()*0.004+i*math.tau/6
            sx=x+int(math.cos(a)*(r+8)); sy=int(y)+int(math.sin(a)*(r+8))
            pygame.draw.circle(s.scr,_C['gold'],(sx,sy),3)

    # ── Character with State Machine ──
    def _character(s,w,h,wlv):
        cx=int(w*HX); by=int(h*GY+R+8)
        bob=int(math.sin(s.cf*math.pi/2)*4)
        jmp=0; tilt=0; flash_col=None

        # State transitions
        if s.char_hurt_t > 0:
            s.char_hurt_t -= 0.016
            s.char_state = 'hurt'
            tilt = int(math.sin(s.char_hurt_t * 40) * 4)
            flash_col = _C['red']
        elif s.cat > 0:
            if s.ca == 'air':
                s.char_state = 'air_attack'
                jmp = int(-65 * (s.cat / 0.18))
            else:
                s.char_state = 'ground_attack'
        else:
            s.char_state = 'run'

        y = by + bob + jmp

        # Weapon aura
        if wlv > 0:
            ar = 24 + wlv * 8; ac = WC[min(wlv, len(WC)-1)]
            aura = pygame.Surface((ar*2, ar*2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (*ac, 10 + wlv * 12), (ar, ar), ar)
            s.scr.blit(aura, (cx-ar, y-38-ar))

        # Body with tilt
        bx = cx + tilt

        # Head
        head_col = flash_col or _C['ground']
        pygame.draw.ellipse(s.scr, head_col, (bx-18, y-62, 36, 40))

        # Eyes
        eye_state = 'x' if s.char_state == 'hurt' else '>' if 'attack' in s.char_state else 'o'
        for dx in (-6, 8):
            if eye_state == 'x':
                pygame.draw.line(s.scr, _C['white'], (bx+dx-3, y-50), (bx+dx+3, y-44), 2)
                pygame.draw.line(s.scr, _C['white'], (bx+dx+3, y-50), (bx+dx-3, y-44), 2)
            elif eye_state == '>':
                pygame.draw.circle(s.scr, _C['white'], (bx+dx, y-47), 5)
                pygame.draw.circle(s.scr, (15,5,30), (bx+dx+2, y-47), 3)
            else:
                pygame.draw.circle(s.scr, _C['white'], (bx+dx, y-47), 5)
                pygame.draw.circle(s.scr, (15,5,30), (bx+dx+1, y-47), 3)

        # Mouth
        if s.char_state == 'hurt':
            pygame.draw.arc(s.scr, _C['ground_d'], (bx-5, y-42, 12, 8), 3.3, 6.0, 2)
        elif 'attack' in s.char_state:
            pygame.draw.ellipse(s.scr, (15,5,30), (bx-4, y-38, 10, 6))
        else:
            pygame.draw.arc(s.scr, _C['ground_d'], (bx-5, y-38, 12, 7), 0.1, math.pi-0.1, 2)

        # Body
        body_col = flash_col or _C['accent']
        pygame.draw.rect(s.scr, body_col, (bx-12, y-24, 24, 26), border_radius=5)

        # Legs (animated)
        ph = s.cf * math.pi / 2
        speed = 1.5 if 'attack' in s.char_state else 1.0
        for dx, si in [(-6, 1), (6, -1)]:
            ex = bx + dx + int(math.sin(ph * si * speed) * 10)
            pygame.draw.line(s.scr, body_col, (bx+dx, y+2), (ex, y+18), 5)

        # Weapon attack
        if s.cat > 0:
            ext = int((0.18 - s.cat) / 0.18 * 30)
            wc = WC[min(wlv, len(WC)-1)]; th = 3 + wlv; ln = 30 + wlv * 10 + ext
            if s.ca == 'gnd':
                pygame.draw.line(s.scr, wc, (bx+14, y-20), (bx+ln, y-24), th)
                if wlv >= 1:
                    trail = pygame.Surface((ln, 20), pygame.SRCALPHA)
                    pygame.draw.arc(trail, (*wc, 80), (0, 0, ln, 20), 0, math.pi, th)
                    s.scr.blit(trail, (bx+14, y-34))
                if wlv >= 2: pygame.draw.circle(s.scr, wc, (bx+ln, y-24), 5+wlv)
            elif s.ca == 'air':
                pygame.draw.line(s.scr, wc, (bx+4, y-34), (bx+ln, y-58-ext), th)
                if wlv >= 2: pygame.draw.circle(s.scr, wc, (bx+ln, y-58-ext), 5+wlv)

    # ── Particles + Popups ──
    def _draw_parts(s):
        for p in s.parts:
            a=max(0,min(255,int(255*p.life/p.ml)))
            sz=max(1,int(p.sz*p.life/p.ml))
            sf=pygame.Surface((sz*2+2,sz*2+2),pygame.SRCALPHA)
            if p.kind=='spark':
                pygame.draw.circle(sf,(*p.col,a),(sz+1,sz+1),sz)
                pygame.draw.circle(sf,(*_C['white'],a//2),(sz+1,sz+1),max(1,sz//2))
            else:
                pygame.draw.circle(sf,(*p.col,a),(sz+1,sz+1),sz)
            s.scr.blit(sf,(int(p.x)-sz-1,int(p.y)-sz-1))

    def _draw_pops(s):
        for j in s.pops:
            a=max(0,min(255,int(255*min(1,j.life/0.25))))
            sz=max(14,int(22*j.sc))
            f=s._f(sz,True)
            sh=f.render(j.txt,True,(0,0,0)); sh.set_alpha(a//3)
            s.scr.blit(sh,(int(j.x)-sh.get_width()//2+2,int(j.y)+2))
            r=f.render(j.txt,True,j.col); r.set_alpha(a)
            s.scr.blit(r,(int(j.x)-r.get_width()//2,int(j.y)))

    # ── HUD ──
    def _hud(s,w,h,gm):
        st=gm.state
        # HP bar
        hpw,hph=200,12; hpx,hpy=16,14
        bg=pygame.Surface((hpw+4,hph+4),pygame.SRCALPHA)
        pygame.draw.rect(bg,(0,0,0,120),(0,0,hpw+4,hph+4),border_radius=7)
        s.scr.blit(bg,(hpx-2,hpy-2))
        pygame.draw.rect(s.scr,(30,15,50),(hpx,hpy,hpw,hph),border_radius=6)
        hw=int(hpw*st.hp/st.hp_max)
        hc=_C['green'] if st.hp>50 else _C['gold'] if st.hp>25 else _C['red']
        if hw>0: pygame.draw.rect(s.scr,hc,(hpx,hpy,hw,hph),border_radius=6)
        t=s._f(11).render(f"HP {int(st.hp)}",True,_C['text2'])
        s.scr.blit(t,(hpx,hpy+hph+2))

        # Score
        sc=s._f(26,True).render(f"{st.score:,}",True,_C['white'])
        sh=s._f(26,True).render(f"{st.score:,}",True,(0,0,0)); sh.set_alpha(60)
        s.scr.blit(sh,(w-sc.get_width()-18,14)); s.scr.blit(sc,(w-sc.get_width()-20,12))
        ac=s._f(13).render(f"{st.accuracy:.1f}%",True,_C['text2'])
        s.scr.blit(ac,(w-ac.get_width()-20,42))

        # Combo
        if st.combo>2:
            cs=s._f(44,True).render(f"{st.combo}x",True,_C['gold'])
            cs.set_alpha(220)
            cx=w//2-cs.get_width()//2; cy=int(h*0.16)
            sh=s._f(44,True).render(f"{st.combo}x",True,(0,0,0)); sh.set_alpha(50)
            s.scr.blit(sh,(cx+2,cy+2)); s.scr.blit(cs,(cx,cy))
            cl=s._f(11).render("COMBO",True,_C['text3'])
            s.scr.blit(cl,(w//2-cl.get_width()//2,cy+50))

        # Weapon
        if st.weapon_level>0:
            wn=['','Schwert','Flamme','Blitz','Nova'][min(st.weapon_level,4)]
            wc=WC[min(st.weapon_level,len(WC)-1)]
            ws=s._f(14,True).render(f"⚔ {wn} Lv.{st.weapon_level}",True,wc)
            s.scr.blit(ws,(w-ws.get_width()-20,60))

        # Progress
        dur=gm.chart.objects[-1].hit_time+2000 if gm.chart.objects else 1
        prog=min(1,gm.song_time/dur)
        bw=int(w*0.28); bx=(w-bw)//2; by=h-16
        pygame.draw.rect(s.scr,(30,15,50),(bx,by,bw,4),border_radius=2)
        if prog>0: pygame.draw.rect(s.scr,_C['air'],(bx,by,int(bw*prog),4),border_radius=2)

        # Timing bar
        if gm.timing_records:
            import time as _t; now=_t.perf_counter()
            tbw,tbh=160,5; tbx=w//2-tbw//2; tby=h-30
            pygame.draw.rect(s.scr,(20,10,40),(tbx,tby,tbw,tbh),border_radius=2)
            pygame.draw.line(s.scr,_C['text3'],(tbx+tbw//2,tby-1),(tbx+tbw//2,tby+tbh+1))
            pw=gm.hit_windows.perfect
            for rec in gm.timing_records[-20:]:
                age=now-rec.time
                if age>1.2: continue
                al=max(0,int(255*(1-age/1.2)))
                ratio=max(-1,min(1,rec.error_ms/100))
                px=tbx+tbw//2+int(ratio*tbw/2)
                c=_C['gold'] if abs(rec.error_ms)<=pw else _C['air'] if rec.error_ms>0 else _C['ground']
                ms=pygame.Surface((3,tbh+2),pygame.SRCALPHA); ms.fill((*c,al))
                s.scr.blit(ms,(px-1,tby-1))

        s.scr.blit(s._f(10).render("[ESC] Pause  [+/-] Vol",True,_C['text3']),(16,h-30))

    # ── Overlays ──
    def render_tutorial(s, w, h, song_time):
        if song_time > 5000: return
        al = max(0, min(255, int(255 * (1 - song_time / 5000))))
        hints = [
            (f"D / J  →  Boden-Gegner treffen", int(h * GY) + 45),
            (f"F / K  →  Luft-Gegner treffen", int(h * AY) - 45),
        ]
        for txt, y in hints:
            t = s._f(14, True).render(txt, True, _C['gold'])
            t.set_alpha(al)
            sh = s._f(14, True).render(txt, True, (0,0,0))
            sh.set_alpha(al // 3)
            s.scr.blit(sh, (int(w * HX) + 82, y + 2))
            s.scr.blit(t, (int(w * HX) + 80, y))

    def _countdown(s,w,h,cd):
        ov=pygame.Surface((w,h),pygame.SRCALPHA); ov.fill((0,0,0,140))
        s.scr.blit(ov,(0,0))
        v=max(0,int(cd)+1) if cd>0 else 0
        txt=str(v) if v>0 else "LOS!"
        col=_C['gold'] if v>0 else _C['green']
        f=s._f(80,True); r=f.render(txt,True,col)
        sh=f.render(txt,True,(0,0,0)); sh.set_alpha(80)
        s.scr.blit(sh,(w//2-r.get_width()//2+3,h//2-r.get_height()//2+3))
        s.scr.blit(r,(w//2-r.get_width()//2,h//2-r.get_height()//2))

    def _overlay(s,w,h,title,sub,col):
        ov=pygame.Surface((w,h),pygame.SRCALPHA); ov.fill((0,0,0,180))
        s.scr.blit(ov,(0,0))
        f1=s._f(48,True); r1=f1.render(title,True,col)
        sh=f1.render(title,True,(0,0,0)); sh.set_alpha(80)
        s.scr.blit(sh,(w//2-r1.get_width()//2+2,h//2-32)); s.scr.blit(r1,(w//2-r1.get_width()//2,h//2-34))
        r2=s._f(15).render(sub,True,_C['text2'])
        s.scr.blit(r2,(w//2-r2.get_width()//2,h//2+22))
