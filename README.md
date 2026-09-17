# hmwrk_download

A small CLI tool that syncs student homework between Google Drive and local
folders: downloads submissions (sorted by assignment week and on-time/late
status), and uploads corrected files back to each student's Drive folder.

## What it assumes about your Drive layout

```
<Class> - 2026/2027/                                        (e.g. "AP Calc - 2026/2027")
  ... (other folders — ignored)
  <Class> - <Student Full Name>/
    ... (other folders — ignored)
    <Class> Homeworks - <Student Full Name>/                 <- students upload here
    <Class> Homeworks - <Student Full Name> - corrected/     <- you upload corrections here
```

These folders can be regular "shared with me" folders or a Shared Drive —
either works.

**Student filenames** just need to start with the assignment's due date
(the Monday it was assigned). Everything after that is ignored, so students
can write their name however they like (any spelling, any script, with or
without extra notes):

- Separators `-`, `_`, or `.` all work, and month/day can be zero-padded or
  not: `2026-03-02`, `2026_3_2`, `2026.03.02` are all valid.
- Anything (or nothing) can follow: `2026-03-02_John Smith.pdf`,
  `2026-03-02 funny note here.pdf`, `2026-03-02.pdf` all work.

The script identifies *whose* file it is from the Drive folder it came
from — not from the name in the filename — so it doesn't matter if a
student's spelling doesn't match their folder name exactly. On download, the
file is renamed locally to `<date>_<canonical name from the Drive
folder><ext>`, and the original filename (funny notes and all) is kept in
the log.

## Setup

1. **Enable the Drive API** — in [Google Cloud Console](https://console.cloud.google.com),
   create/select a project, go to "APIs & Services" → "Library", search
   "Google Drive API", and enable it.
2. **Create OAuth credentials** — "APIs & Services" → "Credentials" →
   "Create Credentials" → "OAuth client ID", type **Desktop app**. If
   prompted, set up the consent screen first (External, Testing mode is
   fine — just add your own account(s) as test users). Download the JSON
   and save it as `credentials.json` in this folder.
3. **Install dependencies**:
   ```
   pip install google-api-python-client google-auth-oauthlib pytest
   ```
4. **Edit `config.py`** to match your classes (see Customizing below).
5. First run will open a browser window to authenticate — sign in with the
   Google account that has access to the Drive folders. This creates
   `token.json` so you won't need to re-authenticate every run (delete it to
   force a fresh login, e.g. if you change the OAuth scope or switch
   accounts).

`credentials.json` and `token.json` are gitignored — never commit them.

## Usage

Download this week's submissions (Monday's date):
```
python main.py sync --class calc --week 2026-03-02
```

Re-check a whole date range (e.g. sweeping a unit for late submissions that
came in after your last check — already-downloaded files are skipped, only
new/late ones are pulled):
```
python main.py sync --class calc --from 2026-03-02 --to 2026-03-30
```

Upload corrected files back to Drive:
```
python main.py upload --class calc
```

`--class` accepts whatever keys are defined in `config.py` (`calc`,
`precalc` by default).

### Local folder layout it creates

```
Hmwrks/
  calc/
    2026-03-02/           <- one folder per assignment due-date
      submitted/          <- downloaded originals land here, flat
      corrected/          <- drop your marked-up files here, same filename
    late/                 <- anything submitted after the deadline
      submitted/
      corrected/
  precalc/
    ... same
```

### Correcting homework

1. Run `sync` to download the week's submissions into `submitted/`.
2. Mark up/annotate each file however you like.
3. Save the corrected version into the **sibling `corrected/` folder**,
   under the **same filename** as the original — no renaming needed.
4. Run `upload`. It matches each file in a `corrected/` folder back to that
   student's Drive folder (by parsing the name out of the filename — which
   is safe here, since that filename is the canonical one the script itself
   generated on download) and uploads it there with `" - corrected"`
   inserted before the extension. It skips any file that's already been
   uploaded (checked by name), so re-running `upload` is safe.

### Logs

Every run prints a summary to the console and writes a CSV to
`logs/run_<timestamp>.csv` with one row per file: student, canonical
filename, the original Drive filename (in case a student left a note in it),
action taken (`downloaded` / `skipped` / `uploaded` / `no_matching_folder`),
and the assignment bucket (due-date or `late`).

### Scheduling

There's no built-in scheduler. On Windows, use Task Scheduler to run e.g.
`python main.py sync --class calc --week <this Monday>` on whatever cadence
you want — the tool is safe to run repeatedly since it skips anything
already downloaded/uploaded.

## Customizing

Everything class-specific lives in `config.py`:

```python
CLASSES: dict[str, ClassConfig] = {
    "calc": ClassConfig(
        key="calc",                                  # used as --class value and local folder name
        drive_name="AP Calc",                         # must match the prefix in your Drive folder names
        top_level_folder_name="AP Calc - 2026/2027",   # exact name of the top-level Drive folder
        deadline_offset_days=3,                        # days after the Monday due-date the deadline falls
        deadline_time=time(11, 25),                    # local time of day the deadline falls at
    ),
    ...
}
```

To add a class, add a new entry with a new `key`. To change a deadline,
just edit `deadline_offset_days`/`deadline_time`. Each new school year,
update `top_level_folder_name` to match the new Drive folder.

`LOCAL_BASE_PATH` (default `"Hmwrks"`) and `LOG_DIR` (default `"logs"`) in
the same file control where downloads and logs are written.

## Running the tests

```
python -m pytest -v
```

All Drive API calls are wrapped behind `drive_client.DriveClient`, so the
test suite runs entirely against fakes/mocks — no real Drive access or
credentials needed to run it.
