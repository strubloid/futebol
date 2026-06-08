"""Run update_channels with lower concurrency and better timeout handling."""
import time
from pathlib import Path
from futebol.services.channel_index_service import ChannelIndexService

t0 = time.time()
svc = ChannelIndexService(channels_dir=Path("channels"), m3u_dir=Path("m3u"))

all_entries = svc._load_all_entries()
print(f"Loaded {len(all_entries)} entries", flush=True)

# Lower concurrency (10) but test each with 15s timeout
result = svc.update_channels(concurrency=10, timeout=15)
elapsed = time.time() - t0
print(f"Done in {elapsed:.1f}s", flush=True)
print(f"before={result.before} after={result.after} removed={result.removed}", flush=True)
if result.backup_path:
    print(f"backup={result.backup_path}", flush=True)
