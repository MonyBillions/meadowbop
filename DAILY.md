# Meadowbop — daily 3D episode runbook

Every day the scheduled task makes ONE new episode (original song about a child's everyday life, sung by
ElevenLabs, animated in 3D with Blender) and adds it to the upload queue. Once a week the owner uploads the
queued videos to YouTube Studio and Claude fills in titles/descriptions and schedules 1 video per day.
Pipeline idea adapted from MoneyPrinterTurbo (MIT, see MONEYPRINTERTURBO_LICENSE).

Runs in the claude.ai/code cloud environment **Default** (it holds the ElevenLabs network secret).
Never print, ask for or commit API keys.

## 1. Setup
```bash
pip install --break-system-packages -q bpy pycairo numpy scipy pyfluidsynth
mkdir -p ~/.fonts && cp fonts/*.ttf ~/.fonts/ && fc-cache -f
```

## 2. Choose today's theme (creative, never repeat)
Read `history.md` and `episodes/`. No theme, title, chorus or scene+action combo from the last 30 days.
Follow the US calendar (school on weekdays, family/outdoor on weekends, holidays when near).
Theme bank: waking up, getting dressed, brushing teeth, washing hands, breakfast, school bus, circle time,
sharing toys, tidy-up, playground, picnic, rainy-day puddles, sunscreen, drinking water, veggies, cooking with
Grandpa Bo, baking, grocery store, gardening, feeding farm animals, beach day, bath time, pajamas, bedtime story,
nap time, feelings & calm breathing, please & thank you, saying sorry, new friend, helping at home, doctor
check-up, haircut, losing a tooth, new baby sibling, pet care, library, counting toys, colors, shapes walk, ABCs,
music & instruments, dance party, stretching, seat belt, crossing the street, autumn leaves, snow day, birthday.

## 3. Write `episodes/YYYY-MM-DD-<slug>.json` (copy the latest one's structure)
- 100% original lyrics, simple American English for ages 2-6; never copy/parody existing songs.
- V C V C V C, 4 lines per section, 5-12 syllables per line, catchy chorus containing the title.
- Positive, safe behaviour; no brands, no scary content.
- Vary daily: key (C D Eb F G A Bb), bpm (bouncy 104-128 / gentle 76-92), mood (bouncy|gentle|march), new seed.
- scene per section: bedroom | bedroom_night | bathroom | kitchen | park | classroom | meadow | beach.
  Change scene at least twice (a little journey through the day).
- singer + action / others per verse; chorus action for everyone. Actions: idle groove wave clap dance jump brush
  eat drink wash stretch yawn sleep march read ball point hug tidy spin flower teddy.
- cast keys: lily, leo, grandpa, pip (duck), rosie (pig), daisy (cow), fluff (sheep); 2-4 per section.
- `seo`: emoji, hook, summary, 6-10 long-tail keywords parents search, 3-5 hashtags (accurate only; max 15 total).

## 4. Song (ElevenLabs, once per episode)
```bash
python3 - <<'PY'
import json, sys; sys.path.insert(0, "engine"); import music, eleven
ep = json.load(open("episodes/<file>.json")); song = music.build_song(ep)
eleven.compose(ep, song, "out/<date>/<slug>_song.mp3")
PY
```
On HTTP error: print status + body; if music_v2_5 rejected, set MEADOWBOP_MUSIC_MODEL=music_v2 then music_v1.
If ElevenLabs is unreachable or fails twice, STOP and report (do not publish a robotic fallback).

## 5. Render 3D (Cycles CPU ~5.5 s/frame; resumable)
Check 4 preview frames first and look at them (Read):
`python3 engine3d/render3d.py episodes/<file>.json out/<date> --layout land --samples 4 --only 3,30,60,100`
Then render in chunks so every command stays under ~9 minutes (existing frames are skipped):
```bash
for a in $(seq 0 90 1500); do python3 engine3d/render3d.py episodes/<file>.json out/<date> --layout land --samples 4 --start $a --end $((a+90)); done
```
(run one chunk per command; land ≈ 1400 frames, vert ≈ 510 frames). Same for `--layout vert`.

## 6. Compose (karaoke, logo, titles, audio)
```bash
python3 engine3d/compose3d.py episodes/<file>.json out/<date> --layout land
python3 engine3d/compose3d.py episodes/<file>.json out/<date> --layout vert
python3 engine/metadata.py episodes/<file>.json out/<date>
```
Check: video 90-150 s, Short ≤ 59 s, audio present; look at 3 frames of each.

## 7. Add to the upload queue (`media` branch, folder `queue/<date>/`, keep the last 14 days)
```bash
D=<date>; rm -rf /tmp/media && git clone --depth 1 -b media https://github.com/MonyBillions/meadowbop /tmp/media
cd /tmp/media && mkdir -p queue && ls -d queue/20*/ 2>/dev/null | sort | head -n -13 | xargs -r rm -rf
mkdir -p queue/$D && cp ~/meadowbop/out/$D/<slug>_video.mp4 ~/meadowbop/out/$D/<slug>_short.mp4 \
   ~/meadowbop/out/$D/<slug>_metadata.json queue/$D/
python3 ~/meadowbop/engine3d/queue_index.py /tmp/media/queue      # rebuilds queue/README.md
git checkout --orphan tmp && git add -A && git -c user.name="Meadowbop Bot" -c user.email="noreply@anthropic.com" \
  commit -qm "queue $D" && git branch -D media && git branch -m media && git push -f origin media
```
Commit the episode JSON + metadata to `main`, append a line to `history.md`
(date | title | theme | scenes | key/bpm), push main.

## 8. Report
Title, theme, durations, queue URL https://github.com/MonyBillions/meadowbop/tree/media/queue — or the exact
failing step.
