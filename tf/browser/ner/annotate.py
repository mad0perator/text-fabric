"""Central Annotation object.

The main task of this module is to find occurrences of annotations
on the basis of criteria.

As a preparation, read `tf.about.annotate` first, since it explains the concepts, and
guides you to set up the configuration for your corpus.

But this is just the tip of the iceberg, since this module inherits
from a number of other modules that inherit form yet other modules:

*   `tf.browser.ner.show`: generate HTML for annotated buckets of the corpus;
*   `tf.browser.ner.sets`: manage annotation sets;
*   `tf.browser.ner.data`: manage annotation data: loading, adding/deleting
    annotations;
*   `tf.browser.ner.settings`: manage the specifics of a TF corpus and have
    access to its data.

It also uses

*   `tf.browser.ner.match`: to filter individual buckets on the basis of
    criteria.

Hence, `Annotation` is the central class of this tools, whose methods are relevant
for:

*   `tf.browser.ner.web`: Flask app that routes urls to controller functions.
*   `tf.browser.ner.power`: the API for users to manipulate annotations in their
    own programs, especially in a Juyter notebook.

`web` makes use of the following modules that are not needed by `power`:

*   `tf.browser.ner.serve`: define the controllers of the web app
*   `tf.browser.ner.servelib`: manage the data of a request;
*   `tf.browser.ner.fragments`: generate HTML for widgets on the page;

Both `web` and `power` make use of the following modules in as far as they are not
already mentioned under `annotate` and its parent classes:

*   `tf.browser.ner.helpers`: a variety of context-free data jugglers;
*   `tf.browser.ner.html`: a generic library to generate HTML using Pythonesque
    syntax.
"""

import collections


from .settings import TOOLKEY

from .helpers import findCompile, makeCss
from .sets import Sets
from .show import Show
from .match import entityMatch, occMatch


class Annotate(Sets, Show):
    def __init__(self, app, data=None, browse=False):
        """Entity annotation.

        Basic methods to handle the various aspects of entity annotation.
        These methods can be used by code that runs in the Text-Fabric browser
        and by code that runs in a Jupyter notebook.

        This class handles data, it does not contain code to generate HTML.
        But it has a parent class, `Show`, that can generate HTML.

        This class works with a fixed annotation set.
        But it has a parent class, `Sets` that has method to manipulate such sets
        and switch between them.

        We consider the corpus as a list of buckets (typically level-3 sectional
        units; in TEI-derived corpora called `chunk`s, being generalizations of
        `p` (paragraph) elements). What type exactly the buckets are is configured
        in the `ner/config.yaml` file.

        Parameters
        ----------
        app: object
            The object that corresponds to a loaded TF app for a corpus.
        data: object, optional None
            Entity data to start with. If this class is initialized by the browser,
            the browser hands over the in-memory data that the tool needs.
            That way, it can maintain access to the same data between requests.
            If None, no data is handed over, and a fresh data store will be
            created by an ancestor class (Data)
        browse: boolean, optional False
            If True, the object is informed that it is run by the Text-Fabric
            browser. This will influence how results are reported back.
        """
        self.app = app
        super().__init__(data=data)

        self.browse = browse

        settings = self.settings
        features = settings.features
        keywordFeatures = settings.keywordFeatures

        app.loadToolCss(TOOLKEY, makeCss(features, keywordFeatures))

        if not browse:
            self.loadData()

    def findOccs(self, qTokenSet=set()):
        """Finds the occurrences of multiple sequences of tokens.

        This is meant to efficiently list all occurrences of many token
        sequences in the corpus.

        Parameters
        ----------
        qTokenSet: set, optional set()
            A set of sequences of tokens. Each sequence in the set will be used as a
            search pattern in the whole corpus, and it occurrences are collected.

        Returns
        -------
        dict
            Keyed by each member of parameter `qTokenSet` the values are
            the occurrences of that member in the corpus.
            A single occurrence is represented as a tuple of slots.

        """
        app = self.app
        setData = self.getSetData()
        api = app.api
        L = api.L
        F = api.F

        buckets = setData.buckets or ()

        results = {}

        for b in buckets:
            occMatch(L, F, b, qTokenSet, results)

        return results

    def filterContent(
        self,
        node=None,
        bFind=None,
        bFindC=None,
        bFindRe=None,
        anyEnt=None,
        eVals=None,
        qTokens=None,
        valSelect=None,
        freeState=None,
        showStats=None,
    ):
        """Filter the buckets according to a variety of criteria.

        Either the buckets of the whole corpus are filtered, or a subset of buckets,
        namely those contained in a particular node.

        **Bucket filtering**

        The parameters `bFind`, `bFindC`, `bFindRe`  specify a regular expression
        search on the texts of the buckets.

        The positions of the found occurrences is included in the result.

        The parameter `anyEnt` is a filter on the presence or absence of entities in
        buckets in general.

        **Entity filtering**

        The parameter `eVals` holds the values of a specific entity to look for.

        **Occurrence filtering**

        The parameter `qTokens` is a sequence of tokens to look for.
        The occurrences that are found, can be filtered further by `valSelect`
        and `freeState`.

        In entity filtering and occurrence filtering, the matching occurrences
        are included in the result.

        Parameters
        ----------
        bFind: string, optional None
            A search pattern that filters the buckets, before applying the search
            for a token sequence.
        bFindC: string, optional None
            Whether the search is case sensitive or not.
        bFindRe: object, optional None
            A compiled regular expression.
            This function searches on `bFindRe`, but if it is None, it compiles
            `bFind` as regular expression and searches on that. If `bFind` itself
            is not None, of course.
        anyEnt: boolean, optional None
            If True, it wants all buckets that contain at least one already
            marked entity; if False, it wants all buckets that do not contain any
            already marked entity.
        eVals: tuple, optional None
            A sequence of values corresponding with the entity features `eid`
            and `kind`. If given, the function wants buckets that contain at least
            an entity with those properties.
        qTokens: tuple, optional None
            A sequence of tokens whose occurrences in the corpus will be looked up.
        valSelect: dict, optional None
            If present, the keys are the entity features (`eid` and `kind`),
            and the values are iterables of values that are allowed.

            The feature values to filter on.
            The results of searching for `eVals` or `qTokens` are filtered further.
            If a result is also an instance of an already marked entity,
            the properties of that entity will be compared feature by feature with
            the allowed values that `valSelect` specifies for that feature.
        freeState: boolean, optional None
            If True, found occurrences may not intersect with already marked up
            features.
            If False, found occurrences must intersect with already marked up features.
        showStats: boolean, optional None
            Whether to show statistics of the find.
            If None, it only shows gross totals, if False, it shows nothing,
            if True, it shows totals by feature.

        Returns
        -------
        list of tuples
            For each bucket that passes the filter, a tuple with the following
            members is added to the list:

            *   the TF node of the bucket;
            *   tokens: the tokens of the bucket, each token is a tuple consisting
                of the TF-slot of the token and its string value;
            *   matches: the match positions of the found occurrences or entity;
            *   positions: the token positions of where the text of the bucket
                starts matching the `bFindRe`;

            If `browse` is True, also some stats are passed next to the list
            of results.
        """
        settings = self.settings
        bucketType = settings.bucketType
        features = settings.features

        browse = self.browse
        app = self.app
        setData = self.getSetData()
        entityIndex = setData.entityIndex
        entityVal = setData.entityVal
        entitySlotVal = setData.entitySlotVal
        entitySlotAll = setData.entitySlotAll
        entitySlotIndex = setData.entitySlotIndex

        api = app.api
        L = api.L
        F = api.F
        T = api.T

        buckets = (
            setData.buckets or ()
            if node is None
            else L.d(T.sectionTuple(node)[1], otype=bucketType)
        )

        nFind = 0
        nEnt = {feat: collections.Counter() for feat in ("",) + features}
        nVisible = {feat: collections.Counter() for feat in ("",) + features}

        if bFindRe is None:
            if bFind is not None:
                (bFind, bFindRe, errorMsg) = findCompile(bFind, bFindC)
                if errorMsg:
                    app.error(errorMsg)

        hasEnt = eVals is not None
        hasQTokens = qTokens is not None and len(qTokens)
        hasOcc = not hasEnt and hasQTokens

        if eVals is not None:
            eSlots = entityVal[eVals]
            eStarts = {s[0]: s[-1] for s in eSlots}
        else:
            eStarts = None

        useQTokens = qTokens if hasOcc else None

        requireFree = (
            True if freeState == "free" else False if freeState == "bound" else None
        )

        results = []

        for b in buckets:
            fValStats = {feat: collections.Counter() for feat in features}
            (fits, result) = entityMatch(
                entityIndex,
                eStarts,
                entitySlotVal,
                entitySlotAll,
                entitySlotIndex,
                L,
                F,
                T,
                b,
                bFindRe,
                anyEnt,
                eVals,
                useQTokens,
                valSelect,
                requireFree,
                fValStats,
            )

            blocked = fits is not None and not fits

            if not blocked:
                nFind += 1

            for feat in features:
                theseStats = fValStats[feat]
                if len(theseStats):
                    theseNEnt = nEnt[feat]
                    theseNVisible = nVisible[feat]

                    for ek, n in theseStats.items():
                        theseNEnt[ek] += n
                        if not blocked:
                            theseNVisible[ek] += n

            nMatches = len(result[1])

            if nMatches:
                nEnt[""][None] += nMatches
                if not blocked:
                    nVisible[""][None] += nMatches

            if node is None:
                if fits is not None and not fits:
                    continue

                if (hasEnt or hasQTokens) and nMatches == 0:
                    continue

            results.append((b, *result))

        if browse:
            return (results, nFind, nVisible, nEnt)

        nResults = len(results)

        if showStats:
            pluralF = "" if nFind == 1 else "s"
            self.console(f"{nFind} {bucketType}{pluralF} satisfy the filter")
            for feat in ("",) + (() if anyEnt else features):
                if feat == "":
                    self.console("Combined features match:")
                    for ek, n in sorted(nEnt[feat].items()):
                        v = nVisible[feat][ek]
                        self.console(f"\t{v:>5} of {n:>5} x")
                else:
                    self.console(f"Feature {feat}: found the following values:")
                    for ek, n in sorted(nEnt[feat].items()):
                        v = nVisible[feat][ek]
                        self.console(f"\t{v:>5} of {n:>5} x {ek}")
        if showStats or showStats is None:
            pluralR = "" if nResults == 1 else "s"
            self.console(f"{nResults} {bucketType}{pluralR}")
        return results
