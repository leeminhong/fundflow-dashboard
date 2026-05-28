# Fundflow Dashboard

Daily fundflow heatmap dashboard built as a static website.

## Files for GitHub Pages

- `index.html` - page shell
- `styles.css` - dashboard styling
- `app.js` - filters, heatmap, and trend chart
- `data/fundflow.json` - normalized web data

## Update Data

After updating the Excel source file locally, regenerate the web JSON:

```bash
python3 scripts/extract_fundflow_source.py
python3 scripts/build_web_data.py
```

Then commit and push:

```bash
git add data/fundflow.json
git commit -m "Update fundflow data"
git push
```

## Local Preview

```bash
python3 -m http.server 4173
```

Open:

```text
http://127.0.0.1:4173/
```
