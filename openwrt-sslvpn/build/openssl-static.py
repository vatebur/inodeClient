#!/usr/bin/env python3
"""Build the pinned OpenSSL libraries for x86_64 Linux musl."""

import argparse
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
VERSION = "3.5.9"
SHA256 = "603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a"
ARCHIVE = f"openssl-{VERSION}.tar.gz"
SOURCE_URL = f"https://github.com/openssl/openssl/releases/download/openssl-{VERSION}/{ARCHIVE}"
REQUIRED_FILES = ("lib/libssl.a", "lib/libcrypto.a", "include/openssl/opensslv.h")


def verify_archive(archive):
    digest = hashlib.sha256()
    with archive.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != SHA256:
        raise SystemExit(f"OpenSSL archive SHA-256 mismatch: {archive}")


def run(command, **kwargs):
    subprocess.run(command, check=True, stdout=sys.stderr, **kwargs)


def build_environment(toolchain):
    env = os.environ.copy()
    for name in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "LDLIBS", "CROSS_COMPILE", "MAKEFLAGS"):
        env.pop(name, None)
    env["SOURCE_DATE_EPOCH"] = "0"
    recipe = hashlib.sha256(Path(__file__).read_bytes())
    recipe.update(toolchain.encode())
    if toolchain == "zig":
        env["PATH"] = f"{HERE}:{env['PATH']}"
        env.update(CC="zig-cc", AR="zig-ar", RANLIB="zig-ranlib")
        zig = env.get("INODE_ZIG") or HERE.parents[1] / "openwrt-inode/toolchain/package/zig"
        recipe.update(subprocess.check_output([zig, "version"], env=env))
        for name in ("zig-cc", "zig-ar", "zig-ranlib"):
            recipe.update((HERE / name).read_bytes())
    else:
        env.update(CC="musl-gcc", AR="ar", RANLIB="ranlib")
        recipe.update(subprocess.check_output(["musl-gcc", "--version"], env=env))
    return env, recipe.hexdigest()


def valid_prefix(prefix, recipe):
    marker = prefix / ".build-complete"
    return (
        marker.is_file()
        and marker.read_text().strip() == recipe
        and all((prefix / name).is_file() and (prefix / name).stat().st_size for name in REQUIRED_FILES)
    )


def prepare(args):
    env, recipe = build_environment(args.toolchain)
    cache = args.cache_dir.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    prefix = cache / f"openssl-{VERSION}-{args.toolchain}-{recipe[:12]}"
    supplied = os.environ.get("INODE_OPENSSL_ARCHIVE")
    supplied = Path(supplied).resolve() if supplied else None
    with (cache / f"{prefix.name}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if valid_prefix(prefix, recipe):
            if supplied:
                verify_archive(supplied)
            return prefix
        if prefix.exists():
            shutil.rmtree(prefix)
        with tempfile.TemporaryDirectory(prefix=".build-", dir=cache) as directory:
            work = Path(directory)
            archive = work / ARCHIVE
            cached_archive = cache / ARCHIVE
            if supplied or cached_archive.is_file():
                shutil.copyfile(supplied or cached_archive, archive)
            elif args.offline:
                raise SystemExit(f"OpenSSL archive unavailable offline: {cached_archive}")
            else:
                run(["curl", "--fail", "--silent", "--show-error", "--location",
                     "--proto", "=https", "--proto-redir", "=https", "--retry", "3",
                     "--output", archive, SOURCE_URL])
            verify_archive(archive)
            run(["tar", "-xzf", archive, "-C", work])
            if supplied or not cached_archive.is_file():
                os.replace(archive, cached_archive)
            source = work / f"openssl-{VERSION}"
            staging = work / "install"
            extra_flags = []
            if args.toolchain == "musl-gcc":
                # Debian's musl include path omits the Linux UAPI headers needed
                # by OpenSSL's secure heap. Expose only UAPI, never glibc headers.
                uapi = work / "linux-uapi"
                uapi.mkdir()
                for name in ("linux", "asm-generic", "asm"):
                    candidates = (Path("/usr/include") / name,
                                  Path("/usr/include/x86_64-linux-gnu") / name)
                    header = next((path for path in candidates if path.is_dir()), None)
                    if header is None:
                        raise SystemExit(f"Missing Linux UAPI headers: {name}; install linux-libc-dev")
                    (uapi / name).symlink_to(header, target_is_directory=True)
                extra_flags.append("-I../linux-uapi")
            run(
                ["perl", "Configure", "linux-x86_64", "--prefix=/usr",
                 "--openssldir=/etc/ssl", "--libdir=lib", "no-shared", "no-module",
                 "no-engine", "no-async", "no-comp", "no-zlib", "no-zlib-dynamic", "no-tests",
                 "no-ssl3", "no-md2", "no-rc5", "no-weak-ssl-ciphers",
                 "no-camellia", "no-idea", "no-seed", *extra_flags],
                cwd=source, env=env,
            )
            jobs = min(8, os.cpu_count() or 1)
            run(["make", f"-j{jobs}", "build_libs"], cwd=source, env=env)
            run(["make", f"DESTDIR={staging}", "install_dev"], cwd=source, env=env)
            installed = staging / "usr"
            (installed / ".build-complete").write_text(recipe + "\n")
            if not valid_prefix(installed, recipe):
                raise SystemExit("OpenSSL build did not produce the expected static libraries and headers")
            installed.rename(prefix)
    return prefix


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--toolchain", choices=("zig", "musl-gcc"), required=True)
    parser.add_argument("--cache-dir", type=Path, default=HERE / "openssl")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    prefix = prepare(args)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        print(prefix)
        return
    env = os.environ.copy()
    env.update(
        X86_64_UNKNOWN_LINUX_MUSL_OPENSSL_DIR=str(prefix),
        X86_64_UNKNOWN_LINUX_MUSL_OPENSSL_LIB_DIR=str(prefix / "lib"),
        X86_64_UNKNOWN_LINUX_MUSL_OPENSSL_INCLUDE_DIR=str(prefix / "include"),
        X86_64_UNKNOWN_LINUX_MUSL_OPENSSL_STATIC="1",
        X86_64_UNKNOWN_LINUX_MUSL_OPENSSL_LIBS="ssl:crypto",
    )
    os.execvpe(command[0], command, env)


def interrupted(signum, _frame):
    raise SystemExit(128 + signum)


if __name__ == "__main__":
    signal.signal(signal.SIGHUP, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    main()
