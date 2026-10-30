"""Environment boundary for candidate graders, not for model/agent harnesses.

Only named runtime/toolchain settings cross this boundary. Provider credentials,
unknown variables and host integration settings do not. This is NOT a filesystem
or network sandbox: HOME, tool/cache directories and candidate code remain
accessible under the caller's OS permissions. Run hostile code in separate OS or
container isolation; subprocesses and memory limits alone do not provide it.
"""
from __future__ import annotations
import os
from collections.abc import Mapping

# Deliberately no suffix/prefix wildcards: an unfamiliar variable fails closed.
_RUNTIME_KEYS = frozenset("""
PATH HOME USER LOGNAME SYSTEMROOT SystemRoot WINDIR COMSPEC PATHEXT
TMPDIR TMP TEMP LANG LANGUAGE LC_ALL LC_CTYPE LC_MESSAGES TZ TERM NO_COLOR CI
PYTHONPATH PYTHONPYCACHEPREFIX PYTHONDONTWRITEBYTECODE PYTHONUNBUFFERED PYTHONIOENCODING
PYTEST_DISABLE_PLUGIN_AUTOLOAD VIRTUAL_ENV CONDA_PREFIX
GOCACHE GOMODCACHE GOPATH GOROOT GOTOOLCHAIN GOFLAGS GOMEMLIMIT
CARGO_HOME RUSTUP_HOME CARGO_TARGET_DIR CARGO_BUILD_JOBS RUSTC RUSTFLAGS
NODE_OPTIONS NODE_PATH npm_config_cache NPM_CONFIG_CACHE
JAVA_HOME CLASSPATH GRADLE_USER_HOME
CC CXX AR CFLAGS CXXFLAGS CPPFLAGS LDFLAGS LIBRARY_PATH LD_LIBRARY_PATH
DYLD_LIBRARY_PATH PKG_CONFIG_PATH SDKROOT MACOSX_DEPLOYMENT_TARGET
SERVICE_PORT
""".split())

def grader_env(overrides: Mapping[str, str] | None = None, *, source: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build the child environment from an explicit runtime allowlist.

    Overrides are filtered too, so passing a broader environment accidentally
    cannot reintroduce credentials. Selected model harnesses must NOT use this.
    """
    result = {k: v for k, v in (os.environ if source is None else source).items() if k in _RUNTIME_KEYS}
    result.update({k: v for k, v in (overrides or {}).items() if k in _RUNTIME_KEYS})
    return result
