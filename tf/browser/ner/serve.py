"""Main controller for Flask

This module contains the controllers that Flask invokes when serving
the annotation tool in the TF browser.

To see how this fits among all the modules of this package, see
`tf.browser.ner.annotate` .
"""

from flask import render_template

from ...core.generic import AttrDict

from .settings import TOOLKEY, SC_ALL
from .helpers import makeCss
from .annotate import Annotate
from .servelib import ServeLib
from .fragments import Fragments


class Serve(ServeLib, Fragments):
    def __init__(self, web):
        """Object that implements the controller functions for the annotatation tool.

        Parameters
        ----------
        web: object
            This represents the Flask website that is the TF browser.
            It has access to the TF-app that represents a loaded TF corpus.
            See `tf.browser.ner.web.factory` and `tf.browser.web.factory`.

            It picks up a handle to the loaded TF corpus, stores it in the `Serve`
            object, and uses it to fetch the CSS code for this tool, which is
            also stored in the `Serve` object.

            Finally, it creates a pointer to the annotation data in memory, as stored
            in the `web` object, if there is already such data from a previous request.
            If not, it initializes an empty dict in the `web` object, with the purpose
            of storing incoming annotation data there.

            This way, the annotation data is preserved between requests.
        """
        self.web = web
        kernelApi = web.kernelApi
        app = kernelApi.app
        self.app = app
        self.css = kernelApi.css()

        if not hasattr(web, "toolData"):
            setattr(web, "toolData", AttrDict())
        toolData = web.toolData

        if TOOLKEY not in toolData:
            toolData[TOOLKEY] = AttrDict()

        data = toolData[TOOLKEY]
        self.data = data

        annotate = Annotate(app, data=data, browse=True)
        self.annotate = annotate

        super().__init__()

        self.initVars()

        v = self.v
        annoSet = v.annoset

        annotate.setSet(annoSet)
        annotate.loadData()

    def setupFull(self):
        """Prepares to serve a complete page.

        *   Sets up the find widget;
        *   Encodes the active entity in hidden `input` elements;
        *   Collects and generates the specific CSS styles needed for this corpus.
        """
        css = self.css

        annotate = self.annotate
        settings = annotate.settings
        features = settings.features
        keywordFeatures = settings.keywordFeatures

        v = self.v

        self.findSetup()
        self.wrapActive()

        v.css = makeCss(features, keywordFeatures, generic=css)

    def setupLean(self):
        """Prepares to update a portion of the page.

        *   Encodes the active entity in hidden `input` elements.
        """
        self.wrapActive()

    def actionsFull(self):
        """Carries out requested actions before building the full page.

        *   annotation set management actions;
        *   fetch selected buckets from the whole corpus;
        *   modification actions in the selected set.
        """
        self.setHandling()

        self.getBuckets()
        self.updateHandling()

    def actionsLean(self, node):
        """Carries out requested actions before building a portion of the page.

        *   fetch all buckets from a section of the corpus.
        """
        self.getBuckets(node=node)

    def wrapFull(self):
        """Builds the full page.

        This includes the controls by which the user makes selections and triggers
        axctions.
        """
        annotate = self.annotate
        v = self.v
        sortKey = v.sortkey
        sortDir = v.sortdir
        activeEntity = v.activeentity
        tokenStart = v.tokenstart
        tokenEnd = v.tokenend
        excludedTokens = v.excludedtokens

        buckets = self.buckets

        self.wrapQuery()
        v.entitytable = annotate.showEntities(
            activeEntity=activeEntity, sortKey=sortKey, sortDir=sortDir
        )
        v.entityoverview = annotate.showEntityOverview()
        v.entityheaders = self.wrapEntityHeaders()
        v.buckets = annotate.showContent(
            buckets,
            activeEntity=activeEntity,
            excludedTokens=excludedTokens,
            mayLimit=not (tokenStart and tokenEnd),
        )

        return render_template(f"{TOOLKEY}/index.html", **v)

    def wrapLean(self):
        """Builds a portion of the page.

        No need to build user controls, because they are already on the page.

        Returns
        -------
        The generated HTML for the portion of the page.
        """
        annotate = self.annotate
        v = self.v
        activeEntity = v.activeentity
        excludedTokens = v.excludedtokens
        buckets = self.buckets

        return annotate.showContent(
            buckets,
            activeEntity=activeEntity,
            excludedTokens=excludedTokens,
            mayLimit=False,
        )

    def getBuckets(self, noFind=False, node=None):
        """Fetch a selection of buckets from the corpus.

        The selection is defined in the `v`.

        We further modify the selection by two additional parameters.

        The resulting list of buckets is obtained by
        `tf.browser.ner.annotate.Annotate.filterContent`, and each member in the bucket
        list is a tuple as indicated in the `filterContent` function.
        The list is stored in the `Serve` object.
        Additionally, statistics about these buckets and how many entity values
        occur in het, are delivered in the `v`.

        Parameters
        ----------
        noFind: boolean, optional False
            If `noFind` we override the filtering by the filter widget on the interface.

            We use this when the user has indicated that he wants to apply an action
            on all buckets instead of the filtered ones.

        node: integer, optional None
            If passed, it is a TF node, probably for a top-level section.
            The effect is that it restricts the result to those buttons that fall
            under that TF node.

            We use this when we retrieve the context for a given bucket.
        """
        annotate = self.annotate
        v = self.v

        bFindRe = None if noFind else v.bfindre
        anyEnt = v.anyent
        activeEntity = v.activeentity
        tokenStart = v.tokenstart
        tokenEnd = v.tokenend
        valSelect = v.valselect
        freeState = v.freestate

        setData = annotate.getSetData()
        entityIdent = setData.entityIdent

        if activeEntity not in entityIdent:
            activeEntity = None
            v.activeentity = None

        qTokens = (
            self.getStrings(tokenStart, tokenEnd) if tokenStart and tokenEnd else None
        )

        (
            self.buckets,
            v.nfind,
            v.nvisible,
            v.nent,
        ) = annotate.filterContent(
            node=node,
            bFindRe=bFindRe,
            anyEnt=anyEnt,
            eVals=activeEntity,
            qTokens=qTokens,
            valSelect=valSelect,
            freeState=freeState,
        )

    def setHandling(self):
        """Carries out the set-related actions before composing the page.

        These actions are:

        *   switch to an other set than the current set
            and create it if it does not yet exist;
        *   duplicate the current set;
        *   rename the current set;
        *   delete a set.

        The results of the actions are wrapped in messages and stored in the
        `v`.
        """
        annotate = self.annotate

        v = self.v
        chosenAnnoSet = v.annoset
        dupAnnoSet = v.duannoset
        renamedAnnoSet = v.rannoset
        deleteAnnoSet = v.dannoset

        messages = []

        if deleteAnnoSet:
            messages.extend(annotate.setDel(deleteAnnoSet))
            v.dannoset = ""
            v.annoset = ""

        if dupAnnoSet:
            messages.extend(annotate.setDup(dupAnnoSet))
            v.annoset = dupAnnoSet
            v.duannoset = ""

        if renamedAnnoSet and chosenAnnoSet:
            messages.extend(annotate.setMove(renamedAnnoSet))
            v.annoset = renamedAnnoSet
            v.rannoset = ""

        v.messagesrc = messages

        chosenAnnoSet = v.annoset
        annotate.setSet(chosenAnnoSet)

        self.wrapAnnoSets()
        self.wrapMessages()

    def updateHandling(self):
        """Carries out modification actions in the current annotation set.

        Modification actions are:

        *   deletion of an entity;
        *   addition of an entity.

        The results of the actions are wrapped in a report and stored in the
        `v`.
        """
        annotate = self.annotate
        v = self.v

        delData = v.deldata
        addData = v.adddata
        activeEntity = v.activeentity
        tokenStart = v.tokenstart
        tokenEnd = v.tokenend
        submitter = v.submitter
        excludedTokens = v.excludedtokens
        bFindRe = v.bfindre
        scope = v.scope

        hasEnt = activeEntity is not None
        hasOcc = tokenStart is not None and tokenEnd is not None

        if (
            submitter in {"delgo", "addgo"}
            and (delData or addData)
            and (hasEnt or hasOcc)
        ):
            if bFindRe and scope == SC_ALL:
                self.getBuckets(noFind=True)

            if submitter == "delgo" and delData:
                report = annotate.delEntityRich(
                    delData.deletions, self.buckets, excludedTokens=excludedTokens
                )
                annotate.loadData()
                self.wrapReport(report, "del")
                if hasEnt:
                    setData = annotate.getSetData()
                    entityIdent = setData.entityIdent

                    stillExists = activeEntity in entityIdent
                    if not stillExists:
                        v.activeentity = None

            if submitter == "addgo" and addData:
                report = annotate.addEntityRich(
                    addData.additions, self.buckets, excludedTokens=excludedTokens
                )
                annotate.loadData()
                self.wrapReport(report, "add")

            self.adaptValSelect()

            self.getBuckets()


def serveNer(web):
    """Main controller to render a full page.

    Parameters
    ----------
    web: object
        The TF browser object, a Flask web app.
    """
    serve = Serve(web)
    serve.setupFull()
    serve.actionsFull()
    return serve.wrapFull()


def serveNerContext(web, node):
    """Controller to render a portion of a page.

    More specifically: the context around a single bucket.

    Parameters
    ----------
    web: object
        The TF browser object, a Flask web app.
    node: integer
        The TF node that contain the bucket nodes that form the context.
    """
    serve = Serve(web)
    serve.setupLean()
    serve.actionsLean(node)
    return serve.wrapLean()
