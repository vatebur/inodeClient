include $(TOPDIR)/rules.mk
PKG_NAME:=luci-app-inode-sslvpn
PKG_VERSION:=0.4.2
PKG_RELEASE:=4
PKG_LICENSE:=MIT
include $(INCLUDE_DIR)/package.mk

define Package/luci-app-inode-sslvpn
  SECTION:=luci
  CATEGORY:=LuCI
  TITLE:=LuCI interface for iNode SSL VPN
  DEPENDS:=+inode-sslvpn +luci-base +rpcd +jshn +logd +ucode +ucode-mod-fs
  PKGARCH:=all
endef

define Build/Compile
endef

define Package/luci-app-inode-sslvpn/install
	$(CP) ./root/* $(1)/
	chmod 755 $(1)/usr/libexec/rpcd/inode-sslvpn
endef

define Package/luci-app-inode-sslvpn/postinst
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] || {
 rm -f /tmp/luci-indexcache
 rm -rf /tmp/luci-modulecache
 /etc/init.d/rpcd reload
}
exit 0
endef

$(eval $(call BuildPackage,luci-app-inode-sslvpn))
