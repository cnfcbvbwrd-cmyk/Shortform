# Short Form Builder

Turns a probationary firefighter's Daily Performance Summary into a filled,
signable City of San Jose Short Form Performance Report (Form 240-081-1A
Rev. 4/99).

Everything runs in the browser. No summary, no form and no name ever leaves
the device.

## Install it on an iPhone

1. Open the Pages URL in Safari.
2. Share, then **Add to Home Screen**.
3. Launch it from the icon. It runs full screen and works with no signal.

## Using it

1. **Paste the email**, or open the attachment. Word (.docx), plain text,
   Markdown, RTF and HTML are read in the page. A PDF has to be pasted as
   text; the app says so rather than failing quietly.
2. **Confirm the header.** Anything the parser could not find is left empty,
   never guessed. Warnings appear under the fields.
3. **Remarks.** The draft follows the house element order. It is a starting
   point, not a finished block.
4. **Ratings.** All eleven rows default to Meets Standard. Any other grade
   needs a written explanation in remarks; the app will not write it.
5. **Generate**, then save.

## What the generator does to the PDF

- Values are drawn into the page content, not left in widget annotations, so
  the form displays and prints the same in Quick Look, mail clients and
  Acrobat. An unflattened form looks completely blank in several viewers.
- Filled widgets are hidden and locked; all 50 page-1 boxes are made
  read-only so a grade cannot be changed downstream.
- Both signature fields are left empty, unlocked and `/F 4`, and the document
  keeps `/SigFlags 3`, so it is still signable in Acrobat.
- Order of operations: generate, then sign. Signing comes last because
  regenerating rewrites the whole file and would invalidate a signature
  already applied.

## Files

| File | What it is |
|---|---|
| `index.html` | The app. Built from `../app/index.html`, do not edit directly. |
| `build.py` | Builds `index.html` from the single source page. |
| `sw.js` | Service worker. Caches everything for offline use. |
| `manifest.webmanifest` | Makes it installable. |
| `short_form_blank.pdf` | The blank template: 84 fields, two signature fields, `/SigFlags 3`. |
| `pdf-lib.min.js` | Vendored (1.17.1) so the app works offline. |
| `jszip.min.js` | Vendored (3.10.1), reads the .docx. |
| `icon-*.png` | Home screen icons. |

### After changing the app

```
python3 build.py          # regenerate index.html
```

Then bump `CACHE` in `sw.js`, or installed copies keep serving the old
version from cache.

### The template

The correct blank has **84 fields including two signature fields and
`/SigFlags 3`**. A copy with 82 fields and no signature fields is the stale
version and will produce a form that cannot be signed. Fields are located by
page position, not by internal field name, because copies of this form in
circulation use different names for the same boxes.

## Known limits

- **PDF attachments** are not read. Open the PDF, select the text and paste.
- **iOS home screen downloads.** An installed web app on iOS sometimes
  previews a generated file instead of saving it
  ([WebKit 275288](https://bugs.webkit.org/show_bug.cgi?id=275288)). An
  **Open in a tab** button appears in standalone mode as a way round it: the
  PDF opens in Safari, where the share sheet saves or mails it normally.
- **The roster lives in this browser only** (`localStorage`). It is not
  synced and not in the repo, which is deliberate: it is personnel data.

## Privacy

Keep this repository free of real summaries and filled forms. They are
personnel records. The blank template and the code are not.

## Why the hosted copy carries no names

A GitHub Pages site is reachable by anyone with the URL, even when the
repository is private
([GitHub docs](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)).
So `build.py` strips the roster and the evaluator details out of the hosted
page and replaces the worked example with an invented one. It refuses to
write the file at all if a real name survives.

Fill both in on the device, once:

- **Your details (evaluator)** in section 2: rank, assignment, and the
  surname used to sign the reply email.
- **Save to roster** adds each candidate's permanent assignment as they
  rotate through.

Both live in that browser's `localStorage`. Neither is in the repository,
and neither syncs between devices, so they are entered once per phone or
laptop.
