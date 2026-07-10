## 1. Logging configuration

- [x] 1.1 In `main.py`, add `import logging`, a module-level
      `logger = logging.getLogger(__name__)`, and a `logging.basicConfig(...)`
      call at module import time (before `main()`/`if __name__`) reading
      level from `LOG_LEVEL` (default `"INFO"`), format
      `"%(asctime)s %(levelname)s %(name)s: %(message)s"`.
- [x] 1.2 In `media.py`, add `import logging` and
      `logger = logging.getLogger(__name__)`.
- [x] 1.3 In `providers.py`, add `import logging` and
      `logger = logging.getLogger(__name__)`.

## 2. Convert main.py

- [x] 2.1 Convert the task-start banner print (`Task %s | styles=%s`) to
      `logger.info`.
- [x] 2.2 Convert the "Probed duration" print (added earlier this session)
      to `logger.info`.
- [x] 2.3 Convert "Task %s done in %.1fs" and the per-style caption preview
      prints to `logger.info`.
- [x] 2.4 In `run_tasks`'s exception handler, replace
      `print(f"ERROR on task {task_id}: {e}")` + `traceback.print_exc()`
      with a single `logger.exception("Task %s failed: %s", task_id, e)`.
- [x] 2.5 Convert `main()`'s "Loading tasks from", "Wrote N results",
      self-check warning/pass/failure, and final "ERROR: N task(s) failed"
      prints to the appropriate `logger.info`/`logger.warning`/
      `logger.error` calls.

## 3. Convert media.py

- [x] 3.1 Convert `download_video`'s local-file and HTTP download/size
      prints to `logger.info`.
- [x] 3.2 Convert `extract_frames`'s "Extracting frames..." and "Extracted
      N frame(s)" prints (added earlier this session) to `logger.info`.

## 4. Convert providers.py and complete stage logging

- [x] 4.1 Convert `_retry`'s failure/backoff print to `logger.warning`.
- [x] 4.2 Convert `_b64_frames`'s "Encoding N frame(s) to base64..." print
      (added earlier this session) to `logger.info`.
- [x] 4.3 Convert `get_provider`'s "Caption provider: %s" print to
      `logger.info`.
- [x] 4.4 Convert `GeminiProvider.caption_clip`'s upload/send/receive
      prints (added earlier this session) to `logger.info`.
- [x] 4.5 Add matching send/receive stage logs to
      `OpenAIProvider.caption_clip`: `logger.info` immediately before the
      `_call()` request (naming the provider and model) and immediately
      after receiving the response.
- [x] 4.6 Add matching send/receive stage logs to
      `AnthropicProvider.caption_clip`: same pattern as 4.5.

## 5. Verify

- [x] 5.1 Run `tests/test_contract.py` and `tests/test_providers.py`;
      confirm no regressions from the logging conversion.
- [x] 5.2 Run the container (or `main.py` locally) against
      `sample_tasks.json` and visually confirm: timestamped log lines,
      correct level names, and a full stage sequence (download → probe →
      extract → encode → send → receive) for at least one frame-based
      provider run.
