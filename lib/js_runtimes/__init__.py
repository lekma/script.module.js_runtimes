# -*- coding: utf-8 -*-


import json
import platform

from .runtime import Runtime


# ------------------------------------------------------------------------------
# BunRuntime

class BunRuntime(Runtime):

    __infos__ = {
        "key": "bun",
        "name": "Bun",
        "url": "https://github.com/oven-sh/bun"
    }

    # --------------------------------------------------------------------------

    @classmethod
    def _current(cls):
        return (("-p", "Bun.version"), {})

    # --------------------------------------------------------------------------

    @classmethod
    def _latest(cls):
        # https://github.com/oven-sh/bun/raw/refs/heads/main/LATEST
        return f"{cls._url().path}/raw/refs/heads/main/LATEST"

    # --------------------------------------------------------------------------

    __machines__ = {
        "x86_64": "x64",
        "arm64": "aarch64"
    }

    __target__ = "bun-{}-{}".format(
        platform.system().lower(),
        __machines__.get((machine := platform.machine()), machine)
    )

    @classmethod
    def _target(cls):
        # https://github.com/oven-sh/bun/releases/download/bun-v1.3.10/bun-linux-x64.zip
        return "{}/releases/download/bun-v{}/{}".format(
            cls._url().path, cls.latest(), cls.__target__
        )

    # --------------------------------------------------------------------------

    @classmethod
    def _zip_name(cls):
        return (cls.__target__,) + super()._zip_name()


# ------------------------------------------------------------------------------
# DenoRuntime

class DenoRuntime(Runtime):

    __infos__ = {
        "key": "deno",
        "name": "Deno",
        "url": "https://dl.deno.land"
    }

    # --------------------------------------------------------------------------

    @classmethod
    def _current(cls):
        return (("eval", "-p", "Deno.version.deno"), {})

    # --------------------------------------------------------------------------

    @classmethod
    def _latest(cls):
        # https://dl.deno.land/release-latest.txt
        return "release-latest.txt"

    # --------------------------------------------------------------------------

    __systems__ = {
        "Linux": {
            "suffix": "unknown-linux-gnu"
        },
        "Darwin": {
            "suffix": "apple-darwin",
            "machines": {
                "arm64": "aarch64"
            }
        }
    }

    @classmethod
    def _target(cls):
        # https://dl.deno.land/release/v2.7.7/deno-x86_64-unknown-linux-gnu.zip
        system = cls.__systems__[platform.system()]
        machine = system.get("machines", {}).get(
            (machine := platform.machine()), machine
        )
        return "release/{}/deno-{}-{}".format(
            cls.latest(), machine, system["suffix"]
        )


# ------------------------------------------------------------------------------
# QuickJSRuntime

class QuickJSRuntime(Runtime):

    __infos__ = {
        "key": "quickjs",
        "name": "QuickJS",
        "url": "https://bellard.org/quickjs",
        "bin": "qjs"
    }

    # --------------------------------------------------------------------------

    @classmethod
    def _get_current(cls):
        return super()._get_current().splitlines()[0].split(" ")[-1]

    @classmethod
    def _current(cls):
        return (("-h", ), {"check": False})

    # --------------------------------------------------------------------------

    @classmethod
    def _get_latest(cls):
        return json.loads(super()._get_latest())["version"]

    @classmethod
    def _latest(cls):
        # https://bellard.org/quickjs/binary_releases/LATEST.json
        return f"{cls._url().path}/binary_releases/LATEST.json"

    # --------------------------------------------------------------------------

    __systems__ = {
        "Linux": "linux",
        "Windows": "win"
    }

    @classmethod
    def _target(cls):
        # https://bellard.org/quickjs/binary_releases/quickjs-linux-x86_64-2025-09-13.zip
        return "{}/binary_releases/quickjs-{}-{}-{}".format(
            cls._url().path,
            cls.__systems__[platform.system()],
            platform.machine(),
            cls.latest()
        )

    # --------------------------------------------------------------------------

    @classmethod
    def _version(cls, version):
        return super()._version(version.replace("-", "."))


# ------------------------------------------------------------------------------

__runtimes__ = {
    cls.key(): cls for cls in (BunRuntime, DenoRuntime, QuickJSRuntime)
}


def infos():
    return {k: v.info() for k, v in __runtimes__.items()}


def runtimes(key="deno"):
    for k, v in __runtimes__.items():
        if v.installed() or (k == key):
            v = v()
    return {k: v.runtime() for k, v in __runtimes__.items() if v.installed()}
