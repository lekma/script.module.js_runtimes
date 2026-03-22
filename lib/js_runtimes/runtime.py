# -*- coding: utf-8 -*-


import abc
import os
import pathlib
import shutil
import stat
import subprocess
import traceback
import urllib
import zipfile

import xbmc, xbmcaddon, xbmcgui, xbmcvfs

from packaging.version import Version


# ------------------------------------------------------------------------------

__addon_id__ = "script.module.js_runtimes"
__addon__ = xbmcaddon.Addon(__addon_id__)
__addon_name__ = __addon__.getAddonInfo("name")

__base_path__ = pathlib.Path(
    xbmcvfs.translatePath(__addon__.getAddonInfo("profile"))
)

__progress__ = xbmcgui.DialogProgress()
__mode__ = (stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)

__headers__ = {"User-Agent": "Mozilla/5.0"}


# ------------------------------------------------------------------------------

def opener(func):
    def wrapper(cls, *args, **kwargs):
        _opener = urllib.request._opener
        urllib.request.install_opener(cls.__opener__)
        try:
            return func(cls, *args, **kwargs)
        finally:
            urllib.request.install_opener(_opener)
    return wrapper


# ------------------------------------------------------------------------------
# Runtime

class Runtime(abc.ABC):

    # --------------------------------------------------------------------------

    __opener__ = urllib.request.build_opener()

    @classmethod
    @opener
    def __urlopen__(cls, *args, **kwargs):
        return urllib.request.urlopen(*args, **kwargs)

    @classmethod
    @opener
    def __urlretrieve__(cls, *args, **kwargs):
        return urllib.request.urlretrieve(*args, **kwargs)

    # --------------------------------------------------------------------------

    @classmethod
    def __log__(cls, msg, level=xbmc.LOGINFO):
        xbmc.log(f"[{__addon_id__}] {msg}", level=level)

    @classmethod
    def __run__(cls, *args, check=True):
        return subprocess.run(
            args, check=check, stdout=subprocess.PIPE, text=True
        ).stdout.strip()

    # --------------------------------------------------------------------------

    @classmethod
    def __localize__(cls, _id_):
        return __addon__.getLocalizedString(_id_)

    @classmethod
    def __message__(cls, _id_, *args):
        return cls.__localize__(_id_).format(*args)

    # --------------------------------------------------------------------------

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for k in ("key", "name", "url"):
            if (k not in (infos := cls.__infos__)):
                raise TypeError(f"missing info: '{k}'")
        infos["url"] = urllib.parse.urlparse(infos["url"])
        infos["path"] = __base_path__.joinpath(
            (key := infos["key"]), infos.setdefault("bin", key)
        )
        cls.__opener__.addheaders = list(
            infos.setdefault("headers", __headers__).items()
        )

    @classmethod
    def key(cls):
        return cls.__infos__["key"]

    @classmethod
    def name(cls):
        return cls.__infos__["name"]

    @classmethod
    def _path(cls):
        return cls.__infos__["path"]

    @classmethod
    def path(cls):
        return f"{cls._path()}"

    @classmethod
    def _url(cls):
        return cls.__infos__["url"]

    @classmethod
    def url(cls):
        return cls._url().geturl()

    @classmethod
    def version(cls):
        return cls.current()

    # --------------------------------------------------------------------------

    __current__ = None

    @classmethod
    def _get_current(cls):
        args, kwargs = cls._current()
        return cls.__run__(cls.path(), *args, **kwargs)

    @classmethod
    def current(cls):
        if not cls.__current__:
            cls.__current__ =  cls._get_current()
        return cls.__current__

    # --------------------------------------------------------------------------

    __latest__ = None

    @classmethod
    def _get_latest(cls):
        with cls.__urlopen__(
            cls._url()._replace(path=cls._latest()).geturl()
        ) as response:
            return response.read().decode("utf-8").strip()

    @classmethod
    def latest(cls):
        if not cls.__latest__:
            cls.__latest__ = cls._get_latest()
        return cls.__latest__

    # --------------------------------------------------------------------------

    __label__ = None

    @classmethod
    def label(cls, _id_):
        if not cls.__label__:
            cls.__label__ = f"{cls.name()} {cls.latest()}"
        return cls.__message__(_id_, cls.__label__)

    # --------------------------------------------------------------------------

    __confirmed__ = None

    @classmethod
    def confirmed(cls):
        if cls.__confirmed__ is None:
            cls.__confirmed__ = xbmcgui.Dialog().yesno(
                __addon_name__, cls.label(30002)
            )
        return cls.__confirmed__

    # --------------------------------------------------------------------------

    @classmethod
    def progress_create(cls):
        __progress__.create(__addon_name__, cls.label(30004))

    @classmethod
    def progress_update(cls, count, size, total):
        __progress__.update(((count * size) * 100) // total)

    @classmethod
    def progress_close(cls):
        __progress__.close()

    @classmethod
    def target(cls):
        return cls._url()._replace(path=f"{cls._target()}.zip").geturl()

    # --------------------------------------------------------------------------

    @classmethod
    def installed(cls):
        return ((path := cls._path()).is_file() and os.access(path, os.X_OK))

    @classmethod
    def outdated(cls):
        try:
            return (cls._version(cls.current()) < cls._version(cls.latest()))
        except Exception:
            msg = cls.__message__(30007, cls.name())
            cls.__log__(
                f"{msg}:\n{traceback.format_exc()}", level=xbmc.LOGERROR
            )
            return False

    @classmethod
    def install(cls):
        cls.__log__(cls.label(30003))
        cls.progress_create()
        try:
            path, _ = cls.__urlretrieve__(
                cls.target(), reporthook=cls.progress_update
            )
        finally:
            cls.progress_close()
        os.makedirs(cls._path().parent, exist_ok=True)
        with zipfile.ZipFile(path, "r") as zip_file:
            cls._path().write_bytes(
                zip_file.read(f"{pathlib.Path(*cls._zip_name())}")
            )
        pathlib.Path(path).unlink()
        cls._path().chmod(__mode__)
        cls.__current__ = None
        xbmcgui.Dialog().ok(__addon_name__, cls.label(30005))

    @classmethod
    def uninstall(cls):
        shutil.rmtree(cls._path().parent)
        xbmcgui.Dialog().ok(__addon_name__, cls.__message__(30006, cls.name()))

    # --------------------------------------------------------------------------

    @classmethod
    def _version(cls, version):
        return Version(version)

    @classmethod
    def _zip_name(cls):
        return (cls.__infos__["bin"],)

    @classmethod
    @abc.abstractmethod
    def _current(cls):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _latest(cls):
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _target(cls):
        raise NotImplementedError

    # --------------------------------------------------------------------------

    @classmethod
    def info(cls):
        result = dict(
            {k: getattr(cls, k)() for k in ("name", "url")},
            installed=(installed := cls.installed())
        )
        if installed:
            result.update({k: getattr(cls, k)() for k in ("path", "version")})
        return result

    @classmethod
    def runtime(cls):
        return {"path": cls.path()}

    # --------------------------------------------------------------------------

    def __init__(self):
        if (((not self.installed()) or self.outdated()) and self.confirmed()):
            try:
                self.install()
            except Exception:
                msg = self.__message__(30008, self.name())
                self.__log__(
                    f"{msg}:\n{traceback.format_exc()}", level=xbmc.LOGERROR
                )
                xbmcgui.Dialog().notification(
                    __addon_name__, msg, xbmcgui.NOTIFICATION_ERROR
                )
