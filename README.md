<p align="center">
  <img src="openwrt-sslvpn/packaging/luci/root/www/luci-static/resources/view/inode-sslvpn/logo.svg" width="128" height="128" alt="iNode SSL VPN Logo">
</p>

# H3C iNode SSL VPN for OpenWrt

基于 [inode-cli](https://github.com/VocabVictor/inode-cli) 的 H3C SSL VPN 协议兼容客户端，集成 OpenWrt UCI 配置与 procd 服务，提供 x86_64 musl 静态构建。官方 iNode 闭源安装包不纳入本仓库。

- [项目与构建说明](openwrt-sslvpn/README.md)
- [许可证与来源](openwrt-sslvpn/THIRD_PARTY.md)

仓库保存运行源码、配置模板、打包文件和公开回归测试。运维记录和实际部署配置留在本地。

- [iStore / iStoreOS APK 打包与安装](openwrt-sslvpn/packaging/README.md)

- [Release](https://github.com/vatebur/inodeClient/releases)：iStoreOS 25.12 x86_64 / APK 安装包。

发布构建由根目录 `.github/workflows/build-release.yml` 手动触发，执行静态编译及打包，
生成静态客户端、三个 APK 和离线安装包。客户端版本为 0.4.2，APK 版本为 0.4.2-r4。
