# Homework Sync Tool — Design

## Purpose

The user is a TA for "AP Calc" and "PreCalc" classes. Students upload homework
to per-student Google Drive folders shared with the TA. The TA needs a tool
to:

1. Download student homework submissions to local disk, sorted by
   assignment week and by whether they were submitted on time or late.
2. Upload corrected versions of those files back to each student's
   "corrected" Drive folder.
3. Re-check a date range (e.g. a whole grading unit) at any time to catch
   late submissions that arrived after an earlier check.
4. Produce a review log of what the tool did on each run, so behavior can
   be verified in the first few weeks of use.

Out of scope for this tool: scheduling. The user will trigger runs manually,
or via Windows Task Scheduler calling the CLI — no in-app scheduler is
built.

## Drive folder structure (existing, not created by this tool)

```
<Class> - 2026/2027/                                        (Class = "AP Calc" | "PreCalc")
  ... (other folders, ignored)
  <Class> - <Student Full Name>/
    ... (other folders, ignored)
    <Class> Homeworks - <Student Full Name>/                (submissions)
    <Class> Homeworks - <Student Full Name> - corrected/    (TA uploads corrections here)
```

All of these folders are shared with the TA's account (not owned by it), and
may live in a Shared Drive or as regular "shared with me" folders — the tool
does not need to know which, since every Drive API call is made with
`supportsAllDrives=True` and `includeItemsFromAllDrives=True`, which works
correctly in both cases.

## Filename convention (enforced by the TA with students)

Submission filenames must start with the assignment's due date (the Monday
it was assigned) followed by the student's full name, e.g.:

```
2026-03-02_John Smith.pdf
```

The full name must appear in the filename so the tool can unambiguously
match a local file back to the correct student's Drive folder (folders are
named `"<Class> - <Student Full Name>"`) — this also disambiguates students
who share a last name.

## Local mirror structure

```
Hmwrks/
  Calc/
    2026-03-02/
      submitted/       (flat — all students' on-time files for this week)
      corrected/       (flat — TA drops marked-up files here, same filenames)
    2026-03-09/
      submitted/
      corrected/
    late/
      submitted/       (flat — all late files across the whole class, any week)
      corrected/
  PreCalc/
    ... same structure
```

No per-student subfolders — files stay flat, matched by parsing the full
name out of each filename. This is deliberately simple since the TA
downloads and corrects files in bulk.

## Deadlines

| Class    | Assigned | Deadline               |
|----------|----------|-------------------------|
| PreCalc  | Monday   | Tuesday, 13:20 local time |
| Calc     | Monday   | Thursday, 11:25 local time |

A submission's Drive `createdTime` (a server-set timestamp, immutable
regardless of when the tool runs) is compared against the deadline for the
week it belongs to (derived from the date in its filename) to classify it
as on-time or late. Times are compared in the local system timezone.

## Core operation: sync (download)

One operation handles both the normal weekly check and the monthly/unit
late-sweep — they differ only in the date range passed in.

```
sync(class, start_monday, end_monday):
  for each student folder under <class>:
    list files in "<Class> Homeworks - <Student>" via files.list
      (fields: name, id, createdTime; supportsAllDrives=True, includeItemsFromAllDrives=True)
    for each file:
      parse due_date, full_name from filename
      if due_date not in [start_monday, end_monday]: skip
      if full_name not in this student folder's name: skip (safety check)
      deadline = due_date + 1 day @ 13:20   (PreCalc)
               = due_date + 3 days @ 11:25  (Calc)
      bucket = "late" if file.createdTime > deadline else due_date.isoformat()
      target = Hmwrks/<class>/<bucket>/submitted/<filename>
      if target exists on disk: skip (already downloaded), log "skipped"
      else: download file to target, log "downloaded"
```

- Weekly use: `sync(class, this_monday, this_monday)`.
- Unit-end late sweep: `sync(class, unit_start_monday, unit_end_monday)` —
  re-scans the whole unit; anything already downloaded is skipped, anything
  newly late (or newly arrived) is picked up and correctly bucketed.

## Upload flow (corrected files)

```
upload(class):
  for each date-or-"late" folder under Hmwrks/<class>:
    for each file in its corrected/ subfolder:
      parse full_name from filename
      find matching "<Class> Homeworks - <full_name> - corrected" Drive folder
      upload_name = filename with " - corrected" inserted before the extension
      if a file named upload_name already exists in that Drive folder: skip, log "skipped"
      else: upload file under upload_name, log "uploaded"
```

The TA never renames files manually — the `" - corrected"` suffix is applied
only on the Drive side, by the tool, at upload time.

## Logging / review output

Every `sync` or `upload` run:
- Prints a summary table to the console (student, filename, action:
  downloaded/uploaded/skipped, on-time/late where applicable).
- Writes the same data to `logs/run_<timestamp>.csv`, so the TA can review
  exactly what happened on any past run — primarily useful for verifying
  correctness in the first few weeks.

## Configuration

A small config (e.g. `config.py` or `config.json`, not committed if it ever
contains anything sensitive — it won't, since it's just class definitions)
holds:
- The two class definitions: display name, Drive folder name prefix,
  deadline weekday offset + time.
- Local base path (`Hmwrks/`) and log path (`logs/`).

`credentials.json` and `token.json` remain local-only (gitignored), same as
in the diagnostic script.

## CLI shape

```
python main.py sync --class calc --week 2026-03-02
python main.py sync --class calc --from 2026-03-02 --to 2026-03-30
python main.py upload --class calc
```

(Exact flag names/parsing are an implementation detail for the plan, not
fixed here.)

## Testing approach

- Unit tests for pure logic: filename parsing (date + full name extraction),
  deadline computation, on-time/late classification — no live Drive calls.
- Drive API interactions (`files.list`, `files.get_media`/download,
  `files.create` for upload) are wrapped in a thin client module so they can
  be mocked in tests; a manual end-to-end smoke test against the TA's real
  Drive (as already done with the diagnostic script) verifies real-world
  behavior before first real use.
