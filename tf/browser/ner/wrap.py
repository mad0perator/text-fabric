"""Wraps various pieces into HTML.
"""

from textwrap import dedent


def wrapMessages(messages):
    """HTML for messages.
    """
    html = []
    html.append("<p>")

    for (kind, text) in messages:
        html.append(f"""<span class="{kind}">{text}</span><br>""")

    html.append("</p>")
    return "\n".join(html)


def wrapAnnoSets(annoDir, chosenAnnoSet, annoSets):
    """HTML for the annoset chooser.

    It is a list of buttons, each corresponding to an existing annoset.
    A click on the button selects that annoset.
    There is also a control to delete the annoset.

    Apart from these buttons there is a button to switch to the entities that are
    present in the TF dataset as nodes of type "ent" with corresponding features.

    Finally, it is possible to create a new, empty annoset.

    Parameters
    ----------
    chosenAnnoSet: string
        The name of the chosen annoset.
        If empty, it refers to the entities already present in the dataset as TF nodes
        and features.
    annoSets: list
        The list of existing annosets.
    """
    html = []

    html.append(
        dedent(
            f"""
            <input
                type="hidden"
                name="annoset"
                value="{chosenAnnoSet}"
                id="annoseth"
            ><input
                type="hidden"
                name="rannoset"
                value=""
                id="rannoseth"
            >"""
        )
    )
    html.append(
        dedent(
            """
            <button
                type="submit" class="medium active" id="anew"
                title="create a new annotation set"
            >+</button>
            """
        )
    )
    html.append("""<select class="selinp" id="achange">""")

    for annoSet in [""] + sorted(annoSets):
        selected = "SELECTED" if annoSet == chosenAnnoSet else ""
        rep = "generated entities" if annoSet == "" else annoSet
        html.append(f"""<option value="{annoSet}" {selected}>{rep}</option>""")

    html.append("""</select>""")

    if chosenAnnoSet:
        html.append(
            dedent(
                """
                <input
                    type="hidden"
                    name="dannoset"
                    value=""
                    id="dannoseth"
                ><button
                    type="submit" class="medium active" id="arename"
                    title="rename current annotation set"
                >→</button>
                """
            )
        )
        html.append(
            dedent(
                """
                <button
                    type="submit" class="medium active" id="adelete"
                    title="delete current annotation set"
                >-</button>
                """
            )
        )
    return "\n".join(html)


def wrapEntityHeaders(sortKey, sortDir):
    """HTML for the header of the entity table.

    Dependent on the state of sorting.

    Parameters
    ----------
    sortKey: string
        Indicator of how the table is sorted.
    sortDir:
        Indicator of the direction of the sorting.

    Returns
    -------
    HTML string

    """
    html = []
    html.append("<span>")

    for (label, key) in (
        ("Frequency", "freqsort"),
        ("Kind", "kindsort"),
        ("Text", "etxtsort"),
    ):
        theDir = sortDir if key == sortKey else "u"
        theArrow = "↑" if theDir == "u" else "↓"
        html.append(
            dedent(
                f"""
                <span>{label}<button type="submit" name="{key}" value="{theDir}"
                >{theArrow}</button><span>
                """
            )
        )

    html.append("</span><br>\n")
    return "".join(html)


def wrapEntityKinds(kinds):
    """HTML for the kinds of entities.

    Parameters
    ----------
    kinds: tuple of tuples
        Frequency list of entity kinds

    Returns
    -------
    HTML string
    """
    html = []

    for (kind, freq) in kinds:
        html.append(
            dedent(
                f"""
                <span><code class="w">{freq:>5}</code> x
                <button type="submit" value="v">{kind}</button>
                </span><br>
                """
            )
        )

    html.append("</span><br>\n")
    return "".join(html)