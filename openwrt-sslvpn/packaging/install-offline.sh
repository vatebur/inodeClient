#!/bin/sh
# iStore .run entry point. Contains no site configuration or passwords.
set -eu
cd "$(dirname "$0")"
[ "$(id -u)" = 0 ] || { echo 'Run as root' >&2; exit 1; }
[ "$(uname -m)" = x86_64 ] || { echo 'This build requires x86_64' >&2; exit 1; }
command -v apk >/dev/null || { echo 'This build requires APK-based OpenWrt' >&2; exit 1; }
backup=$(mktemp -d /tmp/inode-package-config.XXXXXX)
chmod 700 "$backup"
restore() {
 if [ -f "$backup/config" ]; then
  cp -p "$backup/config" /etc/config/inode-sslvpn
 fi
 if [ -f "$backup/password" ]; then
  mkdir -p /etc/inode-sslvpn
  chmod 700 /etc/inode-sslvpn
  cp -p "$backup/password" /etc/inode-sslvpn/password
 fi
 rm -rf "$backup"
}
trap restore EXIT
trap 'exit 1' HUP INT TERM
if [ -f /etc/config/inode-sslvpn ]; then
 cp -p /etc/config/inode-sslvpn "$backup/config"
fi
if [ -f /etc/inode-sslvpn/password ] && [ ! -L /etc/inode-sslvpn/password ]; then
 cp -p /etc/inode-sslvpn/password "$backup/password"
fi
# Local build is unsigned; allow only this explicit set of offline artifacts.
# Reinstall local artifacts so same-version corrections are applied as well.
apk --no-network --allow-untrusted add --force-reinstall \
 ./inode-sslvpn-0.4.2-r3.apk \
 ./luci-app-inode-sslvpn-0.4.2-r3.apk \
 ./app-meta-inode-sslvpn-0.4.2-r3.apk
restore
trap - EXIT
echo 'Installed. Open Services -> iNode SSL VPN. Existing configuration/password preserved.'
echo 'VPN is not started automatically. Restart it manually after reviewing settings.'
