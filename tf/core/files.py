import os
import yaml

from shutil import rmtree, copytree, copy

from ..parameters import (
    ON_IPAD,
    GH,
    GL,
    URL_GH,
    URL_GH_API,
    URL_GH_UPLOAD,
    URL_GL,
    URL_GL_API,
    URL_GL_UPLOAD,
    URL_NB,
    ORG,
    REPO,
)
from .generic import deepAttrDict


def normpath(path):
    if path is None:
        return None
    norm = os.path.normpath(path)
    return "/".join(norm.split(os.path.sep))


_tildeDir = normpath(os.path.expanduser("~"))
_homeDir = f"{_tildeDir}/Documents" if ON_IPAD else _tildeDir


scanDir = os.scandir
walkDir = os.walk
splitExt = os.path.splitext
mTime = os.path.getmtime


def abspath(path):
    return normpath(os.path.abspath(path))


def expanduser(path):
    nPath = normpath(path)
    if nPath.startswith("~"):
        return f"{_homeDir}{nPath[1:]}"

    return nPath


def unexpanduser(path):
    nPath = normpath(path)
    # if nPath.startswith(_homeDir):
    #    return f"~{nPath[len(_homeDir):]}"

    return nPath.replace(_homeDir, "~")


def setDir(obj):
    obj.homeDir = expanduser("~")
    obj.curDir = normpath(os.getcwd())
    (obj.parentDir, x) = os.path.split(obj.curDir)


def expandDir(obj, dirName):
    if dirName.startswith("~"):
        dirName = dirName.replace("~", obj.homeDir, 1)
    elif dirName.startswith(".."):
        dirName = dirName.replace("..", obj.parentDir, 1)
    elif dirName.startswith("."):
        dirName = dirName.replace(".", obj.curDir, 1)
    return normpath(dirName)


def prefixSlash(path):
    """Prefix a / before a path if it is non-empty and not already starts with it."""
    return f"/{path}" if path and not path.startswith("/") else path


def getLocation(targetDir=None):
    """Get back-end, org, repo, relative of directory.

    Parameters
    ----------
    targetDir: string, optional None
        If None, we take the current directory.
        Otherwise, if it starts with a `/` we take it as the absolute
        target directory.
        Otherwise, we append it to the absolute path of the current directory,
        with a `/` in between.

    We assume the target directory is somewhere inside

    `~/backend/org/repo`

    If it is immediately inside this, we set `relative` to `""`.

    If it is deeper down, we assume the reference directory is the parent of the
    current directory, and the path of this parent, relative to the repo directory
    goes into the `relative` component, preceded with a backslash if it is non-empty.

    Returns
    -------
    tuple
        Consisting of `backend`, `org`, `repo`, `relative`.
        `relative` is either empty or it starts with a "/" plus a non-empty path.
    """
    curDir = normpath(os.getcwd())
    if targetDir is not None:
        targetDir = normpath(targetDir)

    destDir = (
        curDir
        if targetDir is None
        else targetDir
        if targetDir.startswith("/")
        else f"{curDir}/{targetDir}"
    )
    destDir = unexpanduser(destDir)

    if not destDir.startswith("~/"):
        return (None, None, None, None)

    destDir = destDir.removeprefix("~/")
    parts = destDir.split("/")

    if len(parts) == 1:
        return (parts[0], None, None, None)
    if len(parts) == 2:
        return (parts[0], parts[1], None, None)
    if len(parts) in {2, 3}:
        return (parts[0], parts[1], parts[2], "")

    relative = prefixSlash("/".join(parts[3:-1]))
    return (parts[0], parts[1], parts[2], relative)


def backendRep(be, kind, default=None):
    """Various back-end dependent values.

    First of all, the back-end value is
    normalized. Then related values are computed.

    Parameters
    ----------
    be: string or None
        The raw back-end value.
        It will be normalized first, where missing, undefined, empty values are
        converted to the string `github`, and other values will be lower-cased.
        Also, `github.com` and `gitlab.com` will be shortened to `github` and `gitlab`.

    kind: string
        Indicates what kind of related value should be returned:

        *   `norm`: the normalized value as described above
        *   `tech`: technology of the back-end: either `github` or `gitlab` or None;
            we assume that there is only one GitHub; that there are many GitLabs;
            any back-end that is not `github` is an instance of `gitlab`.
        *   `name`: lowercase shortest name of the back-end: `github` or `gitlab`
            or a server name like `gitlab.huc.knaw.nl`
        *   `machine`: lowercase machine name of the back-end: `github.com` or
            `gitlab.com`
            or a server name like `gitlab.huc.knaw.nl`
        *   `spec`: enclosed in `<` and `>`. Depending on the parameter `default`
            the empty string is returned instead.
        *   `clone`: base directory where clones of repos in this back-end are stored
            `~/github`, etc.
        *   `cache`: base directory where data downloads from this back-end are stored:
            `~/text-fabric-data/github`, etc.
        *   `url`: URL of the online back-end
        *   `urlnb`: URL of notebooks from the online back-end, rendered on NB-Viewer
        *   `pages`: base URL of the Pages service of the back-end

    default: boolean, optional False
        Only relevant for `kind` = `rep`.
        If `default` is passed and not None and `be` is equal to `default`,
        then the empty string is returned.

        Explanation: this is used to supply a back-end specifier to a module
        but only if that module has a different back-end than the main module.

    Returns
    -------
    string
    """

    be = (be or "").lower()
    be = (
        GH
        if be in {None, "", GH, f"{GH}.com"}
        else GL
        if be in {GL, f"{GL}.com"}
        else be
    )
    beTail = ".".join(be.split(".")[1:])

    if kind == "norm":
        return be

    if kind == "tech":
        return be if be in {GH, GL} else GL

    if kind == "name":
        return "GitHub" if be == GH else "GitLab" if be == GL else be

    if kind == "machine":
        return "github.com" if be == GH else "gitlab.com" if be == GL else be

    if kind == "rep":
        if default is not None:
            default = backendRep(default, "norm")
            if be == default:
                return ""
        return f"<{be}>"

    if kind == "clone":
        return f"{_homeDir}/{be}"

    if kind == "cache":
        return f"{_homeDir}/text-fabric-data/{be}"

    if kind == "url":
        return URL_GH if be == GH else URL_GL if be == GL else f"https://{be}"

    if kind == "urlapi":
        return (
            URL_GH_API if be == GH else URL_GL_API if be == GL else f"https://api.{be}"
        )

    if kind == "urlupload":
        return (
            URL_GH_UPLOAD
            if be == GH
            else URL_GL_UPLOAD
            if be == GL
            else f"https://api.{be}"
        )

    if kind == "urlnb":
        return f"{URL_NB}/{be}"

    if kind == "pages":
        return f"{GH}.io" if be == GH else f"{GL}.io" if be == GL else f"pages.{beTail}"
    return None


def annotateDir(app, tool):
    """Return the input and output directories for a specific annotation tool.

    *   The input directory is located next to the TF data of the corpus
    *   The output directory is located in the `_temp` directory next to the TF data of
        the corpus

    Parameters
    ----------
    app: object
        the TF app
    tool: string
        The name of the annotation tool

    Returns
    -------
    string
        The path of the working directory for that tool and that corpus
    """
    context = app.context
    appPath = context.appPath
    localDir = context.localDir
    return (f"{dirNm(appPath)}/{tool}", f"{localDir}/{tool}")


URL_TFDOC = f"https://{ORG}.{backendRep(GH, 'pages')}/{REPO}/tf"
"""Base URL of the online TF documentation."""


APIREF = f"https://{ORG}.{backendRep(GH, 'pages')}/{REPO}/tf/cheatsheet.html"
"""Link to the Api docs of TF."""

SEARCHREF = f"https://{ORG}.{backendRep(GH, 'pages')}/{REPO}/tf/about/searchusage.html"
"""Link to the Search docs of TF."""


DOWNLOADS = f"{_homeDir}/Downloads"
"""Local Downloads directory."""


EXPRESS_SYNC = "__checkout__.txt"
"""Name of cache indicator file.

When a dataset is stored in the cache,
information about the release / commit is stored in a file
with this name.
"""

EXPRESS_SYNC_LEGACY = [
    "__release.txt",
    "__commit.txt",
]
"""Legacy names of cache indicator files."""


APP_EXPRESS_ZIP = "complete.zip"
"""Name of the zip file with the complete corpus data as attached to a release.

This zip file is retrieved when using a corpus without checkout specifiers
and a part of the corpus is not locally available.
"""

APP_CONFIG = "config.yaml"
"""Name of the config file of a TF app."""

APP_CONFIG_OLD = "config.py"
"""Name of the config file of a an older, incompatible TF app."""

APP_CODE = "code"
"""Name of the top-level directory of a legacy TF app."""

APP_APP = "app"
"""Name of the top-level directory of a TF app."""

APP_DISPLAY = "static/display.css"
"""Relative path of the CSS file of a TF app."""

SERVER_DISPLAY_BASE = "/browser/static"
"""Base of server CSS files."""

SERVER_DISPLAY = ("fonts.css", "display.css", "highlight.css")
"""Bunch of TF generic CSS files."""

TOOL_DISPLAY_BASE = "/browser/{}/static"
"""Base of tool CSS files."""

TOOL_DISPLAY = ("base.css",)
"""Bunch of tool-specific CSS files."""

TEMP_DIR = "_temp"
"""Name of temporary directories.

!!! hint ".gitignore"
    Take care that these directories are ignored by git operations.
    Put a line

        _temp/

    in the `.gitignore` file.
"""

LOCATIONS = ["~/text-fabric-data"]
"""Default locations for TF data files.

If the `locations` parameter for the `tf.fabric.Fabric` call is omitted,
this is the default.
TF will search all these directories as for `.tf` modules of files.
"""

LOCAL = "_local"
"""Name of auxiliary directories.

Examples where this is used:

*   volume support: inside a TF dataset, the directory `_local` contains
    volumes of that dataset
"""

LS = "layeredsearch"
"""Directory where layered search code is stored.

Layered search is client-side search, generated in a dedicated search repo.
If the main data resides in `org/repo`, then the layered search code resides
in `org/repo-search/layeredsearch`.
"""


def dirEmpty(target):
    target = normpath(target)
    return not os.path.exists(target) or not os.listdir(target)


def clearTree(path):
    """Remove all files from a directory, recursively, but leave subdirectories.

    Reason: we want to inspect output in an editor.
    But if we remove the directories, the editor looses its current directory
    all the time.

    Parameters
    ----------
    path:
        The directory in question. A leading `~` will be expanded to the user's
        home directory.
    """

    subdirs = []
    path = expanduser(path)

    with os.scandir(path) as dh:
        for (i, entry) in enumerate(dh):
            name = entry.name
            if name.startswith("."):
                continue
            if entry.is_file():
                os.remove(f"{path}/{name}")
            elif entry.is_dir():
                subdirs.append(name)

    for subdir in subdirs:
        clearTree(f"{path}/{subdir}")


def initTree(path, fresh=False, gentle=False):
    """Make sure a directory exists, optionally clean it.

    Parameters
    ----------
    path:
        The directory in question. A leading `~` will be expanded to the user's
        home directory.

        If the directory does not exist, it will be created.

    fresh: boolean, optional False
        If True, existing contents will be removed, more or less gently.

    gentle: boolean, optional False
        When existing content is removed, only files are recursively removed, not
        subdirectories.
    """

    path = expanduser(path)
    exists = os.path.exists(path)
    if fresh:
        if exists:
            if gentle:
                clearTree(path)
            else:
                rmtree(path)

    if not exists or fresh:
        os.makedirs(path, exist_ok=True)


def dirNm(path):
    """Get the directory part of a file name."""
    return os.path.dirname(path)


def baseNm(path):
    """Get the file part of a file name."""
    return os.path.basename(path)


def stripExt(path):
    """Strip the extension of a file name, if there is one."""
    (d, f) = (dirNm(path), baseNm(path))
    sep = "/" if d else ""
    return f"{d}{sep}{f.rsplit('.', 1)[0]}"


def replaceExt(path, newExt):
    """Replace the extension of a path by another one. Specify it without dot."""
    (main, ext) = os.path.splitext(path)
    return f"{main}.{newExt}"


def splitPath(path):
    """Split a file name in a directory part and a file part."""
    return os.path.split(path)


def isFile(path):
    """Whether path exists and is a file."""
    return os.path.isfile(path)


def isDir(path):
    """Whether path exists and is a directory."""
    return os.path.isdir(path)


def fileExists(path):
    """Whether a path exists as file on the file system."""
    return os.path.isfile(path)


def fileRemove(path):
    """Removes a file if it exists as file."""
    if fileExists(path):
        os.remove(path)


def fileCopy(pathSrc, pathDst):
    """Copies a file if it exists as file.

    Wipes the destination file, if it exists.
    """
    if fileExists(pathSrc):
        fileRemove(pathDst)
        copy(pathSrc, pathDst)


def fileMove(pathSrc, pathDst):
    """Moves a file if it exists as file.

    Wipes the destination file, if it exists.
    """
    if fileExists(pathSrc):
        fileRemove(pathDst)
    os.rename(pathSrc, pathDst)


def dirExists(path):
    """Whether a path exists as directory on the file system."""
    return (
        False
        if path is None
        else True
        if path == ""
        else os.path.isdir(path)
        if path
        else True
    )


def dirRemove(path):
    """Removes a directory if it exists as directory."""
    if dirExists(path):
        rmtree(path)


def dirMove(pathSrc, pathDst):
    """Moves a directory if it exists as directory.

    Refuses the operation in the target exists.
    """
    if not dirExists(pathSrc) or dirExists(pathDst):
        return False
    os.rename(pathSrc, pathDst)
    return True


def dirCopy(pathSrc, pathDst, noclobber=False):
    """Copies a directory if it exists as directory.

    Wipes the destination directory, if it exists.
    """
    if dirExists(pathSrc):
        if dirExists(pathDst):
            if noclobber:
                return False
        dirRemove(pathDst)
        copytree(pathSrc, pathDst)
        return True
    else:
        return False


def dirMake(path):
    """Creates a directory if it does not already exist as directory."""
    if not dirExists(path):
        os.makedirs(path, exist_ok=True)


def dirContents(path):
    """Gets the contents of a directory.

    Only the direct entries in the directory (not recursively), and only real files
    and folders.

    The list of files and folders will be returned separately.
    There is no attempt to sort the files.

    Parameters
    ----------
    path: string
        The path to the directory on the file system.

    Returns
    -------
    tuple of tuple
        The subdirectories and the files.
    """
    if not dirExists(path):
        return ((), ())

    files = []
    dirs = []

    for entry in os.listdir(path):
        if os.path.isfile(f"{path}/{entry}"):
            files.append(entry)
        elif os.path.isdir(f"{path}/{entry}"):
            dirs.append(entry)

    return (tuple(files), tuple(dirs))


def dirAllFiles(path, ignore=None):
    """Gets all the files found by `path`.

    The result is just `[path]` if `path` is a file, otherwise the list of files under
    `path`, recursively.

    The files are sorted alphabetically by path name.

    Parameters
    ----------
    path: string
        The path to the file or directory on the file system.
    ignore: set
        Names of directories that must be skipped

    Returns
    -------
    tuple of string
        The names of the files under `path`, starting with `path`, followed
        by the bit relative to `path`.
    """
    if fileExists(path):
        return [path]

    if not dirExists(path):
        return []

    files = []

    if not ignore:
        ignore = set()

    for entry in os.listdir(path):
        name = f"{path}/{entry}"

        if os.path.isfile(name):
            files.append(name)
        elif os.path.isdir(name):
            if entry in ignore:
                continue
            files.extend(dirAllFiles(name, ignore=ignore))

    return tuple(sorted(files))


def getCwd():
    """Get current directory.

    Returns
    -------
    string
        The current directory.
    """
    return os.getcwd()


def chDir(directory):
    """Change to other directory.

    Parameters
    ----------
    directory: string
        The directory to change to.
    """
    return os.chdir(directory)


def readYaml(text=None, plain=False, asFile=None, preferTuples=True):
    kwargs = dict(Loader=yaml.FullLoader)

    if asFile is None:
        cfg = yaml.load(text, **kwargs)
    else:
        if fileExists(asFile):
            with open(asFile, encoding="utf8") as fh:
                cfg = yaml.load(fh, **kwargs)
        else:
            cfg = {}

    return cfg if plain else deepAttrDict(cfg, preferTuples=preferTuples)


def writeYaml(data, asFile=None):
    kwargs = dict(allow_unicode=True, sort_keys=False)

    if asFile is None:
        return yaml.dump(data, **kwargs)

    with open(asFile, "w", encoding="utf8") as fh:
        yaml.dump(data, fh, **kwargs)
