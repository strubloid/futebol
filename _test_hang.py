"""Debug - use wait() with timeout to avoid hanging."""
import time, json, httpx, socket
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

with open('channels/index.json') as f:
    channels = json.load(f)['channels']

results = {}
stuck = []

def test_one(idx, c):
    url = c['streamUrl']
    headers = {"User-Agent": "Mozilla/5.0"}
    if c.get('extraHeaders'):
        headers.update(c['extraHeaders'])
    try:
        old = socket.getdefaulttimeout()
        socket.setdefaulttimeout(10)
        try:
            with httpx.Client(follow_redirects=True, timeout=10) as cl:
                r = cl.get(url, headers=headers)
                ok = 200 <= r.status_code < 400
                if ok and (url.endswith('.m3u8') or '/playlist' in url):
                    ok = r.text[:500].startswith('#EXTM3U')
                return (idx, ok)
        finally:
            socket.setdefaulttimeout(old)
    except Exception:
        return (idx, False)

print(f"Testing {len(channels)} channels...", flush=True)
t0 = time.time()
with ThreadPoolExecutor(max_workers=80) as ex:
    futures = {ex.submit(test_one, i, c): i for i, c in enumerate(channels)}
    
    not_done = set(futures.keys())
    deadline = time.time() + 90
    
    while not_done and time.time() < deadline:
        done, not_done = wait(not_done, timeout=5, return_when=FIRST_COMPLETED)
        for f in done:
            try:
                idx, ok = f.result(timeout=0.1)
                results[idx] = ok
            except Exception:
                idx = futures[f]
                results[idx] = False
        
        if done:
            remaining = len(not_done)
            elapsed = time.time() - t0
            print(f"  {remaining} pending at {elapsed:.0f}s - last completed idx {futures[list(done)[-1]]}", flush=True)
    
    # Cancel stragglers
    for f in not_done:
        idx = futures[f]
        f.cancel()
        stuck.append(idx)
        results[idx] = False
    
    elapsed_total = time.time() - t0
    
# Results
completed = sum(1 for v in results.values() if v)
print(f"\nCompleted: {completed}/{len(channels)} in {elapsed_total:.1f}s", flush=True)
if stuck:
    print(f"\nStuck ({len(stuck)}):", flush=True)
    for i in stuck[:15]:
        print(f"  idx={i}: {channels[i]['name'][:35]} url={channels[i]['streamUrl'][:60]}", flush=True)
