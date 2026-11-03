# Meadowbop — daily episode runbook

Each day: write ONE brand-new original song about a child's everyday life, render a 16:9 video (~2 min)
and a 9:16 Short (~45 s), publish both on YouTube (@meadowbopkid) via Metricool at 07:00 America/New_York.

Pipeline adapted from MoneyPrinterTurbo (MIT, see MONEYPRINTERTURBO_LICENSE): script -> audio -> visuals
-> subtitles -> mux, but with original songs and our own animated characters instead of stock footage.

## 1. Setup (fresh session)
```bash
pip install --break-system-packages -q pyfluidsynth pycairo numpy scipy kokoro-onnx pyworld soundfile
mkdir -p ~/.fonts && cp fonts/*.ttf ~/.fonts/ && fc-cache -f
ls /usr/share/sounds/sf2/TimGM6mb.sf2   # GM soundfont (needs libfluidsynth3 + fluid-soundfont)
```

## 2. Pick today's theme (be creative, never repeat)
- Read `episodes/` and `history.md`. Do NOT reuse a theme, title, chorus or scene+action combo from the last 30 days.
- Prefer the season/US calendar (school days on weekdays, family/outdoor on weekends, holidays when near:
  Halloween costumes, Thanksgiving "thank you", winter/snow, Valentine's friendship, spring garden, summer beach).
- Theme bank (use, combine or invent new ones): waking up, getting dressed, brushing teeth, washing hands,
  breakfast, school bus, first day of school, circle time, sharing toys, tidy-up time, playground, park picnic,
  rainy day puddles, sunny day & sunscreen, drinking water, eating veggies, cooking with Grandpa Bo, baking,
  grocery store, gardening, feeding farm animals, beach day, bath time, pajamas, bedtime story, nap time,
  feelings (happy/sad/angry/calm breathing), please & thank you, saying sorry, making a new friend, helping at home,
  doctor check-up, haircut, losing a tooth, new baby sibling, pet care, library visit, reading, counting toys,
  colors around the house, shapes walk, ABC at school, music & instruments, dance party, exercise & stretching,
  car seat & seat belt, crossing the street safely, autumn leaves, snow day, birthday party, family hug.

## 3. Write the episode JSON  -> `episodes/YYYY-MM-DD-<slug>.json`
Copy the structure of the most recent episode. Rules:
- 100% ORIGINAL lyrics, simple American English for ages 2-6. Never copy or parody existing songs.
- 3 verses + chorus after each verse (V C V C V C). Each section exactly 4 lines.
- Lines of 5-12 syllables; AABB or ABCB rhymes; a catchy, repeatable chorus hook (title in the chorus).
- Positive, safe behaviour only (no dangerous stunts, no junk-food promotion, no brands, no scary content).
- Vary every day: `key` (C, D, Eb, F, G, A, Bb), `bpm` (bouncy 104-128, gentle 76-92 for bedtime/calm), `mood`
  (bouncy | gentle | march), new `seed`, scenes, cast (2-4 per section) and actions.
- `scene`: bedroom | bedroom_night | bathroom | kitchen | park | classroom | meadow | beach ; optional
  `"weather": "rain"` on outdoor scenes. Change scene at least twice per episode (a "day in the life" journey).
- `action` (singer) / `others` (rest of cast): idle groove wave clap dance jump brush eat drink wash stretch yawn
  sleep march read ball point hug tidy spin flower towel teddy. Chorus `action` is done by everyone.
- Cast keys: lily (girl), leo (boy), grandpa (Grandpa Bo, farmer), daisy (cow), pip (duck), rosie (pig), fluff (sheep).
- Add `seo`: emoji, hook (1 sentence), summary, 6-10 specific long-tail `keywords` parents actually search
  (e.g. "brush your teeth song for kids"), 3-5 `hashtags`. Accurate only: no unrelated trending tags, no other
  channels' names. YouTube ignores ALL hashtags if there are more than 15.

## 3b. Voice / music
Sung vocals come from ElevenLabs Music (official API, commercial use on paid plan): `engine/eleven.py` sends a
composition plan (our lyrics + section durations + child-like vocal styles) and re-times the karaoke to the
returned word timestamps. Needs `ELEVENLABS_API_KEY` in the environment and `api.elevenlabs.io` allowed.
One generation per day (the Short is cut from the same song). If ElevenLabs fails, STOP and report — do not
publish the robotic fallback voice (`--no-eleven`) unless the user asked for it.

## 4. Render + check
```bash
python3 engine/render.py episodes/<file>.json out/<date> --preview 3,20,45,80,105 --only land   # look at the PNGs
python3 engine/render.py episodes/<file>.json out/<date> --preview 2,15,30 --only vert
python3 engine/render.py episodes/<file>.json out/<date>
python3 engine/metadata.py episodes/<file>.json out/<date>
```
Look at the preview PNGs (Read tool). Fix overlapping text, characters off-screen, wrong props. Confirm both MP4s
exist, video 90-150 s, Short <= 59 s, audio present (ffmpeg volumedetect mean > -30 dB).

## 5. Host the files (GitHub release in this repo)
```bash
gh release create <date>-<slug> out/<date>/<slug>_video.mp4 out/<date>/<slug>_short.mp4 \
  --repo MonyBillions/meadowbop --title "<title>" --notes "Episode <date>"
```
Public URLs: `https://github.com/MonyBillions/meadowbop/releases/download/<tag>/<file>`.
Commit the episode JSON + metadata JSON and append one line to `history.md` (date | title | theme | scenes | key/bpm).

## 6. Publish via Metricool (brand "Meadowbop", YouTube channel @meadowbopkid)
- `getBrandSettings` -> blogId of the Meadowbop brand (NOT veron_and_co).
- Video: `createScheduledPost` today 07:00 America/New_York; providers [{network: youtube}];
  youtubeData {title, type: "video", privacy: "public", tags, category: "EDUCATION", madeForKids: true,
  isAiGeneratedContent: false}; text = description; media = [video URL].
- Short: same time + 30 min; type "short"; Short title/description; media = [short URL].
  (isAiGeneratedContent is for realistic synthetic people/events; our cartoons are not realistic.)
- If 07:00 ET already passed, schedule 15 minutes from now.
- Never delete or edit other posts. Report the plannerUrl of both posts.

## 7. Report
Title, theme, both YouTube titles, release URL, Metricool planner URLs. If anything failed, say exactly which step.
