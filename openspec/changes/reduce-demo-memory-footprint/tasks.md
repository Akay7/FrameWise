## 1. Frame sampling rewrite

- [x] 1.1 Replace `NUM_FRAMES` (fixed count) with `FRAME_INTERVAL_SECONDS` (default 4) and `MAX_FRAMES` (default 30) in `media.py`
- [x] 1.2 Rewrite `extract_frames` to use a single `ffmpeg` pass with the `fps` filter instead of one subprocess per frame
- [x] 1.3 Update `providers.py`'s `_b64_frames` call site (`extract_frames(clip_path, frame_dir)`, no longer passing a frame count/duration through)
- [x] 1.4 Update `README.md`'s env var documentation (`FRAME_INTERVAL_SECONDS`/`MAX_FRAMES` replace `NUM_FRAMES`)

## 2. Batch tab resource defaults

- [x] 2.1 `app.py`: `DEMO_MAX_PARALLEL_TASKS` default 4 → 1 (sequential by default)
- [x] 2.2 `app.py`: `DEMO_MAX_VIDEO_MB` default 200 → 50
- [x] 2.3 Update the batch status message to read naturally when running sequentially ("one at a time" vs "up to N in parallel")

## 3. Deployment hygiene

- [x] 3.1 `Dockerfile.demo`: set `GRADIO_ANALYTICS_ENABLED=False`

## 4. Verify

- [x] 4.1 `python -m py_compile media.py providers.py app.py main.py`
- [x] 4.2 Direct unit check of `extract_frames` against a real sample clip: 6-second clip → 2 frames (matches `duration / FRAME_INTERVAL_SECONDS`, rounded up), single ffmpeg pass completes in ~0.35s
- [x] 4.3 Re-run `tests/test_contract.py` and `tests/test_providers.py` — both pass unchanged
- [ ] 4.4 Confirm the batch tab no longer OOMs on Render with a frame-based provider and real 4K clips — **manual**: needs the user to push and re-test against the live deployment; not verifiable from this environment
