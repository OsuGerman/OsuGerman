#!/usr/bin/env python3
"""Generate 5 songs with 3 difficulties each."""
import json, os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.makedirs('songs', exist_ok=True)
os.makedirs('data/songs', exist_ok=True)
os.makedirs('data/charts', exist_ok=True)

SONGS = [
    {'id':'neon_rush','title':'Neon Rush','artist':'Rhythm Dash','bpm':128,'dur':40,
     'bass':65,'melody':[330,370,415,440,494,440,370,330],'key':'E'},
    {'id':'midnight_pulse','title':'Midnight Pulse','artist':'Rhythm Dash','bpm':110,'dur':45,
     'bass':55,'melody':[262,294,330,349,392,349,330,294],'key':'C'},
    {'id':'electric_surge','title':'Electric Surge','artist':'Rhythm Dash','bpm':150,'dur':35,
     'bass':73,'melody':[392,440,494,523,587,523,494,440],'key':'G'},
    {'id':'crystal_drop','title':'Crystal Drop','artist':'Rhythm Dash','bpm':99,'dur':50,
     'bass':58,'melody':[294,330,370,440,370,330,294,262],'key':'D'},
    {'id':'inferno_beat','title':'Inferno Beat','artist':'Rhythm Dash','bpm':170,'dur':30,
     'bass':82,'melody':[523,587,659,698,784,698,659,587],'key':'C5'},
]

DIFFS = [
    {'id':'easy','name':'Easy','level':3,'snap':2,'density':0.4,'approach':1400},
    {'id':'normal','name':'Normal','level':6,'snap':4,'density':0.7,'approach':1200},
    {'id':'hard','name':'Hard','level':9,'snap':8,'density':1.0,'approach':900},
]

def gen_wav(path, bpm, dur, bass_freq, melody, sr=44100):
    n = int(sr * dur)
    out = np.zeros(n, dtype=np.float64)
    bs = int(60/bpm*sr)
    for i in range(int(dur*bpm/60)):
        s = i*bs; b = i%4
        kl = int(sr*0.12)
        if s+kl<n:
            t=np.arange(kl)/sr; f=150-100*(t/0.12)
            out[s:s+kl]+=np.sin(2*np.pi*f*t)*(1-t/0.12)**2*0.5
        if b==2:
            sl=int(sr*0.07)
            if s+sl<n:
                t=np.arange(sl)/sr
                out[s:s+sl]+=np.random.randn(sl)*(1-t/0.07)**1.5*0.2+np.sin(2*np.pi*200*t)*(1-t/0.07)*0.12
        ho=bs//2; hl=int(sr*0.015)
        if s+ho+hl<n:
            out[s+ho:s+ho+hl]+=np.random.randn(hl)*np.exp(-np.arange(hl)/sr*80)*0.1
        bl=min(bs, n-s)
        if bl>0:
            t=np.arange(bl)/sr
            out[s:s+bl]+=np.sin(2*np.pi*bass_freq*t)*np.exp(-t*3)*0.15
    ei=bs//2; bo=4*bs
    for i,f in enumerate(melody*(int(dur*bpm/60/8)+1)):
        s=bo+i*ei
        if s>=n: break
        ml=min(ei,n-s); t=np.arange(ml)/sr
        e=np.exp(-t*4)*(1-np.clip(t/(ml/sr)-0.8,0,1)*5)
        out[s:s+ml]+=(np.sin(2*np.pi*f*t)*0.1+np.sin(2*np.pi*f*2*t)*0.03)*e
    pf=[bass_freq*2,bass_freq*2.5,bass_freq*3,bass_freq*3.5]
    for i in range(int(dur*bpm/60/4)):
        s=i*4*bs; p=pf[i%4]; pl=min(4*bs,n-s)
        if pl<=0: break
        t=np.arange(pl)/sr
        e=0.05*(1-np.abs(t/(pl/sr)-0.5)*1.5).clip(0)
        out[s:s+pl]+=np.sin(2*np.pi*p*t)*e
    out=out/max(np.abs(out).max(),1e-6)*0.82
    import soundfile as sf
    sf.write(path, np.column_stack([out,out]).astype(np.float64), sr, subtype='PCM_16')

def gen_chart(song, diff, approach):
    bpm=song['bpm']; beat=60000/bpm; dur_s=song['dur']; dur_ms=dur_s*1000
    snap=diff['snap']; density=diff['density']
    objects=[]; oid=0; seen=set()
    total_beats=int(dur_s*bpm/60)
    for i in range(total_beats):
        t=i*beat; bar=i//4; b=i%4; sec=bar//4; prog=t/dur_ms
        if prog < 0.1 and diff['id']!='easy':
            if b==0: oid+=1; objects.append(_obj(oid,t,'Ground','GroundEnemy'))
            continue
        if random.random() > density and diff['id']=='easy': continue
        objects.append(_obj(oid:=oid+1, t, 'Ground', 'GroundEnemy'))
        if sec>=1 and b in (1,3) and density>0.5:
            objects.append(_obj(oid:=oid+1, t+beat/2, 'Air', 'AirEnemy'))
        if sec>=2 and b==0 and density>0.8:
            objects.append(_obj(oid:=oid+1, t+beat/2, 'Air', 'AirEnemy'))
        if sec>=3 and diff['id']=='hard':
            if b==2: objects.append(_obj(oid:=oid+1, t+beat/4, 'Air', 'AirEnemy'))
            if b==0 and bar%4==0:
                objects.append(_obj(oid:=oid+1, t, 'Ground', 'HoldNote', 'Hold', beat*2))
        if sec>=4 and diff['id']!='easy' and b==1:
            objects.append(_obj(oid:=oid+1, t, 'Ground', 'Obstacle', 'Dodge'))
        if sec>=5 and diff['id']=='hard':
            for e in range(snap//2):
                et=t+e*(beat/snap*2)
                objects.append(_obj(oid:=oid+1, et, 'Air' if e%2 else 'Ground',
                    'AirEnemy' if e%2 else 'GroundEnemy'))
    objects.sort(key=lambda o:o['hitTime'])
    unique=[]
    for o in objects:
        k=(round(o['hitTime'],0),o['lane'])
        if k not in seen: seen.add(k); unique.append(o)
    hw = {'easy':{'perfect':45,'great':90,'good':135},
          'normal':{'perfect':35,'great':70,'good':110},
          'hard':{'perfect':25,'great':55,'good':90}}
    return {
        'songId':song['id'],'difficultyId':diff['id'],
        'globalOffsetMs':0,'approachTimeMs':approach,
        'hitWindowProfile':hw[diff['id']],
        'objects':unique,'events':[]
    }

def _obj(oid,t,lane,typ,action='Tap',dur=0):
    return {'id':f'obj_{oid:04d}','type':typ,'lane':lane,
            'hitTime':round(t,1),'spawnTime':round(t-1200,1),
            'actionType':action,'duration':dur}

import random
for song in SONGS:
    wav_path = f"songs/{song['id']}.wav"
    if not os.path.exists(wav_path):
        gen_wav(wav_path, song['bpm'], song['dur'], song['bass'], song['melody'])
        print(f"Generated: {wav_path}")

    diffs_meta = []
    for diff in DIFFS:
        chart = gen_chart(song, diff, diff['approach'])
        chart_path = f"data/charts/{song['id']}_{diff['id']}.json"
        with open(chart_path, 'w') as f:
            json.dump(chart, f, indent=2)
        print(f"  Chart: {chart_path} ({len(chart['objects'])} objects)")
        diffs_meta.append({
            'id': diff['id'], 'name': diff['name'],
            'level': diff['level'], 'chartFile': chart_path
        })

    meta = {
        'id': song['id'], 'title': song['title'], 'artist': song['artist'],
        'bpm': song['bpm'], 'offsetMs': 0,
        'audioFile': os.path.abspath(wav_path),
        'previewStartMs': 5000, 'stageThemeId': 'default',
        'difficulties': diffs_meta
    }
    meta_path = f"data/songs/{song['id']}.json"
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)
    print(f"Song: {meta_path}")

print(f"\n=== Generated {len(SONGS)} songs x {len(DIFFS)} difficulties = {len(SONGS)*len(DIFFS)} charts ===")
