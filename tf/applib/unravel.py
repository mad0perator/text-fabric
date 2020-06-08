"""
.. include:: ../../docs/applib/unravel.md
"""

from itertools import chain
from ..core.helpers import rangesFromList, console
from .highlight import getHlAtt
from .displaylib import (
    NodeContext,
    OuterContext,
    _getBigType,
    _getLtr,
    _getTextCls,
    QUAD,
)


def _unravel(app, isPretty, dContext, n, _inTuple=False, explain=False):
    """Unravels a node in a tree of fragments dressed up with formatting properties.
    """

    api = app.api
    N = api.N
    E = api.E
    F = api.F
    Fs = api.Fs
    L = api.L
    T = api.T

    sortKeyChunk = N.sortKeyChunk
    sortKeyChunkLength = N.sortKeyChunkLength
    eOslots = E.oslots.s
    fOtype = F.otype
    fOtypeV = fOtype.v
    fOtypeAll = fOtype.all
    slotType = fOtype.slotType
    nType = fOtypeV(n)

    aContext = app.context
    verseTypes = aContext.verseTypes
    lexTypes = aContext.lexTypes
    descendantType = aContext.descendantType
    exclusions = aContext.exclusions
    showVerseInTuple = aContext.showVerseInTuple
    levelCls = aContext.levelCls
    prettyCustom = aContext.prettyCustom
    styles = aContext.styles
    formatHtml = aContext.formatHtml
    hasGraphics = aContext.hasGraphics
    afterChild = aContext.afterChild

    full = dContext.full
    hideTypes = dContext.hideTypes
    baseTypes = dContext.baseTypes
    hiddenTypes = dContext.hiddenTypes
    highlights = dContext.highlights
    fmt = dContext.fmt
    dContext.isHtml = fmt in formatHtml
    ltr = _getLtr(app, dContext)
    textCls = _getTextCls(app, fmt)
    descendType = T.formats.get(fmt, slotType)

    startCls = "r" if ltr == "rtl" else "l"
    endCls = "l" if ltr == "rtl" else "r"

    nSlots = eOslots(n)
    if nType in lexTypes:
        nSlots = (nSlots[0],)
    nSlots = set(nSlots)
    isBigType = (
        _inTuple
        if not isPretty and nType in verseTypes and not showVerseInTuple
        else _getBigType(app, isPretty, dContext, nType)
    )

    subBaseTypes = set()

    if baseTypes and baseTypes != {slotType}:
        for bt in baseTypes:
            if bt in descendantType:
                subBaseTypes |= descendantType[bt]

    oContext = OuterContext(slotType, ltr, fmt, textCls)

    nodeInfo = {}

    def distillChunkInfo(m, chunkInfo):
        """Gather all the dressing info for a chunk.
        """

        mType = fOtypeV(m)
        isSlot = mType == slotType
        (hlCls, hlStyle) = getHlAtt(app, m, highlights, isSlot, not isPretty)
        cls = {}
        if isPretty:
            if mType in levelCls:
                cls.update(levelCls[mType])
            if mType in prettyCustom:
                prettyCustom[mType](app, m, mType, cls)
        textCls = styles.get(mType, oContext.textCls)
        isBaseNonSlot = not isSlot and (mType in baseTypes or mType in subBaseTypes)
        nodeInfoM = nodeInfo.setdefault(
            m,
            NodeContext(
                mType,
                isSlot,
                isSlot or mType == descendType,
                False if descendType == mType or mType in lexTypes else None,
                isBaseNonSlot,
                textCls,
                hlCls,
                hlStyle,
                cls,
                mType in hasGraphics,
                afterChild.get(mType, None),
            ),
        )
        chunkInfo.update(
            dContext=dContext,
            oContext=oContext,
            nContext=nodeInfoM,
            boundaryCls=chunkBoundaries[chunk],
        )

    # determine intersecting nodes

    if isBigType and not full:
        iNodes = set()
    elif nType in descendantType:
        myDescendantType = descendantType[nType]
        iNodes = set(L.i(n, otype=myDescendantType))
    elif nType in lexTypes:
        iNodes = {n}
    else:
        iNodes = set(L.i(n))

    if hideTypes:
        iNodes -= set(m for m in iNodes if fOtypeV(m) in hiddenTypes)

    iNodes.add(n)

    # chunkify all nodes and determine all true boundaries:
    # of nodes and of their maximal contiguous chunks

    chunks = {}
    boundaries = {}

    for m in iNodes:
        mType = fOtypeV(m)
        if mType in exclusions:
            skip = False
            conditions = exclusions[mType]
            for (feat, value) in conditions.items():
                if Fs(feat).v(m) == value:
                    skip = True
                    break
            if skip:
                continue

        slots = eOslots(m)
        if nType in lexTypes:
            slots = (slots[0],)
        if m != n and mType == nType and nSlots <= set(slots):
            continue
        ranges = rangesFromList(slots)
        bounds = {}
        minSlot = min(slots)
        maxSlot = max(slots)

        # for each node m the boundaries value is a dict keyed by slots
        # and valued by a tuple: (left bound, right bound)
        # where bound is:
        # None if there is no left resp. right boundary there
        # True if the left resp. right node boundary is there
        # False if a left resp. right inner chunk boundary is there

        for r in ranges:
            (b, e) = r
            chunks.setdefault(mType, set()).add((m, r))
            bounds[b] = ((b == minSlot), (None if b != e else e == maxSlot))
            bounds[e] = ((b == minSlot if b == e else None), (e == maxSlot))
        boundaries[m] = bounds

    # fragmentize all chunks

    typeLen = len(fOtypeAll) - 1  # exclude the slot type

    for (p, pType) in enumerate(fOtypeAll):
        pChunks = chunks.get(pType, ())
        if not pChunks:
            continue

        # fragmentize nodes of the same type, largest first

        splits = {}

        pChunksLen = len(pChunks)
        pSortedChunks = sorted(pChunks, key=sortKeyChunkLength)
        for (i, pChunk) in enumerate(pSortedChunks):
            for j in range(i + 1, pChunksLen):
                p2Chunk = pSortedChunks[j]
                splits.setdefault(p2Chunk, set()).update(_getSplitPoints(pChunk, p2Chunk))

        # apply the splits for nodes of this type

        _applySplits(pChunks, splits)

        # fragmentize nodes of other types

        for q in range(p + 1, typeLen):
            qType = fOtypeAll[q]
            qChunks = chunks.get(qType, ())
            if not qChunks:
                continue
            splits = {}
            for qChunk in qChunks:
                for pChunk in pChunks:
                    splits.setdefault(qChunk, set()).update(
                        _getSplitPoints(pChunk, qChunk)
                    )
            _applySplits(qChunks, splits)

    # collect all fragments for all types in one list, ordered canonically
    # theorem: each fragment is either contained in the top node or completely
    # outside the top node.
    # We leave out the fragments that are outside the top node.
    # In order to test that, it is sufficient to test only one slot of
    # the fragment. We take the begin slot/

    chunks = sorted(
        (c for c in chain.from_iterable(chunks.values()) if c[1][0] in nSlots),
        key=sortKeyChunk,
    )

    # determine boundary classes

    chunkBoundaries = {}

    for (m, (b, e)) in chunks:
        bounds = boundaries[m]
        css = []
        code = bounds[b][0] if b in bounds else None
        cls = f"{startCls}no" if code is None else "" if code else startCls
        if cls:
            css.append(cls)
        code = bounds[e][1] if e in bounds else None
        cls = f"{endCls}no" if code is None else "" if code else endCls
        if cls:
            css.append(cls)

        chunkBoundaries[(m, (b, e))] = " ".join(css)

    # stack the chunks hierarchically

    tree = (None, oContext, [])
    parent = {}
    rightmost = tree

    for chunk in chunks:
        rightnode = rightmost
        added = False
        m = chunk[0]
        e = chunk[1][1]
        chunkInfo = {}

        while rightnode is not tree:
            (br, er) = rightnode[0][1]
            cr = rightnode[2]
            if e <= er:
                rightmost = (chunk, chunkInfo, [])
                cr.append(rightmost)
                parent[chunk] = rightnode
                added = True
                break

            rightnode = parent[rightnode[0]]

        if not added:
            rightmost = (chunk, chunkInfo, [])
            tree[2].append(rightmost)
            parent[chunk] = tree

        distillChunkInfo(m, chunkInfo)

    if explain:
        details = False if explain is True else True if explain == "details" else None
        if details is None:
            console(
                "Illegal value for parameter explain: `{explain}`.\n"
                "Must be `True` or `'details'`",
                error=True,
            )
        _showTree(tree, 0, details=details)
    return tree


def _getSplitPoints(pChunk, qChunk):
    """Determines where the boundaries of one chunk cut through another chunk.

    The splitpoint is the index where the second part starts.
    So the split point is always greater than the start point.
    """

    (b1, e1) = pChunk[1]
    (b2, e2) = qChunk[1]
    if b2 == e2 or (b1 <= b2 and e1 >= e2):
        return []
    splitPoints = set()
    if (b2 < b1 <= e2):
        splitPoints.add(b1)
    if (b2 <= e1 < e2):
        splitPoints.add(e1 + 1)
    return splitPoints


def _applySplits(chunks, splits):
    """Splits a chunk in multiple pieces marked by a given sets of points.
    """

    if not splits:
        return

    for (target, splitPoints) in splits.items():
        if not splitPoints:
            continue
        chunks.remove(target)
        (m, (b, e)) = target
        prevB = b
        # invariant: sp > prevB
        # initially true because it is the result of _getSPlitPoint
        # after each iteration: the new split point cannot be the old one
        # and the new start is the old split point.
        for sp in sorted(splitPoints):
            chunks.add((m, (prevB, sp - 1)))
            prevB = sp
        chunks.add((m, (prevB, e)))


def _showTree(tree, level, details=False):
    indent = QUAD * level
    (chunk, info, children) = tree
    if chunk is None:
        console(f"{indent}<{level}> TOP")
    else:
        (n, (b, e)) = chunk
        rangeRep = "{" + (str(b) if b == e else f"{b}-{e}") + "}"
        nContext = info["nContext"]
        nType = nContext.nType
        isBaseNonSlot = nContext.isBaseNonSlot
        base = "*" if isBaseNonSlot else ""
        boundaryCls = info["boundaryCls"]
        console(f"{indent}<{level}> {nType}{base} {n} {rangeRep} {boundaryCls}")
        if details:
            for (k, v) in sorted(nContext._asdict().items(), key=lambda x: x[0]):
                console(f"{indent}{QUAD * 4}{k:<10} = {v}")
    for subTree in children:
        _showTree(subTree, level + 1, details=details)
