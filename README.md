# Meadowbop 🌼 — daily animated sing-along songs for kids

Original songs about a child's everyday life, with an original cast: Lily, Leo, Grandpa Bo, Daisy the Cow,
Pip the Duck, Rosie the Pig and Fluff the Sheep.

- `engine/rig.py` — shaded vector characters with jointed arms/legs, head tilt, props
- `engine/actions.py` — action poses (brush, eat, wash, dance, sleep, read…)
- `engine/scenes.py` — bedroom (day/night), bathroom, kitchen, park, classroom, meadow, beach
- `engine/music.py` — lyrics → original melody, chords, arrangement, FluidSynth audio
- `engine/render.py` — 2D renderer + overlays (karaoke, logo, titles) reused by the 3D compositor
- `engine3d/` — 3D pipeline (Blender): `chars3d.py` cast, `sets3d.py` sets, `render3d.py` multi-angle animation, `compose3d.py` overlays + audio
- `engine/eleven.py` — ElevenLabs Music (sung vocals, word timestamps)
- `engine/metadata.py` — YouTube title/description/chapters/tags/hashtags
- `episodes/` — one JSON per day; `history.md` — what was already published
- `DAILY.md` — the runbook the daily scheduled task follows

Pipeline idea adapted from MoneyPrinterTurbo (MIT license, see `MONEYPRINTERTURBO_LICENSE`).
