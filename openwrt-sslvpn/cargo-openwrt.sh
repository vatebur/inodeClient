#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export RUSTUP_HOME="$root/toolchain/rustup"
export CARGO_HOME="$root/toolchain/cargo"
export PATH="$CARGO_HOME/bin:$PATH"
export CARGO_TARGET_X86_64_UNKNOWN_LINUX_MUSL_LINKER="$root/build/zig-cc"
export CC_x86_64_unknown_linux_musl="$root/build/zig-cc"
export AR_x86_64_unknown_linux_musl="$root/build/zig-ar"
export RANLIB_x86_64_unknown_linux_musl="$root/build/zig-ranlib"
cd "$root/client"
exec cargo "$@"
