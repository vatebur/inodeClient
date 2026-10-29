include $(TOPDIR)/rules.mk
PKG_NAME:=inode-sslvpn
PKG_VERSION:=0.4.2
PKG_RELEASE:=1
PKG_LICENSE:=MIT
include $(INCLUDE_DIR)/package.mk

define Package/inode-sslvpn
  SECTION:=net
  CATEGORY:=Network
  TITLE:=H3C SSL VPN compatible client
  DEPENDS:=@TARGET_x86_64 +kmod-tun +ip-full +firewall4
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) ./inode-sslvpn $(PKG_BUILD_DIR)/inode-sslvpn
endef

define Build/Compile
endef

define Package/inode-sslvpn/conffiles
/etc/config/inode-sslvpn
/etc/inode-sslvpn/
endef

define Package/inode-sslvpn/install
	$(INSTALL_DIR) $(1)/usr/sbin $(1)/usr/libexec $(1)/etc/init.d $(1)/etc/config $(1)/usr/share/licenses/inode-sslvpn
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/inode-sslvpn $(1)/usr/sbin/
	$(INSTALL_BIN) ./files/inode-sslvpn-run $(1)/usr/libexec/
	$(INSTALL_BIN) ./files/inode-sslvpn-firewall $(1)/usr/libexec/
	$(INSTALL_BIN) ./files/inode-sslvpn-dns $(1)/usr/libexec/
	$(INSTALL_BIN) ./files/inode-sslvpn.init $(1)/etc/init.d/inode-sslvpn
	$(INSTALL_CONF) ./files/inode-sslvpn.config $(1)/etc/config/inode-sslvpn
	$(CP) ./licenses/* $(1)/usr/share/licenses/inode-sslvpn/
endef

define Package/inode-sslvpn/postinst
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] || {
 mkdir -p /etc/inode-sslvpn
 chmod 700 /etc/inode-sslvpn
 [ "$${PKG_UPGRADE}" = 1 ] || /etc/init.d/inode-sslvpn disable
}
exit 0
endef

define Package/inode-sslvpn/prerm
#!/bin/sh
[ -n "$${IPKG_INSTROOT}" ] || {
 /etc/init.d/inode-sslvpn stop || exit $$?
 /usr/libexec/inode-sslvpn-dns down || exit $$?
 /usr/libexec/inode-sslvpn-firewall remove || exit $$?
 [ "$${PKG_UPGRADE}" = 1 ] || /etc/init.d/inode-sslvpn disable
}
exit 0
endef

$(eval $(call BuildPackage,inode-sslvpn))
