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

target=x86_64-unknown-linux-musl
explicit_target=0
read_target=0
build_musl=0
offline=
case "${CARGO_NET_OFFLINE:-}" in true|1) offline=--offline ;; esac
for arg do
	if [ "$read_target" = 1 ]; then
		[ "$arg" != "$target" ] || build_musl=1
		read_target=0
		continue
	fi
	case "$arg" in
		--) break ;;
		--target) explicit_target=1; read_target=1 ;;
		--target=*) explicit_target=1; [ "$arg" != "--target=$target" ] || build_musl=1 ;;
		--offline|--frozen) offline=--offline ;;
	esac
done
if [ "$explicit_target" = 0 ] && [ "${CARGO_BUILD_TARGET:-}" = "$target" ]; then
	build_musl=1
fi
if [ "$build_musl" = 1 ]; then
	exec python3 "$root/build/openssl-static.py" --toolchain zig ${offline:+$offline} -- cargo "$@"
fi
exec cargo "$@"
