#!/bin/sh
# Run in the prepared staging directory using an apk-tools 3 host build.
set -eu
APK=${APK:-apk}
mkdir -p output scripts
cat > scripts/post-install <<'EOF'
#!/bin/sh
mkdir -p /etc/inode-sslvpn
chmod 700 /etc/inode-sslvpn
# Deliberately do not enable or start a VPN from package installation.
exit 0
EOF
cat > scripts/pre-deinstall <<'EOF'
#!/bin/sh
/etc/init.d/inode-sslvpn stop || exit $?
/usr/libexec/inode-sslvpn-dns down || exit $?
/usr/libexec/inode-sslvpn-firewall remove || exit $?
/etc/init.d/inode-sslvpn disable || :
exit 0
EOF
cat > scripts/pre-upgrade <<'EOF'
#!/bin/sh
/etc/init.d/inode-sslvpn stop
EOF
cat > scripts/luci-refresh <<'EOF'
#!/bin/sh
rm -f /tmp/luci-indexcache
rm -rf /tmp/luci-modulecache
/etc/init.d/rpcd reload
EOF
chmod 755 scripts/*
for name in inode-sslvpn luci-app-inode-sslvpn app-meta-inode-sslvpn; do
 chown -R 0:0 "$name"
 arch=noarch
 deps=
 set --
 case "$name" in
 inode-sslvpn)
  arch=x86_64; deps='kmod-tun ip-full firewall4'
  set -- --script "post-install:scripts/post-install" --script "post-upgrade:scripts/post-install" --script "pre-deinstall:scripts/pre-deinstall" --script "pre-upgrade:scripts/pre-upgrade" ;;
 luci-app-inode-sslvpn) deps='inode-sslvpn luci-base rpcd jshn logd ucode ucode-mod-fs'; set -- --script 'post-install:scripts/luci-refresh' --script 'post-upgrade:scripts/luci-refresh' ;;
 app-meta-inode-sslvpn) deps='luci-app-inode-sslvpn' ;;
 esac
 if [ -n "${APK_SIGN_KEY:-}" ]; then set -- "$@" --sign-key "$APK_SIGN_KEY"; fi
 "$APK" mkpkg --info "name:$name" --info 'version:0.4.2-r4' \
  --info "arch:$arch" --info 'license:MIT' \
  --info "description:H3C SSL VPN compatible client - $name" \
  --info 'url:https://github.com/VocabVictor/inode-cli' \
  --info 'origin:inode-sslvpn' --info "depends:$deps" \
  "$@" --files "$name" --output "output/${name}-0.4.2-r4.apk"
done
