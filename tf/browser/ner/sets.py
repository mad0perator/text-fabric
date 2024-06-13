"""Annotation set management.

Annotation sets contain the annotations that the user generates by using
the tool.

To see how this fits among all the modules of this package, see
`tf.browser.ner.ner` .
"""

from .data import Data


from ...core.generic import AttrDict
from ...core.files import (
    fileExists,
    initTree,
    dirExists,
    dirContents,
    dirMake,
    dirCopy,
    dirRemove,
    dirMove,
)

from .settings import ERROR, SET_ENT, SET_SHEET, SET_MAIN


class Sets(Data):
    def __init__(self, sets=None):
        """Methods to create, duplicate, rename and delete annotation sets.

        Annotation sets have names, given by the user.

        There is a special annotation set, whose name is the empty string,
        and whose content are the pre-existing entities, i.e. the entities that
        are present in the TF data as nodes and features.

        Users can not name sets with names that start with a dot.

        Annotation sets whose name start with a dot are generated by the system
        when a family of spreadsheets with entity triggers is processed.
        These sets are readonly, like the special annotation set, but they can
        be duplicated to ordinary sets. Those copies loose the relationship with
        the original spreadsheet.

        There is always one current annotation set, whose data is loaded into
        memory.

        Parameters
        ----------
        sets: object, optional None
            Entity sets to start with.
            If None, a fresh store of sets will be created by a parent class (Data).
        """
        Data.__init__(self, sets=sets)

        if not self.properlySetup:
            return

        browse = self.browse

        self.setName = ""
        """The current annotation set."""

        self.setInfo()

        self.setNames = set()
        """The set of names of annotation sets that are present on the file system."""

        self.readSets()

        if not browse:
            self.loadSetData()

    def setInfo(self, setName=None):
        settings = self.settings
        entitySet = settings.entitySet

        inObject = False

        if setName is None:
            setName = self.setName
            inObject = True

        setIsRo = setName == "" or setName.startswith(".")
        setIsSrc = setName == ""

        setNameRep = (
            f"{SET_ENT} {entitySet}"
            if setName == ""
            else f"{SET_SHEET} {setName[1:]}"
            if setName.startswith(".")
            else f"{SET_MAIN} {setName}"
        )
        if inObject:
            self.setNameRep = setNameRep
            self.setIsRo = setIsRo
            self.setIsSrc = setIsSrc
        else:
            return (setNameRep, setIsRo, setIsSrc)

    def readSets(self):
        """Read the list current annotation sets (again).

        Use this when you change annotation sets outside the NER browser, e.g.
        by working with annotations in a Jupyter Notebook.
        """
        annoDir = self.annoDir
        self.setNames = set(dirContents(annoDir)[1])

    def getSetData(self):
        """Deliver the current set."""
        setsData = self.sets
        setName = self.setName
        setData = setsData.setdefault(setName, AttrDict())
        return setData

    def setSet(self, newSetName):
        """Switch to a named annotation set.

        If the new set does not exist, it will be created.
        After the switch, the new set will be loaded into memory.

        Parameters
        ----------
        newSetName: string
            The name of the new annotation set to switch to.
        """
        if not self.properlySetup:
            return

        browse = self.browse

        if not browse:
            self.loadSetData()

        setNames = self.setNames
        setsData = self.sets
        setName = self.setName
        annoDir = self.annoDir
        newSetDir = f"{annoDir}/{newSetName}"

        (newSetNameRep, newSetRo, newSetSrc) = self.setInfo(newSetName)

        if (not newSetSrc) and (newSetName not in setNames or not dirExists(newSetDir)):
            initTree(newSetDir, fresh=False)
            setNames.add(newSetName)

        if newSetName != setName:
            setName = newSetName
            self.setName = setName
            self.setInfo()
            self.loadSetData()

        if not browse:
            setNameRep = self.setNameRep
            entities = setsData[setName].entities
            nEntities = len(entities)
            plural = "" if nEntities == 1 else "s"
            self.console(
                f"Annotation set {setNameRep} has {nEntities} annotation{plural}"
            )

    def _addToSet(self, newEntities, silent=False):
        """Add a bunch of entities to the current set.

        Only for sets that correspond to sheets. This is to create such a set,
        it is not meant to call this function manually in a Jupyter notebook.

        Parameters
        ----------
        newSetName: string
            The name of the new annotation set to switch to.
        """
        if not self.properlySetup:
            return

        setIsRo = self.setIsRo
        setIsSrc = self.setIsSrc

        if setIsSrc or not setIsRo:
            return

        self._clearSetData()
        self.addEntities(newEntities, silent=False, _lowlevel=True)

    def resetSet(self):
        """Clear the current annotation set.

        The special set `""` cannot be reset, because it is read-only.
        """
        if not self.properlySetup:
            return

        settings = self.settings
        setName = self.setName
        setIsRo = self.setIsRo
        entitySet = settings.entitySet

        if setIsRo:
            self.console(f"Resetting the {entitySet} has no effect")
            return

        browse = self.browse

        setsData = self.sets
        annoDir = self.annoDir
        setDir = f"{annoDir}/{setName}"

        initTree(setDir, fresh=True, gentle=True)
        self.loadSetData()

        if not browse:
            setNameRep = self.setNameRep
            entities = setsData[setName].entities
            nEntities = len(entities)
            plural = "" if nEntities == 1 else "s"
            self.console(
                f"Annotation set {setNameRep} has {nEntities} annotation{plural}"
            )

    def setDup(self, dupSet):
        """Duplicates the current set to a set with a new name.

        !!! hint "The readonly sets can be duplicated"
            After duplication of a read-only set, the duplicate
            copy is modifiable.
            In this way you can make corrections to the set of pre-existing,
            tool-generated annotations.

        The current set changes to the result of the duplication.

        Parameters
        ----------
        dupSet: string
            The name of new set that is the result of the duplication.
        """
        if not self.properlySetup:
            return []

        setNames = self.setNames
        setsData = self.sets
        setName = self.setName
        setIsSrc = self.setIsSrc
        annoDir = self.annoDir
        annoPath = f"{annoDir}/{dupSet}"

        messages = []

        if dupSet in setNames:
            messages.append((ERROR, f"""Set {dupSet} already exists"""))
        else:
            if setIsSrc:
                dataFile = f"{annoPath}/entities.tsv"

                if fileExists(dataFile):
                    messages.append((ERROR, f"""Set {dupSet} already exists"""))
                else:
                    dirMake(annoPath)
                    self.saveEntitiesAs(dataFile)
                    setNames.add(dupSet)
                    setsData[dupSet] = setsData[setName]
                    self.setName = dupSet
                    self.setInfo()
            else:
                if not dirCopy(
                    f"{annoDir}/{setName}",
                    annoPath,
                    noclobber=True,
                ):
                    messages.append(
                        (ERROR, f"""Could not copy {setName} to {dupSet}""")
                    )
                else:
                    setNames.add(dupSet)
                    setsData[dupSet] = setsData[setName]
                    self.setName = dupSet
                    self.setInfo()

        return messages

    def setDel(self, delSet):
        """Remove a named set.

        If the removed set happens to be the current set, the current set changes
        to the special set named `""`.

        Parameters
        ----------
        delSet: string
            The name of the set to be removed.
            It is not allowed to remove the special set named `""`.
        """
        if not self.properlySetup:
            return []

        messages = []
        (delSetRep, delSetRo, delSetSrc) = self.setInfo(setName=delSet)

        if delSetRo:
            messages.append(
                (ERROR, f"""Cannot remove set {delSetRep} because it is read-only""")
            )
            return messages

        setNames = self.setNames
        setsData = self.sets
        annoDir = self.annoDir
        annoPath = f"{annoDir}/{delSet}"

        dirRemove(annoPath)

        if dirExists(annoPath):
            messages.append((ERROR, f"""Could not remove {delSetRep}"""))
        else:
            setNames.discard(delSet)
            del setsData[delSet]
            if self.setName == delSet:
                self.setName = ""
                self.setInfo()

        return messages

    def setMove(self, moveSet):
        """Renames a named set.

        The current set changes to the renamed set.
        It is not possible to rename the special set named `""`.
        It is also forbidden to rename another set to the special set.

        Parameters
        ----------
        moveSet: string
            The new name of the current set.
        """
        if not self.properlySetup:
            return []

        messages = []
        (moveSetRep, moveSetRo, moveSetSrc) = self.setInfo(setName=moveSet)

        if moveSetRo:
            messages.append((ERROR, f"""Cannot rename a set to ""{moveSetRep}"""))
            return messages

        setName = self.setName
        setNameRep = self.setNameRep
        setIsRo = self.setIsRo

        if setIsRo:
            messages.append((ERROR, f"""Cannot rename set ""{setNameRep}"""))
            return messages

        setNames = self.setNames
        setsData = self.sets
        annoDir = self.annoDir
        annoPath = f"{annoDir}/{moveSet}"

        if dirExists(annoPath):
            messages.append((ERROR, f"""Set {moveSetRep} already exists"""))
        else:
            if not dirMove(f"{annoDir}/{setName}", annoPath):
                messages.append(
                    (
                        ERROR,
                        f"""Could not rename {setNameRep} to {moveSetRep}""",
                    )
                )
            else:
                setNames.add(moveSet)
                setNames.discard(setName)
                setsData[moveSet] = setsData[setName]
                del setsData[setName]
                self.setName = moveSet
                self.setInfo()

        return messages
