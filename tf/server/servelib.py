"""
# Common Server Related Functions

## About

Here are functions that are being used by various parts of the
TF browser infrastructure, such as

* `tf.server.kernel`
* `tf.server.web`
* `tf.server.start`
"""

import json
from io import BytesIO
from zipfile import ZipFile

from ..capable import Capable
from ..parameters import ZIP_OPTIONS


Cap = Capable("browser")
request = Cap.loadFrom("flask", "request")


DEFAULT_NAME = "default"

BATCH = 20


def getInt(x, default=1):
    if len(x) > 15:
        return default
    if not x.isdecimal():
        return default
    return int(x)


def getFormData(interfaceDefaults):
    """Get form data.

    The TF browser user interacts with the web app by clicking and typing,
    as a result of which a HTML form gets filled in.
    This form as regularly submitted to the web server with a request
    for a new incarnation of the page: a response.

    The values that come with a request, must be peeled out of the form,
    and stored as logical values.

    Most of the data has a known function to the web server,
    but there is also a list of webapp dependent options.
    """

    if not Cap.can("browser"):
        return {}

    form = {}
    jobName = request.form.get("jobName", "").strip()
    form["resetForm"] = request.form.get("resetForm", "")
    if jobName:
        form["jobName"] = jobName
        form["loadJob"] = ""
    else:
        form["jobName"] = DEFAULT_NAME
        form["loadJob"] = "1"
        form["resetForm"] = "1"
    form["query"] = request.form.get("query", "").replace("\r", "")
    form["messages"] = request.form.get("messages", "") or ""
    form["features"] = request.form.get("features", "") or ""
    form["tuples"] = request.form.get("tuples", "").replace("\r", "")
    form["sections"] = request.form.get("sections", "").replace("\r", "")
    form["appName"] = request.form.get("appName", "")
    form["jobName"] = request.form.get("jobName", "").strip() or DEFAULT_NAME
    form["side"] = request.form.get("side", "")
    form["dstate"] = request.form.get("dstate", "")
    form["author"] = request.form.get("author", "").strip()
    form["title"] = request.form.get("title", "").strip()
    form["description"] = request.form.get("description", "").replace("\r", "")
    form["forceEdges"] = request.form.get("forceEdges", None)
    form["hideTypes"] = request.form.get("hideTypes", None)
    form["condensed"] = request.form.get("condensed", "")
    form["baseTypes"] = tuple(request.form.getlist("baseTypes"))
    form["hiddenTypes"] = tuple(request.form.getlist("hiddenTypes"))
    form["edgeFeatures"] = tuple(request.form.getlist("edgeFeatures"))
    form["condenseType"] = request.form.get("condenseType", "")
    form["textFormat"] = request.form.get("textFormat", "")
    form["sectionsExpandAll"] = request.form.get("sectionsExpandAll", "")
    form["tuplesExpandAll"] = request.form.get("tuplesExpandAll", "")
    form["queryExpandAll"] = request.form.get("queryExpandAll", "")
    form["passageOpened"] = request.form.get("passageOpened", "")
    form["sectionsOpened"] = request.form.get("sectionsOpened", "")
    form["tuplesOpened"] = request.form.get("tuplesOpened", "")
    form["queryOpened"] = request.form.get("queryOpened", "")
    form["mode"] = request.form.get("mode", "") or "passage"
    form["position"] = getInt(request.form.get("position", ""), default=1)
    form["batch"] = getInt(request.form.get("batch", ""), default=BATCH)
    form["sec0"] = request.form.get("sec0", "")
    form["sec1"] = request.form.get("sec1", "")
    form["sec2"] = request.form.get("sec2", "")
    form["s0filter"] = request.form.get("s0filter", "")

    colorMap = {}
    colorMapN = getInt(request.form.get("colormapn", ""), default=0)

    for i in range(1, colorMapN + 1):
        colorKey = f"colormap_{i}"
        color = request.form.get(colorKey, "")
        colorMap[i] = color

    form["colorMap"] = colorMap

    edgeHighlights = {}
    eColorMapN = getInt(request.form.get("ecolormapn", ""), default=0)

    for i in range(1, eColorMapN + 1):
        color = request.form.get(f"ecolormap_{i}", "")
        name = request.form.get(f"edge_name_{i}", "")
        fRep = request.form.get(f"edge_from_{i}", "")
        tRep = request.form.get(f"edge_to_{i}", "")
        if name == "" or fRep == "" or tRep == "":
            continue
        f = (
            0
            if fRep == ""
            else None
            if fRep == "all"
            else int(fRep)
            if fRep.isdecimal()
            else 0
        )
        t = (
            0
            if tRep == ""
            else None
            if tRep == "all"
            else int(tRep)
            if tRep.isdecimal()
            else 0
        )
        edgeHighlights.setdefault(name, {})[(f, t)] = color

    for i in range(1, 4):
        color = request.form.get(f"ecolormap_new_{i}", "")
        name = request.form.get(f"edge_name_new_{i}", "")
        fRep = request.form.get(f"edge_from_new_{i}", "")
        tRep = request.form.get(f"edge_to_new_{i}", "")
        if name != "" and fRep != "" and tRep != "":
            f = (
                0
                if fRep == ""
                else None
                if fRep == "all"
                else int(fRep)
                if fRep.isdecimal()
                else 0
            )
            t = (
                0
                if tRep == ""
                else None
                if tRep == "all"
                else int(tRep)
                if tRep.isdecimal()
                else 0
            )
            edgeHighlights.setdefault(name, {})[(f, t)] = color

    form["edgeHighlights"] = edgeHighlights

    for (k, v) in interfaceDefaults.items():
        if v is None:
            continue
        form[k] = request.form.get(k, None)
    return form


def getAbout(colofon, header, provenance, form):
    return f"""
{colofon}

{provenance}

Job: {form['jobName']}

# {form['title']}

## {form['author']}

{form['description']}

## Information requests:

### Sections

```
{form['sections']}
```

### Nodes

```
{form['tuples']}
```

### Search

```
{form['query']}
```
"""


def zipTables(csvs, tupleResultsX, queryResultsX, about, form):
    appName = form["appName"]
    jobName = form["jobName"]

    zipBuffer = BytesIO()
    with ZipFile(zipBuffer, "w", **ZIP_OPTIONS) as zipFile:

        zipFile.writestr("job.json", json.dumps(form).encode("utf8"))
        zipFile.writestr("about.md", about)
        if csvs is not None:
            for (csv, data) in csvs:
                contents = "".join(
                    ("\t".join(str(t) for t in tup) + "\n") for tup in data
                )
                zipFile.writestr(f"{csv}.tsv", contents.encode("utf8"))
            for (name, data) in (
                ("nodesx.tsv", tupleResultsX),
                ("resultsx.tsv", queryResultsX),
            ):
                if data is not None:
                    contents = "\ufeff" + "".join(
                        ("\t".join("" if t is None else str(t) for t in tup) + "\n")
                        for tup in data
                    )
                    zipFile.writestr(name, contents.encode("utf_16_le"))
    return (f"{appName}-{jobName}.zip", zipBuffer.getvalue())
