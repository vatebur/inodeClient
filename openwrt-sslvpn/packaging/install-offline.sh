#!/bin/sh
# iStore .run entry point. Contains no site configuration or passwords.
set -eu
cd "$(dirname "$0")"
[ "$(id -u)" = 0 ] || { echo 'Run as root' >&2; exit 1; }
[ "$(uname -m)" = x86_64 ] || { echo 'This build requires x86_64' >&2; exit 1; }
command -v apk >/dev/null || { echo 'This build requires APK-based OpenWrt' >&2; exit 1; }
backup=$(mktemp -d /tmp/inode-package-config.XXXXXX)
# A failed backup copy may leave a partial file. Restore only after both copies finish.
restore_ready=0
restore_file() {
 local source="$1" destination="$2" temporary
 temporary=$(mktemp "$destination.inode-restore.XXXXXX") || return 1
 if cp -p "$source" "$temporary" && [ ! -d "$destination" ] && mv -f "$temporary" "$destination"; then
  return 0
 fi
 rm -f "$temporary"
 return 1
}
cleanup() {
 result=$?
 trap - EXIT
 trap '' HUP INT TERM
 restored=1
 if [ "$restore_ready" = 1 ]; then
  if [ -f "$backup/config" ]; then
   restore_file "$backup/config" /etc/config/inode-sslvpn || restored=0
  fi
  if [ -f "$backup/password" ]; then
   mkdir -p /etc/inode-sslvpn && chmod 700 /etc/inode-sslvpn &&
    restore_file "$backup/password" /etc/inode-sslvpn/password || restored=0
  fi
 fi
 if [ "$restored" = 0 ]; then
  echo "Could not restore configuration or password. Backup retained at $backup" >&2
  [ "$result" != 0 ] || result=1
 elif ! rm -rf "$backup"; then
  [ "$result" != 0 ] || result=1
 fi
 if [ "$result" = 0 ]; then
  echo 'Installed. Open Services -> iNode SSL VPN. Existing configuration/password preserved.'
  echo 'VPN is not started automatically. Restart it manually after reviewing settings.'
 fi
 exit "$result"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
chmod 700 "$backup"
if [ -f /etc/config/inode-sslvpn ]; then
 cp -p /etc/config/inode-sslvpn "$backup/config"
fi
if [ -f /etc/inode-sslvpn/password ] && [ ! -L /etc/inode-sslvpn/password ]; then
 cp -p /etc/inode-sslvpn/password "$backup/password"
fi
restore_ready=1
# Local build is unsigned; allow only this explicit set of offline artifacts.
# Reinstall local artifacts so same-version corrections are applied as well.
apk --no-network --allow-untrusted add --force-reinstall \
 ./inode-sslvpn-0.4.2-r4.apk \
 ./luci-app-inode-sslvpn-0.4.2-r4.apk \
 ./app-meta-inode-sslvpn-0.4.2-r4.apk
