"""Rebuild queue/README.md: one row per queued episode with download links and YouTube metadata.
usage: python3 queue_index.py /path/to/media/queue"""
import glob, json, os, sys

RAW = "https://raw.githubusercontent.com/MonyBillions/meadowbop/media/queue"

q = sys.argv[1]
rows = []
for d in sorted(glob.glob(os.path.join(q, "20*"))):
    date = os.path.basename(d)
    meta = glob.glob(os.path.join(d, "*_metadata.json"))
    vid = glob.glob(os.path.join(d, "*_video.mp4")); sh = glob.glob(os.path.join(d, "*_short.mp4"))
    if not (meta and vid):
        continue
    m = json.load(open(meta[0]))
    rows.append((date, m["video"]["title"], os.path.basename(vid[0]), os.path.basename(sh[0]) if sh else ""))
lines = ["# Meadowbop upload queue", "",
         "Download, upload to YouTube Studio (as Draft), then ask Claude to fill the details and schedule 1 per day.",
         "Each folder also has `*_metadata.json` with title, description, tags (made for kids = yes).", "",
         "| made on | title | video | short |", "|---|---|---|---|"]
for date, title, v, s in rows:
    lines.append(f"| {date} | {title} | [{v}]({RAW}/{date}/{v}) | " + (f"[{s}]({RAW}/{date}/{s})" if s else "") + " |")
open(os.path.join(q, "README.md"), "w").write("\n".join(lines) + "\n")
print(len(rows), "episodes in queue")
