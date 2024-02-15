"""Export to Web Annotation Text Model

# The general idea

This module can export a TF corpus to WATM (Web Annotation Text Model),
which is the input format of the suite of systems developed by Team Text for
serving text plus annotations over the web.

The idea of WATM is, like the idea of Text-Fabric, to untangle the text from its
markup. Everything outside the text itself is coded in annotations.

Annotations look a lot like TF features, but they are a bit more general.
Annotations can also annotate annotations, not only pieces of text.

We need this extra generality, because unlike TF, WATM does not have a concept
of node. The only parallel are the slot nodes of TF, which corresponds to the
tokens of the text in WATM.

Every node in TF is linked to a set of slot nodes.
As such it can be mapped to an annotation to the corresponding tokens.
Features of such nodes can be mapped to annotations to annotations.

TF also has edges. These can be mapped to WATM annotations whose targets are
pairs: one for the thing the edge is *from*, and one for the thing the edge is *to*.
These things are typical annotations that correspond to TF nodes, since TF edges
are links between TF nodes.

If the TF dataset itself is the result of converting an XML file (e.g TEI or
PageXML), then there is a further correspondence between the XML and the TF:

*   elements translate into nodes; element tags translate into node types;
*   attributes translate into features; values of attributes translate into
    values of features.

In our terminology below we assume that the TF data comes from XML files,
but this is not essential. Whenever we talk about *elements* and *tags*,
you may read *nodes* and *node types* if the TF dataset does not have an XML
precursor. Likewise, for *attributes* you may read *features*.

# The specifics

We generate tokens and annotations out of a TF dataset. Here is what we deliver
and in
what form:

*   a bunch of files `text-0.json`, `text-1.json`: with the text segments in an array;
    Each file corresponds with a top-level section in the TF dataset;
*   a bunch of files `anno-1.json`, `anno-2.json, ...: all generated annotations;
    We pack at most 400,000 annotations in one file, that keeps their size
    below 50MB,
    so that they still can live in a git directory without large file support.

## Format of the text files

A `text-i.json` is a JSON file with the following structure:

```
{
  "_ordered_segments": [
    "token1 ",
    "token2 ",
    ...
  ]
}
```
*   each item in `_ordered_segments` corresponds to one token;
*   the item contains the text of the token plus the subsequent whitespace, if any;
*   if the corpus is converted from TEI, we skip all material inside the
    TEI-header.

### Tokens

Tokens correspond to the slot nodes in the TF dataset.
Depending on the original format of the corpus we have the following specifics.

#### TEI corpora

The base type is `t`, the *atomic* token.
Atomic tokens are tokens as they come from some NLP processing, except when tokens
contain element boundaries. In those cases tokens are split in fragments
between the element boundaries.

It is guaranteed that a text segment that corresponds to a `t` does not contain
element boundaries.

The original, unsplit tokens are also present in the annotations, they have
type `token`.

Tokens have the attributes `str` and `after`, both may be empty.

#### PageXML corpora

The base type is `token`, it is available without NLP processing.

Tokens have the attributes `str` and `after`, both may be empty.
They may also have the attributes `rstr` and `rafter`.

*   `str` is the *logical* string value of a token, `after` is empty or a space:
    what comes after the token before the next token.
*   `rstr` is the raw string value of a token, **when it deviates from the
    logical value**, otherwise no value. `rafter` analogously.

**Example**

token | 1 | 2 | 3 | 4 | 5
--- | --- | --- | --- | --- | ---
rstr | empty | `efflagitan` | `¬` | `do` | empty
str | `improbè` | `efflagitando` | empty | empty | `tandem`

## Format of the annotation files

The `anno-1.json`, `anno-2.json`, ... files are JSON file with the following
structure:

```
{
 "a000nnn": [
  "kind",
  "namespace",
  "body",
  "target"
 ],{
 ...
}
```

It is a big dictionary, keyed by annotation ids and each value is the data of
an annotation, divided in the following fields:

*   `kind`: the kind of annotation:
    *   `element`: targets the text location where an *element* occurs, the body
        is the element name;
    *   `pi`: targets the text location where a *processing instruction* occurs,
        the body is the  target of the *pi*;
    *   `attribute`: targets an annotation (an *element* or *pi*), the body has
        the shape *name*`=`*value*,
        the name and value of the attribute in question;
    *   `node`: targets an individual *token* or *element* or *pi*,
        the body is the TF node (a number) of that *token* / *element* / *pi*;
    *   `edge`: targets two node annotations, the body has the shape
        `*name* or `*name*`=`*value*,
        where *name* is the name of the edge and *value* is the label of the edge
        if the edge has a label;
    *   `format`: targets an individual token, the body is a formatting property
        for that token,
        all tokens in note elements get a `format` annotation with body `note`;
    *   `anno`: targets an arbitrary annotation or text range,
        body has an arbitrary value;
        can be used for extra annotations,
        e.g. in the Mondriaan corpus to provide an URL to an artwork derived
        from an `<rs>` element.

*   `namespace`: the namespace of the annotation; an indicator where the
    information comes from. Possible values:
    *   `pagexml`: annotation comes from the PageXML, possibly indirectly, e.g.
        `h`, `w`, `x`, `y`
    *   `tei`: annotation comes
        [literally](https://annotation.github.io/text-fabric/tf/convert/helpers.html#tf.convert.helpers.CM_LIT)
        from the TEI guidelines or the PageXML specification, or is
        [processed](https://annotation.github.io/text-fabric/tf/convert/helpers.html#tf.convert.helpers.CM_LITP)
        straightforwardly from it;
    *   `tf`: annotation is
        [composed](https://annotation.github.io/text-fabric/tf/convert/helpers.html#tf.convert.helpers.CM_LITC)
        in a more intricate way from the original source or even
        [added](https://annotation.github.io/text-fabric/tf/convert/helpers.html#tf.convert.helpers.CM_PROV)
        to it;
    *   `nlp`: annotation is generated as a result of
        [NLP processing](https://annotation.github.io/text-fabric/tf/convert/helpers.html#tf.convert.helpers.CM_NLP);
    *   `tt`: annotation is derived from other material in the source for the benefit
        of the Team Text infrastructure. Defined in the `watm.yaml` file next
        to this program.
        Currently used for annotations that derive from project specific
        requirements.

*   `body`: the body of an annotation (probably the *kind* and *body* fields
    together will make up the body of the resulting web annotation);

*   `target`: a string specifying the target of the annotation, of the
    following kinds:

    *   **single** this is a target pointing to a single thing, either:
        *   `fn:bbb-eee` a range of text segments in the `_ordered_segments`
            in the file `text-fn.json`;

            **N.B.**: we will not have targets that span accross more than one
            `text-i.json` file;
        *   an annotation id

    *   **double** this is a target pointing to two things:
        *   `fff->ttt` where `fff` is a "from" target and `ttt` is a "to" target;
            both targets can vary independently between a range and an annotation id.

            **N,B.** It is allowed that `fff` and `ttt` target segments in distinct
            `text-i.json` files.

# Caveat

The WATM representation of the corpus is a faithful and complete representation
of the TF dataset and hence of the TEI/PageXML source from which the TF dataset has been
converted.

Well, don't take this too literally, probably there are aspects where the
different representations differ.

I am aware of the following:

*   The TEI to TF conversion has lost the exact embedding of elements in the
    following case:

    Suppose element A contains the same words as element B. Then the TF data
    does not know whether A is a child of B or the other way round.

    This is repairable by adding parenthood edges between nodes when
    constructing the TF data. We should then also convert these TF edges to
    WATM annotations, for which we need structured targets:

    If `n` is the parent of `m`, we must make an annotation with body
    `"parent"` and target `[n, m]`.

    Something similar holds for the sibling relationship: if two nodes are adjacent
    in a TF dataset, we do not know whether they are siblings elements in the
    original XML. It is also possible to add sibling edges to the TF dataset.

    See `tf.convert.tei` under **parentEdges** and **siblingEdges**.

*   The TF to WATM conversion forgets the types of feature values: it does not
    make a distinction between the integer `1` and the string `"1"`.

    This is repairable by creating annotations with structured bodies like
    `{"att": value}` instead of strings like `att=value` as we do now.

    In practice, the meaning of the features in TF are known, and hence the attributes
    in the WATM data, so this is not a blocking problem for now.
"""

import collections
import json
import re

from tf.core.helpers import console
from tf.core.files import initTree, dirContents, expanduser as ex
from tf.core.timestamp import DEEP
from tf.parameters import OTYPE, OSLOTS, URL_TF_DOCS
from tf.app import use


TT_NAME = "watm"

NS_TF = "tf"
NS_PAGEXML = "pagexml"
NS_TEI = "tei"
NS_NLP = "nlp"
NS_TT = "tt"
NS_NONE = "tf"

NS_FROM_OTYPE = dict(
    doc=NS_TF,
    page=NS_TF,
    file=NS_TF,
    folder=NS_TF,
    letter=NS_TF,
    chapter=NS_TF,
    chunk=NS_TF,
    word=NS_TF,
    char=NS_TF,
    token=NS_NLP,
    sentence=NS_NLP,
)
NS_FROM_FEAT = dict(
    otype=NS_TF,
    doc=NS_TF,
    page=NS_TF,
    line=NS_TF,
    after=NS_TF,
    rafter=NS_TF,
    str=NS_TF,
    rstr=NS_TF,
)

KIND_NODE = "node"
KIND_EDGE = "edge"
KIND_ELEM = "element"
KIND_PI = "pi"
KIND_ATTR = "attribute"
KIND_FMT = "format"
KIND_ANNO = "anno"

REL_RE = re.compile(r"""/tf\b""")

TR_SEP_LEVEL = 1


def rep(status):
    """Represent a boolean status for a message to the console.

    Parameters
    ----------
    status: boolean

    Returns
    -------
    string
    """
    return "OK" if status else "XX"


class WATM:
    """The export machinery is exposed as a class, wrapped around a TF dataset."""

    def __init__(self, app, nsOrig, skipMeta=False, extra={}):
        """Wrap the WATM exporter around a TF dataset.

        Given an already loaded TF dataset, we make an inventory of all data
        we need to perform an export to WATM.

        Parameters
        ----------
        app: object
            A loaded TF dataset, as obtained by a call `use(...)`.
            See `tf.app.use`
        nsOrig: string
            A namespace corresponding to the format of the original, pre-Text-Fabric
            representation. For example `tei` for a TEI corpus, `pagexml` for a
            PageXML corpus. The namespace is not related to XML namespaces, it is
            merely a device to categorize the resulting annotations.
        skipMeta: boolean, optional False
            Only relevant for TEI corpora. If True, all material in the TEI Header
            will not be converted to tokens in the text.
            More precisely: all TF slots for which the feature `is_meta` has a true-ish
            value will be skipped. If there is no feature `is_meta` in the dataset,
            the setting of `skipMeta` will have no effect: nothing will be excluded.
        extra: dictionary, optional {}
            The data for extra annotations, which will be generated on the fly under the
            namespace `anno`. The keys are the names of features/attributes, the
            value for each key is a dictionary that maps nodes to values.
        """
        self.app = app
        self.nsOrig = nsOrig
        self.extra = extra
        api = app.api
        F = api.F
        E = api.E
        T = api.T
        sectionTypes = T.sectionTypes

        if len(sectionTypes) == 0:
            console(
                "No section types in corpus. "
                "We need at least one section level for tier-0",
                error=True,
            )
            self.error = True
        else:
            tierType = T.sectionTypes[0]
            console(f"Tier 0 is section level '{tierType}'")
            self.tierType = tierType
            self.error = False

        self.L = api.L
        self.Es = api.Es
        self.F = F
        self.E = E
        self.Fs = api.Fs
        self.slotType = self.F.otype.slotType
        self.otypes = self.F.otype.all
        self.info = app.info
        self.repoLocation = app.repoLocation

        Fall = api.Fall
        Eall = api.Eall
        self.Fall = Fall
        self.Eall = Eall

        excludedFeatures = {OTYPE, OSLOTS, "after", "str"}
        self.nodeFeatures = [f for f in Fall() if f not in excludedFeatures]
        self.edgeFeatures = [f for f in Eall() if f not in excludedFeatures]

        FAllSet = set(Fall())

        self.fotypev = F.otype.v
        self.eoslots = E.oslots.s
        self.emptyv = F.empty.v if "empty" in FAllSet else None
        self.strv = F.str.v if "str" in FAllSet else None
        self.rstrv = F.rstr.v if "rstr" in FAllSet else None
        self.afterv = F.after.v if "after" in FAllSet else None
        self.rafterv = F.rafter.v if "rafter" in FAllSet else None
        is_metav = F.is_meta.v if "is_meta" in FAllSet else None
        self.is_metav = is_metav

        app.dm(f"[WATM exporter docs]({URL_TF_DOCS}/convert/watm.html)")

        if skipMeta and not is_metav:
            console(
                "skipMeta=True has no effect because feature is_meta is not defined.",
                error=True,
            )
            skipMeta = False

        self.skipMeta = skipMeta

    def makeText(self):
        """Creates the text data.

        The text is a list of tokens and will be stored in member `text` in this object.
        Additionally, the mapping from slot numbers in the TF data
        to indices in this list is stored in member `tlFromTf`.
        """
        error = self.error

        if error:
            console("Cannot run because of an earlier error", error=True)

        F = self.F
        L = self.L
        slotType = self.slotType
        tierType = self.tierType
        skipMeta = self.skipMeta

        emptyv = self.emptyv
        strv = self.strv
        rstrv = self.rstrv
        afterv = self.afterv
        rafterv = self.rafterv
        is_metav = self.is_metav

        texts = []
        tlFromTf = {}

        self.texts = texts
        self.tlFromTf = tlFromTf

        for ti, sec0 in enumerate(F.otype.s(tierType)):
            text = []
            texts.append(text)

            for s in L.d(sec0, otype=slotType):
                if skipMeta and is_metav(s):
                    continue

                after = rafterv(s) if rafterv else None

                if after is None:
                    after = afterv(s) if afterv else None

                if after is None:
                    after = ""

                if emptyv and emptyv(s):
                    value = after
                else:
                    string = rstrv(s) if rstrv else None

                    if string is None:
                        string = strv(s) if strv else None

                    if string is None:
                        string = ""

                    value = f"{string}{after}"

                text.append(value)
                t = len(text) - 1
                tlFromTf[s] = (ti, t)

    def mkAnno(self, kind, ns, body, target):
        """Make a single annotation and return its id.

        Parameters
        ----------
        kind: string
            The kind of annotation.
        ns: string
            The namespace of the annotation.
        body: string
            The body of the annotation.
        target: string  or tuple of strings
            The target of the annotation.
        """
        annos = self.annos
        aId = f"a{len(annos):>08}"
        annos.append((kind, aId, ns, body, target))
        return aId

    def makeAnno(self):
        """Make all annotations.

        The annotations are stored in a big list, in member `anno` of this object.

        The mapping from slots to indices in the list of tokens is now extended
        with the mapping from nodes to corresponding node annotations.

        So member `tlFromTf` is now a full mapping from all nodes in TF to
        tokens and/or annotations in WATM.
        """
        error = self.error

        if error:
            console("Cannot run because of an earlier error", error=True)

        Es = self.Es
        F = self.F
        Fs = self.Fs
        fotypev = self.fotypev
        eoslots = self.eoslots
        nodeFeatures = self.nodeFeatures
        edgeFeatures = self.edgeFeatures
        slotType = self.slotType
        otypes = self.otypes
        nsOrig = self.nsOrig
        skipMeta = self.skipMeta
        extra = self.extra

        tlFromTf = self.tlFromTf

        is_metav = self.is_metav

        isTei = nsOrig == NS_TEI

        annos = []
        texts = self.texts
        self.annos = annos

        invertedTargets = []
        farTargets = []

        def mkTarget(n):
            ts = tlFromTf[n]
            return f"{ts[0]}:{ts[1]}-{ts[1] + 1}" if fotypev(n) == slotType else ts

        for otype in otypes:
            isSlot = otype == slotType

            for n in F.otype.s(otype):
                if isSlot:
                    if skipMeta and is_metav(n):
                        continue

                    self.mkAnno(KIND_NODE, NS_TF, n, mkTarget(n))
                else:
                    ws = eoslots(n)
                    if skipMeta and (is_metav(ws[0]) or is_metav(ws[-1])):
                        continue

                    ti0, start = tlFromTf[ws[0]]
                    ti1, end = tlFromTf[ws[-1]]

                    if ti0 != ti1:
                        farTargets.append((otype, ti0, start, ti1, end))
                        continue

                    if end < start:
                        invertedTargets.append((otype, ti0, start, end))
                        start, end = (end, start)

                    target = f"{ti0}:{start}-{end + 1}"
                    aId = (
                        self.mkAnno(KIND_PI, nsOrig, otype[1:], target)
                        if otype.startswith("?")
                        else self.mkAnno(
                            KIND_ELEM, NS_FROM_OTYPE.get(otype, nsOrig), otype, target
                        )
                    )
                    tlFromTf[n] = aId
                    self.mkAnno(KIND_NODE, NS_TF, n, aId)

        for feat in nodeFeatures:
            ns = Fs(feat).meta.get("conversionCode", NS_FROM_FEAT.get(feat, nsOrig))

            if ns is None:
                console(
                    f"Node feature {feat} has no namespace, "
                    f"defaulting to {NS_NONE}",
                    error=True,
                )
                ns = NS_NONE

            isRend = False
            isNote = False

            if isTei:
                parts = feat.split("_", 2)
                isRend = len(parts) >= 2 and parts[0] == "rend"
                isNote = len(parts) == 2 and parts[0] == "is" and parts[1] == "note"

            if isRend or isNote:
                body = parts[1] if isRend else "note"

                for n, val in Fs(feat).items():
                    if not val or (skipMeta and is_metav(n)):
                        continue

                    self.mkAnno(KIND_FMT, ns, body, mkTarget(n))
            else:
                for n, val in Fs(feat).items():
                    if val is None or skipMeta and is_metav(n):
                        continue

                    body = f"{feat}={val}"
                    self.mkAnno(KIND_ATTR, ns, body, mkTarget(n))

        for feat in edgeFeatures:
            ns = Es(feat).meta.get("conversionCode", NS_FROM_FEAT.get(feat, nsOrig))

            if ns is None:
                console(
                    f"Edge feature {feat} has no conversion code, "
                    f"defaulting to {NS_NONE}",
                    error=True,
                )
                ns = NS_NONE

            for fromNode, toNodes in Es(feat).items():
                if skipMeta and is_metav(fromNode):
                    continue

                if fromNode not in tlFromTf:
                    continue

                targetFrom = mkTarget(fromNode)

                if type(toNodes) is dict:
                    for toNode, val in toNodes.items():
                        if skipMeta and is_metav(toNode):
                            continue

                        if toNode not in tlFromTf:
                            continue

                        body = f"{feat}={val}"
                        targetTo = mkTarget(toNode)
                        target = f"{targetFrom}->{targetTo}"
                        self.mkAnno(KIND_EDGE, ns, body, target)
                else:
                    for toNode in toNodes:
                        if skipMeta and is_metav(toNode):
                            continue

                        if toNode not in tlFromTf:
                            continue

                        targetTo = mkTarget(toNode)
                        target = f"{targetFrom}->{targetTo}"
                        self.mkAnno(KIND_EDGE, ns, feat, target)

        for feat, featData in extra.items():
            for n, value in featData.items():
                self.mkAnno(KIND_ANNO, NS_TT, f"{feat}={value}", mkTarget(n))

        if len(invertedTargets):
            console(f"WARNING: inverted targets, {len(invertedTargets)}x")
            for otype, ti0, start, end in invertedTargets:
                text = texts[ti0]
                sega = text[start]
                segb = text[end - 1]
                console(f"{otype:>20} {start:>6} `{sega}` > {end - 1} `{segb}`")

        if len(farTargets):
            console(
                f"ERROR: targets across tier0 items, {len(farTargets)}x",
                error=True,
            )
            for otype, ti0, start, ti1, end in farTargets:
                sega = texts[ti0][start]
                segb = texts[ti1][end - 1]
                console(
                    f"{otype:>20} {ti0:>2}:{start:>6} `{sega}` - "
                    f"{ti1:>2}:{end - 1} `{segb}`"
                )

    def writeAll(self):
        """Write text and annotation data to disk.

        The data will be written as JSON files.
        When the annotation data grows larger than a certain threshold, it will be
        divided over several files.

        The annotations are sorted by annotation id.
        """

        # text files

        error = self.error

        if error:
            console("Cannot run because of an earlier error", error=True)

        app = self.app
        texts = self.texts
        annos = self.annos

        baseDir = self.repoLocation
        relative = app.context.relative
        version = app.version
        wRelative = REL_RE.sub(f"/{TT_NAME}/{version}/", relative, count=1)
        resultDir = f"{baseDir}{wRelative}"

        textFiles = []
        self.textFiles = textFiles

        initTree(resultDir, fresh=True)

        total = 0

        for i, text in enumerate(texts):
            textFile = f"{resultDir}/text-{i}.json"
            textFiles.append(textFile)
            nText = len(text)
            total += nText

            with open(textFile, "w") as fh:
                json.dump(
                    dict(_ordered_segments=text), fh, ensure_ascii=False, indent=1
                )

            console(f"Text file {i:>4}: {nText:>8} segments to {textFile}")

        nTextFiles = len(textFiles)
        sep = "" if nTextFiles == 1 else "s"
        console(f"Text files all: {total:>8} segments to {nTextFiles} file{sep}")

        # annotation files

        annoStore = {}

        for kind, aId, ns, body, target in annos:
            annoStore[aId] = (kind, ns, body, target)

        aIdSorted = sorted(annoStore.keys())

        annoFile = f"{resultDir}/anno.tsv"

        if False:
            with open(annoFile, "w") as fh:
                for aId in aIdSorted:
                    kind, ns, body, target = annoStore[aId]
                    fh.write(f"{aId}\t{kind}\t{ns}\t{body}\t{target}\n")

        thisAnnoStore = {}
        thisA = 1
        annoFiles = []
        self.annoFiles = annoFiles

        LIMIT = 400000
        j = 0
        total = 0

        def writeThis():
            annoFile = f"{resultDir}/anno-{thisA:>01}.json"
            annoFiles.append(annoFile)

            with open(annoFile, "w") as fh:
                json.dump(thisAnnoStore, fh, ensure_ascii=False, indent=1)

            console(f"Anno file {i:>4}: {j:>8} annotations written to {annoFile}")

        for aId in aIdSorted:
            if j >= LIMIT:
                writeThis()
                thisA += 1
                thisAnnoStore = {}
                total += j
                j = 0

            thisAnnoStore[aId] = annoStore[aId]
            j += 1

        if len(thisAnnoStore):
            writeThis()
            total += j

        if len(annos) != total:
            console(f"Sum of batches : {total:>8}")
            console(f"All annotations: {len(annoStore):>8}")
            console("Mismatch in number of annotations", error=True)

        nAnnoFiles = len(annoFiles)
        sep = "" if nAnnoFiles == 1 else "s"
        console(f"Anno files all: {total:>8} annotations to {nAnnoFiles} file{sep}")

    @staticmethod
    def compare(nTF, nWA):
        """Compare two numbers and report the outcome.

        Used for testing the WATM conversion.

        Parameters
        ----------
        nTF: integer
            The number as it is counted from the original TF dataset.
        nWA: integer
            The number as it is counted from the generated WATM dataset.

        Returns
        -------
        boolean
            Whether the two values are equal.
        """
        console(f"\tTF: {nTF:>6}\n\tWA: {nWA:>6}", error=nTF != nWA)
        return nTF == nWA

    @staticmethod
    def strEqual(wa=None, tf=None):
        """Compare two strings and report the outcome.

        Used for testing the WATM conversion.

        Parameters
        ----------
        nTF: string
            The string as encountered in the original TF dataset.
        nWA: string
            The string as encountered in the generated WATM dataset.

        Returns
        -------
        boolean
            Whether the two values are equal.
        """
        different = False

        for i, cTF in enumerate(tf):
            if i >= len(wa):
                contextI = max((0, i - 10))
                console(f"\tWA {i}: {wa[contextI:i]} <END>", error=True)
                console(f"\tTF {i}: {tf[contextI:i]} <> {tf[i:i + 10]}", error=True)
                different = True
                break
            elif tf[i] != wa[i]:
                contextI = max((0, i - 10))
                console(
                    f"\tWA {i}: {wa[contextI:i]} <{wa[i]}> {wa[i + 1:i + 11]}",
                    error=True,
                )
                console(
                    f"\tTF {i}: {tf[contextI:i]} <{tf[i]}> {tf[i + 1:i + 11]}",
                    error=True,
                )
                different = True
                break

        if not different and len(wa) > len(tf):
            i = len(tf)
            contextI = max((0, i - 10))
            console(f"\tWA {i}: {wa[contextI:i]} <> {wa[i:i + 10]}", error=True)
            console(f"\tTF {i}: {tf[contextI:i]} <END>", error=True)
            different = True

        sampleWA = f"{wa[0:20]} ... {wa[-20:]}".replace("\n", " ")
        sampleTF = f"{tf[0:20]} ... {tf[-20:]}".replace("\n", " ")
        console(f"\tTF: {sampleTF:>6}\n\tWA: {sampleWA:>6}")
        return not different

    def testAll(self):
        """Test all aspects of the WATM conversion.

        For all kinds of information, such as nodes, edges, features, tokens,
        annotations, we check whether the parts that should correspond between
        the TF dataset and the WATM annotations do so indeed.

        We present some statistics, and highlight the mismatches.

        Returns
        -------
        boolean
            Whether all things that must agree do indeed agree.
        """
        error = self.error

        if error:
            console("Cannot run because of an earlier error", error=True)

        self.testSetup()

        good = True

        if not self.testText():
            good = False

        if not self.testElements():
            good = False

        if not self.testAttributes():
            good = False

        if not self.testExtra():
            good = False

        if not self.testEdges():
            good = False

        console("Overall outcome ...")
        console(f"{rep(good)} - whether all tests passed", error=not good)

        return good

    def testSetup(self):
        """Prepare the tests.

        We read the WATM dataset and store the tokens in member `testTokens`
        and the annotations in the member `testAnnotations`.
        We unpack targets if they contain structured information.
        """
        textFiles = self.textFiles
        annoFiles = self.annoFiles

        tokenFiles = []

        for textFile in textFiles:
            with open(textFile) as fh:
                text = json.load(fh)
                tokens = text["_ordered_segments"]
                tokenFiles.append(tokens)

        self.testTokens = tokenFiles

        annotations = []

        for annoFile in annoFiles:
            with open(annoFile) as fh:
                annos = json.load(fh)

                for aId, (kind, ns, body, target) in annos.items():
                    if "->" in target:
                        parts = target.split("->", 1)
                    else:
                        parts = [target]

                    newParts = []

                    for part in parts:
                        if "-" in part:
                            file, part = part.split(":", 1)
                            start, end = part.split("-", 1)
                            part = (int(file), int(start), int(end))

                        newParts.append(part)

                    target = newParts[0] if len(newParts) == 1 else tuple(newParts)

                    annotations.append((aId, kind, body, target))

        annotations = sorted(annotations)
        self.testAnnotations = annotations

    def testText(self):
        """Test the text.

        We test the number of tokens and the equality of the resulting text:
        whether the TF and WATM datasets agree on it.

        Returns
        -------
        boolean
            Whether all these tests succeed.
        """
        F = self.F
        skipMeta = self.skipMeta
        is_metav = self.is_metav
        tokenFiles = self.testTokens
        texts = self.texts

        console("Testing the text ...")

        nTokensTF = sum(
            0 if skipMeta and is_metav(s) else 1 for s in range(1, F.otype.maxSlot + 1)
        )
        nTokensWA = sum(len(tokens) for tokens in tokenFiles)
        nGood = self.compare(nTokensTF, nTokensWA)
        console(f"{rep(nGood)} - whether the amounts of tokens agree", error=not nGood)

        textWA = "".join("".join(tokens) for tokens in tokenFiles)
        textTF = "".join("".join(text) for text in texts)

        tGood = self.strEqual(wa=textWA, tf=textTF)
        console(f"{rep(tGood)} - whether the text is the same", error=not tGood)

        return nGood and tGood

    def testElements(self):
        """Test the elements.

        We test the annotations representing elements/processing instructions
        and check whether they correspond 1-1 to the non-slot nodes in the TF
        dataset.

        Returns
        -------
        boolean
            Whether all these tests succeed.
        """
        F = self.F
        fotypev = self.fotypev
        eoslots = self.eoslots
        skipMeta = self.skipMeta
        is_metav = self.is_metav
        annotations = self.testAnnotations

        console("Testing the elements ...")

        nElementsTF = 0
        nPisTF = 0

        for n in range(F.otype.maxSlot + 1, F.otype.maxNode + 1):
            nType = fotypev(n)
            isPi = nType.startswith("?")

            if isPi:
                nPisTF += 1

            slots = eoslots(n)
            b = slots[0]
            e = slots[-1]

            if skipMeta and (is_metav(b) or is_metav(e)):
                continue
            else:
                if not isPi:
                    nElementsTF += 1

        nElementsWA = sum(1 if a[1] == "element" else 0 for a in annotations)
        nPisWA = sum(1 if a[1] == "pi" else 0 for a in annotations)

        eGood = self.compare(nElementsTF, nElementsWA)
        console(
            f"{rep(eGood)} - whether the amounts of elements and nodes agree",
            error=not eGood,
        )

        console("Testing the processing instructions ...")

        pGood = self.compare(nPisTF, nPisWA)
        console(
            f"{rep(pGood)} - whether the amounts of processing instructions agree",
            error=not pGood,
        )

        console("Testing the element annotations ...")

        tfFromAid = {}

        element = 0
        pi = 0
        other = 0
        good = 0
        wrong = 0
        unmapped = 0

        for aId, kind, body, target in annotations:
            if kind == "node":
                tfFromAid[target] = body

        self.tfFromAid = tfFromAid

        console(f"\t{len(tfFromAid)} element annotations")

        for aId, kind, body, target in annotations:
            isElem = kind == "element"
            isPi = kind == "pi"

            if not isElem and not isPi:
                other += 1
                continue

            if isElem:
                element += 1
            else:
                pi += 1

            tag = body
            node = tfFromAid.get(aId, None)
            if node is None:
                unmapped += 1
                continue

            otype = fotypev(node)

            if isPi and tag == otype[1:] or not isPi and tag == otype:
                good += 1
            else:
                wrong += 1

        console(f"\tElement : {element:>5} x")
        console(f"\tPi      : {pi:>5} x")
        console(f"\tOther   : {other:>5} x")
        console(f"\tGood    : {good:>5} x")
        console(f"\tWrong   : {wrong:>5} x")
        console(f"\tUnmapped: {unmapped:>5} x")

        aGood = wrong == 0 and unmapped == 0
        console(
            f"{rep(aGood)} - whether all element annotations are ok", error=not aGood
        )

        return aGood and eGood and pGood

    def testAttributes(self):
        """Test the attributes.

        We test whether attributes and features correspond to each other.

        Some attributes in the original TEI are converted in a special way into
        TF features: this holds for the `rend` attribute.
        Basically, a value `rend="italic"` is translated into feature
        `is_italic=1`.
        In turn, these features have been translated into annotations of kind
        `format`. We test them separately.

        Returns
        -------
        boolean
            Whether all these tests succeed.
        """
        Fs = self.Fs
        Fall = self.Fall
        eoslots = self.eoslots
        skipMeta = self.skipMeta
        is_metav = self.is_metav
        annotations = self.testAnnotations
        tfFromAid = self.tfFromAid
        nsOrig = self.nsOrig

        isTei = nsOrig == NS_TEI

        console("Testing the attributes ...")

        attWA = []

        for aId, kind, body, target in annotations:
            if kind != "attribute":
                continue
            node = tfFromAid[target]
            att, value = body.split("=", 1)
            attWA.append((node, att, value))

        attWA = sorted(attWA)

        console(f"\t{len(attWA)} attribute values")

        good = 0
        wrong = []

        for node, att, valWA in attWA:
            valTF = str(Fs(att).v(node))
            if valWA == valTF:
                good += 1
            else:
                wrong.append((node, att, valWA, valTF))

        console(f"\tGood:     {good:>5} x")
        console(f"\tWrong:    {len(wrong):>5} x")
        consistent = len(wrong) == 0

        console(
            f"{rep(consistent)} - whether annotations are consistent with features",
            error=not consistent,
        )

        attTF = []

        for feat in Fall():
            if feat in {"otype", "str", "after"}:
                continue

            if skipMeta and feat == "is_meta":
                continue

            if isTei and (
                (feat != "is_meta" and feat.startswith("is_"))
                or feat.startswith("rend_")
            ):
                continue

            for node, valTF in Fs(feat).items():
                slots = eoslots(node)
                b = slots[0]
                e = slots[-1]

                if skipMeta and (is_metav(b) or is_metav(e)):
                    continue

                attTF.append((node, feat, str(valTF)))

        attTF = sorted(attTF)

        console(f"\tWA attributes: {len(attWA)}")
        console(f"\tTF attributes: {len(attTF)}")
        complete = attTF == attWA
        console(
            f"{rep(complete)} - whether annotations are complete w.r.t. features",
            error=not complete,
        )

        console("Testing the format attributes ...")

        fmtWA = []

        for aId, kind, body, target in annotations:
            if kind != "format":
                continue
            if body == "note":
                continue
            node = tfFromAid[target]
            fmtWA.append((node, body))

        fmtWA = sorted(fmtWA)
        fmtWaFreq = collections.Counter()

        for node, body in fmtWA:
            fmtWaFreq[body] += 1

        console(f"\t{len(fmtWA)} format values")
        console("\tformatting attributes: ")
        for fa, n in sorted(fmtWaFreq.items(), key=lambda x: (-x[1], x[0])):
            console(f"\t\t{n:>6} x {fa}")

        good = 0
        wrong = []

        for node, valWA in fmtWA:
            feat = f"rend_{valWA}"
            valTF = valWA if str(Fs(feat).v(node)) else None
            if valWA == valTF:
                good += 1
            else:
                wrong.append((node, feat, valWA, valTF))

        console(f"\tGood:     {good:>5} x")
        console(f"\tWrong:    {len(wrong):>5} x")
        fconsistent = len(wrong) == 0
        console(
            f"{rep(fconsistent)} - "
            f"whether format annotationsare consistent with features",
            error=not fconsistent,
        )

        fmtTF = []

        for feat in Fall():
            if not feat.startswith("rend_"):
                continue

            value = feat.split("_", 2)[1]
            if value == "note":
                continue

            for node, valTF in Fs(feat).items():
                slots = eoslots(node)
                b = slots[0]
                e = slots[-1]

                if skipMeta and (is_metav(b) or is_metav(e)):
                    continue

                fmtTF.append((node, value))

        fmtTF = sorted(fmtTF)

        console(f"\tWA format attributes: {len(fmtWA)}")
        console(f"\tTF format attributes: {len(fmtTF)}")
        fcomplete = fmtTF == fmtWA
        console(
            f"{rep(complete)} - "
            f"whether format annotations are complete w.r.t. features",
            error=not fcomplete,
        )

        return consistent and complete and fconsistent and fcomplete

    def testExtra(self):
        """Test the extra data for on-the-fly annotations.

        Annotations that have been generated out of the data stored in the
        `extra` parameter with which the object has been initialized, all got
        the kind `anno`.

        Now we check these annotations against the data that went into it.

        Returns
        -------
        boolean
            Whether all these tests succeed.
        """
        annotations = self.testAnnotations
        tfFromAid = self.tfFromAid
        extra = self.extra

        console("Testing the extra annotations ...")

        attWA = []

        for aId, kind, body, target in annotations:
            if kind != "anno":
                continue
            node = tfFromAid[target]
            att, value = body.split("=", 1)
            attWA.append((node, att, value))

        attWA = sorted(attWA)

        attEX = []

        for feat, featData in extra.items():
            for n, value in featData.items():
                attEX.append((n, feat, value))

        attEX = sorted(attEX)

        console(f"\t{len(attEX)} extra feature values")
        console(f"\t{len(attWA)} extra annotations")

        good = attWA == attEX

        def showData(tuples, isin, isout):
            data = {}

            for n, f, v in tuples:
                data.setdefault(f, {})[n] = v

            for f in sorted(data):
                fData = data[f]
                console(
                    f"\t{isin}: {f} misses {len(fData)} annotations in {isout}",
                    error=True,
                )
                for n in sorted(fData.keys())[0:3]:
                    console(f"\t\t\t{n:>7} = {fData[n]}", error=True)

        if not good:
            attWASet = set(attWA)
            attEXSet = set(attEX)

            onlyWA = attWASet - attEXSet
            onlyEX = attEXSet - attWASet

            if len(onlyWA):
                showData(onlyWA, "WA", "EX")
            else:
                console("\tWA: All extra annotations derive from the extra data")
            if len(onlyEX):
                showData(onlyEX, "EX", "WA")
            else:
                console("\tEX: All extra data ended up as annotations")

        console(f"{rep(good)} - whether the extra annotations agree", error=not good)

        return good

    def testEdges(self):
        """Test the edges.

        Edges in TF are links between nodes, and they translate into annotations of
        kind `edge` which target a pair of annotations: the `from` annotation,
        and the `to` annotation.

        Here we check whether the TF edges are faithfully and completely parallelled
        by annotations.

        Returns
        -------
        boolean
            Whether all these tests succeed.
        """
        Es = self.Es
        Eall = self.Eall
        annotations = self.testAnnotations

        console("Testing the edges ...")

        tfFromWANodes = {}
        tfFromWAEdges = {}

        for aId, kind, body, target in annotations:
            if kind != "node":
                continue
            if type(target) is tuple:
                file, start, end = target
                if start + 1 != end:
                    # we expect that node annotations either targets a single token
                    # or an element/pi annotation
                    print(target)
                    break
                target = (file, end)
            tfFromWANodes[target] = body

        for aId, kind, body, target in annotations:
            if kind != "edge":
                continue

            fro, to = target
            fromNode = tfFromWANodes[fro]
            toNode = tfFromWANodes[to]
            parts = body.split("=", 1)
            name, val = (body, None) if len(parts) == 1 else parts
            tfFromWAEdges.setdefault(name, {}).setdefault(fromNode, {})[toNode] = val

        console(f"\tFound: {len(tfFromWANodes)} nodes")

        for edge, edgeData in sorted(tfFromWAEdges.items()):
            console(f"\tFound edge {edge} with {len(edgeData)} starting nodes")

        allGood = True

        for edge in set(Eall()) | set(tfFromWAEdges):
            if edge == "oslots":
                continue

            console(f"\tChecking edge {edge}")

            good = True

            if edge not in set(Eall()):
                console("\t\tmissing in TF data", error=True)
                good = False

            if edge not in tfFromWAEdges:
                console("\t\tmissing in annotation data", error=True)
                good = False

            if not good:
                continue

            dataTF = dict(Es(edge).items())
            dataWA = tfFromWAEdges[edge]

            fromNodesTF = set(dataTF)
            fromNodesWA = set(dataWA)

            nFromTF = len(fromNodesTF)
            nFromWA = len(fromNodesWA)

            if fromNodesTF == fromNodesWA:
                console(f"\t\tsame {nFromTF} fromNodes")
            else:
                console(
                    f"\t\tfrom nodes differ: {nFromTF} in TF, {nFromWA} in WA",
                    error=True,
                )
                good = False

            diffs = []

            nToChecked = 0

            for f, toNodeInfoTF in dataTF.items():
                toNodeInfoWA = dataWA[f]
                if type(toNodeInfoTF) is dict:
                    toNodeInfoTF = {k: str(v) for (k, v) in toNodeInfoTF.items()}
                else:
                    toNodeInfoTF = {x: None for x in toNodeInfoTF}

                if toNodeInfoTF != toNodeInfoWA:
                    diffs.append((f, toNodeInfoTF, toNodeInfoWA))

                nToChecked += len(toNodeInfoTF)

            if len(diffs):
                good = False
                console(
                    f"\t\tdifferences in toNodes for {len(diffs)} fromNodes", error=True
                )

                for f, toNodeInfoTF, toNodeInfoWA in sorted(diffs)[0:10]:
                    console(f"\t\t\tfromNode {f}", error=True)

                    toNodesTF = set(toNodeInfoTF)
                    toNodesWA = set(toNodeInfoWA)

                    nToTF = len(toNodesTF)
                    nToWA = len(toNodesWA)

                    if toNodesTF == toNodesWA:
                        console(f"\t\t\tsame {nToTF} toNodes")
                    else:
                        console(
                            f"\t\t\ttoNodes differ: {nToTF} in TF, {nToWA} in WA",
                            error=True,
                        )
                    for t in toNodesTF | toNodesWA:
                        doCompare = True
                        if t not in toNodesTF:
                            console(f"\t\t\t\ttoNode {t} not in TF", error=True)
                            doCompare = False
                        else:
                            valTF = toNodeInfoTF[t]

                        if t not in toNodesWA:
                            console(f"\t\t\t\ttoNode {t} not in WA", error=True)
                            doCompare = False
                        else:
                            valWA = toNodeInfoWA[t]

                        if doCompare:
                            if valTF == valWA:
                                console(
                                    f"\t\t\t\ttoNode{t} values agree: {repr(valTF)}"
                                )
                            else:
                                console(
                                    f"\t\t\t\ttoNode{t} values differ: "
                                    f"TF: {repr(valTF)} WA: {repr(valWA)}",
                                    error=True,
                                )

            console(f"\t{rep(good)} - {nToChecked} toNodes checked", error=not good)

            if not good:
                allGood = False

        console(f"{rep(allGood)} - whether all edges agree")

        return allGood


class WATMS:
    """Export corpora that are divided over multiple TF datasets.

    We set up and run WATM objects for each TF dataset, and generate results
    for them separately.

    We assume that all corpora have been generated by the same method and originate
    from the same original format.

    They must reside in the same repository, in adjacent directories under the `tf`
    top-level directory of the repo.
    """

    def __init__(self, org, repo, backend, nsOrig, skipMeta=False, extra={}):
        """Collect the parameters for the WATM machinery.

        We will initialize many `WATM` objects with mostly the same parameters.
        These are collected when we initialize this object.

        Parameters
        ----------
        org: string
            The organization of all TF datasets.
        repo: string
            The repo of all TF datasets.
        backend: string
            The backend of all TF datasets.
        nsOrig: string
            The original namespace of all TF datasets.
            See `tf.convert.watm.WATM`.
        skipMeta: boolean, optional False
            See `tf.convert.watm.WATM`.
        extra: dictionary, optional {}
            See `tf.convert.watm.WATM`.
        """
        self.org = org
        self.repo = repo
        self.backend = backend
        self.nsOrig = nsOrig
        self.skipMeta = skipMeta
        self.extra = extra

        repoDir = ex(f"~/{backend}/{org}/{repo}")
        tfDir = f"{repoDir}/tf"
        docs = dirContents(tfDir)[1]
        console(f"Found {len(docs)} docs in {tfDir}")
        self.docs = docs

    def produce(self, doc=None):
        """Convert all relevant TF datasets.

        Parameters
        ----------
        doc: string, optional None
            Subdirectory where one of the TF datasets resides.
            If passed, only this dataset will be converted.
            Otherwise all datasets will be converted.
        """
        org = self.org
        repo = self.repo
        backend = self.backend
        nsOrig = self.nsOrig
        skipMeta = self.skipMeta
        extra = self.extra
        docs = self.docs

        chosenDoc = doc

        for doc in sorted(docs, key=lambda x: (x[0], int(x[1:]))):
            if chosenDoc is not None and chosenDoc != doc:
                continue

            console(f"{doc:>5} ... ", newline=False)
            A = use(
                f"{org}/{repo}:clone",
                relative=f"tf/{doc}",
                checkout="clone",
                backend=backend,
                silent=DEEP,
            )
            WA = WATM(A, nsOrig, skipMeta=skipMeta, extra=extra)
            WA.makeText()
            WA.makeAnno()
            WA.writeAll()
