import re
from textwrap import dedent

from ..core.helpers import console


PRE = "pre"
ZWSP = "\u200b"  # zero-width space

FOLDER = "folder"
FILE = "file"
CHAPTER = "chapter"
CHUNK = "chunk"

XNEST = "xnest"
TNEST = "tnest"
TSIB = "tsiblings"
SLOT = "slot"
WORD = "word"
CHAR = "char"
TOKEN = "token"


SECTION_MODELS = dict(
    I=dict(levels=(list, [FOLDER, FILE, CHUNK])),
    II=dict(
        levels=(list, [CHAPTER, CHUNK]),
        element=(str, "head"),
        attributes=(dict, {}),
    ),
)


SECTION_MODEL_DEFAULT = "I"


def setUp(kind):
    helpText = f"""
    Convert {kind} to TF.

    There are also commands to check the {kind} and to load the TF."""

    taskSpec = dict(
        check="reports on the elements in the source",
        convert=f"converts {kind} to TF",
        load="loads the generated TF",
        app="configures the TF-app for the result",
        apptoken="modifies the TF-app to make it token- instead of character-based",
        browse="starts the text-fabric browser on the result",
    )
    taskExcluded = {"apptoken", "browse"}

    paramSpec = {
        "tf": (
            (
                "0 or latest: update latest version;\n\t\t"
                "1 2 3: increase major, intermediate, minor tf version;\n\t\t"
                "rest: explicit version."
            ),
            "latest",
        ),
        kind.lower(): (
            (
                "0 or latest: latest version;\n\t\t"
                "-1 -2 etc: previous version, before previous, ...;\n\t\t"
                "1 2 etc: first version, second version, ...;\n\t\t"
                "rest: explicit version."
            ),
            "latest",
        ),
    }

    flagSpec = dict(
        verbose=("Produce less or more progress and reporting messages", -1, 3),
    )
    return (helpText, taskSpec, taskExcluded, paramSpec, flagSpec)


def checkSectionModel(sectionModel):
    if sectionModel is None:
        model = SECTION_MODEL_DEFAULT
        console(f"WARNING: No section model specified. Assuming model {model}.")
        properties = {k: v[1] for (k, v) in SECTION_MODELS[model].items()}
        return dict(model=model, properties=properties)

    if type(sectionModel) is str:
        if sectionModel in SECTION_MODELS:
            sectionModel = dict(model=sectionModel)
        else:
            console(f"WARNING: unknown section model: {sectionModel}")
            return False

    elif type(sectionModel) is not dict:
        console(
            f"ERROR: Section model must be a dict. You passed a {type(sectionModel)}"
        )
        return False

    model = sectionModel.get("model", None)
    if model is None:
        model = SECTION_MODEL_DEFAULT
        console(f"WARNING: No section model specified. Assuming model {model}.")
        sectionModel["model"] = model
    if model not in SECTION_MODELS:
        console(f"WARNING: unknown section model: {sectionModel}")
        return False

    properties = {k: v for (k, v) in sectionModel.items() if k != "model"}
    modelProperties = SECTION_MODELS[model]

    good = True
    delKeys = []

    for (k, v) in properties.items():
        if k not in modelProperties:
            console(f"WARNING: ignoring unknown model property {k}={v}")
            delKeys.append(k)
        elif type(v) is not modelProperties[k][0]:
            console(
                f"ERROR: property {k} should have type {modelProperties[k][0]}"
                f" but {v} has type {type(v)}"
            )
            good = False
    if good:
        for k in delKeys:
            del properties[k]

    for (k, v) in modelProperties.items():
        if k not in properties:
            console(f"WARNING: model property {k} not specified, taking default {v[1]}")
            properties[k] = v[1]

    if not good:
        return False

    return dict(model=model, properties=properties)


def tweakTrans(template, wordAsSlot, tokenBased, sectionModel, sectionProperties, rendDesc):
    if wordAsSlot:
        slot = WORD
        slotc = "Word"
        slotf = "words"
        xslot = "`word`"
    else:
        slotc = "Char"
        slot = CHAR
        slotf = "characters"
        xslot = "`char` and `word`"
    if tokenBased:
        slot = TOKEN
        slotc = "Token"
        slotf = "tokens"
        xslot = "`token`"
        tokenGen = dedent(
            """
            Tokens and sentence boundaries have been generated by a Natural Language
            Pipeline, such as Spacy.
            """
        )
        tokenWord = "token"
        hasToken = "Yes"
    else:
        tokenGen = ""
        tokenWord = "word"
        hasToken = "No"

    levelNames = sectionProperties["levels"]

    if sectionModel == "II":
        nLevels = "2"
        chapterSection = levelNames[0]
        chunkSection = levelNames[1]
        head = sectionProperties["element"]
        attributes = sectionProperties["attributes"]
        propertiesRaw = repr(sectionProperties)
        properties = (
            "".join(
                f"\t*\t`{att}` = `{val}`\n" for (att, val) in sorted(attributes.items())
            )
            if attributes
            else "\t*\t*no attribute properties*\n"
        )
    else:
        nLevels = "3"
        folderSection = levelNames[0]
        fileSection = levelNames[1]
        chunkSection = levelNames[2]

    rendDescStr = "\n".join(
        f"`{val}` | {desc}" for (val, desc) in sorted(rendDesc.items())
    )
    modelKeepRe = re.compile(rf"«(?:begin|end)Model{sectionModel}»")
    modelRemoveRe = re.compile(r"«beginModel([^»]+)».*?«endModel\1»", re.S)
    slotKeepRe = re.compile(rf"«(?:begin|end)Slot{slot}»")
    slotRemoveRe = re.compile(r"«beginSlot([^»]+)».*?«endSlot\1»", re.S)
    tokenKeepRe = re.compile(rf"«(?:begin|end)Token{hasToken}»")
    tokenRemoveRe = re.compile(r"«beginToken([^»]+)».*?«endToken\1»", re.S)

    skipVars = re.compile(r"«[^»]+»")

    text = (
        template.replace("«slot»", slot)
        .replace("«Slot»", slotc)
        .replace("«slotf»", slotf)
        .replace("«char and word»", xslot)
        .replace("«tokenWord»", tokenWord)
        .replace("«token generation»", tokenGen)
        .replace("«nLevels»", nLevels)
        .replace("«sectionModel»", sectionModel)
        .replace("«rendDesc»", rendDescStr)
    )
    if sectionModel == "II":
        text = (
            text.replace("«head»", head)
            .replace("«properties»", properties)
            .replace("«propertiesRaw»", propertiesRaw)
            .replace("«chapter»", chapterSection)
            .replace("«chunk»", chunkSection)
        )
    else:
        text = (
            text.replace("«folder»", folderSection)
            .replace("«file»", fileSection)
            .replace("«chunk»", chunkSection)
        )

    text = tokenKeepRe.sub("", text)
    text = tokenRemoveRe.sub("", text)
    text = modelKeepRe.sub("", text)
    text = modelRemoveRe.sub("", text)
    text = slotKeepRe.sub("", text)
    text = slotRemoveRe.sub("", text)

    text = skipVars.sub("", text)
    return text
