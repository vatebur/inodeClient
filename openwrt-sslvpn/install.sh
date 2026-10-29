#!/bin/sh
set -eu
cd "$(dirname "$0")"
[ "$(id -u)" = 0 ] && [ "$(uname -m)" = x86_64 ]
[ -e /dev/net/tun ] && command -v ip >/dev/null
for dst in /usr/sbin/inode-sslvpn /usr/libexec/inode-sslvpn-run /usr/libexec/inode-sslvpn-firewall /usr/libexec/inode-sslvpn-dns /etc/init.d/inode-sslvpn /etc/config/inode-sslvpn; do
	[ ! -e "$dst" ] || { echo "Existing $dst; refusing to replace" >&2; exit 1; }
done
./inode-sslvpn doctor
mkdir -p /usr/sbin /usr/libexec /etc/init.d /etc/config /etc/inode-sslvpn
chmod 700 /etc/inode-sslvpn
[ -e /etc/inode-sslvpn/password ] || : > /etc/inode-sslvpn/password
chmod 600 /etc/inode-sslvpn/password
cp inode-sslvpn /usr/sbin/inode-sslvpn
cp files/inode-sslvpn-run /usr/libexec/inode-sslvpn-run
cp files/inode-sslvpn-firewall /usr/libexec/inode-sslvpn-firewall
cp files/inode-sslvpn-dns /usr/libexec/inode-sslvpn-dns
cp files/inode-sslvpn.init /etc/init.d/inode-sslvpn
cp files/inode-sslvpn.config /etc/config/inode-sslvpn
chmod 755 /usr/sbin/inode-sslvpn /usr/libexec/inode-sslvpn-run /usr/libexec/inode-sslvpn-firewall /usr/libexec/inode-sslvpn-dns /etc/init.d/inode-sslvpn
chmod 600 /etc/config/inode-sslvpn
/etc/init.d/inode-sslvpn disable
echo 'Installed; disabled until explicitly configured and started.'
