#!/bin/sh
# Usage: sh build-offline.sh /path/to/makeself.sh /path/to/apk-output /path/to/app.run
set -eu
[ "$#" = 3 ] || { echo 'Usage: build-offline.sh MAKESELF APK_DIRECTORY OUTPUT.run' >&2; exit 1; }
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
for name in inode-sslvpn luci-app-inode-sslvpn app-meta-inode-sslvpn; do
 cp "$2/$name-0.4.2-r3.apk" "$work/"
done
cp "$here/install-offline.sh" "$work/install.sh"
COPYFILE_DISABLE=1 sh "$1" --nox11 --nomd5 --sha256 "$work" "$3" \
 'iNode SSL VPN 0.4.2-r3 (iStoreOS APK x86_64)' sh ./install.sh
