# Start here (cloud, no installs)

You are in a ready-made workspace: Python, ffmpeg, the render engine and the local voice are installed.

1. Open the chat panel of your coding agent (Claude Code, Codex, Copilot…) or a terminal.
2. Ask: **"Use the docuframe skill in skills/docuframe to make a 2 minute documentary about …"**
3. Or by hand in the terminal:
   ```
   docuframe new my-film
   # edit my-film/script.json, facts.json, film.json
   docuframe make --project my-film --yes
   ```
4. Your film is in `my-film/out/`. Right-click → Download.
