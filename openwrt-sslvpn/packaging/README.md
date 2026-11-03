# iStore / iStoreOS 安装包

目标平台：iStoreOS 25.12.5，x86/64，x86_64，apk-tools 3。
当前源码包版本为 0.4.2-r3，仅适用于 APK 系统的 x86_64，不适用于 opkg/IPK、ARM 或 MIPS。

## 产物与安装

按下文构建后生成 `../dist/inode-sslvpn-0.4.2-r3-istoreos-25.12-x86_64.run`，可上传到 iStore「手动安装」。
包含主程序包、LuCI 页面包、app-meta 元数据包。LuCI 位于「服务 → iNode SSL VPN」。

也可将 .run 复制到设备后运行：

```sh
sh /tmp/inode-sslvpn-0.4.2-r3-istoreos-25.12-x86_64.run
```

安装器保存并恢复已有 UCI 配置，兼容原先通过 tar.gz 安装的未被包管理器接管的配置。
密码不打包；离线安装器在权限为 0700 的临时目录备份已有密码和配置，成功或失败退出均恢复并删除备份。配置文件权限 0600，密码目录权限 0700。
新安装不自动连接、不启用开机启动。升级会停止原服务，安装后应检查配置并手动重启。
LuCI 页面提供动态状态、配置、密码更新、连接/断开/重连、独立开机启动和脱敏诊断。
路由设置新增默认关闭的「允许局域网通过 VPN 访问」，配置 LAN → VPN 转发、NAT 和 MTU 调整。
关闭、停止服务及卸载时清理本插件规则；LAN 开关本身不修改 DNS，电脑仍需配置网关或内网静态路由。
内网域名可在「连接配置 → 内网 DNS」独立启用分域转发，填写内网域名或后缀；DNS 地址使用网关下发且被 VPN 路由覆盖的解析器，不写死在安装包中。
程序仅维护自己新增的转发和重绑定例外，断线时清理、重连后更新；检测到运行中的 Passwall DNS 时会重启它以应用配置。
密码通过专用 RPC 原子写入 `/etc/inode-sslvpn/password`，root 所有、0600；留空保留，页面不读取已有值。

此次 APK 为本地构建的未签名包；离线安装器对随包携带的三个明确文件使用 `--allow-untrusted`。
不会修改系统全局签名信任配置。依赖 `firewall4`、`ip-full`、`kmod-tun`、`luci-base`、`rpcd`、`jshn`、`logd` 必须已安装。
若要放入正式在线仓库，应通过仓库的审核、构建与签名流程，不代表本包已获官方上架。
不要仅改扩展名生成 IPK/APK。

## 重建 APK v3

客户端从 0.4.2-r2 起负责连接、断线和重连时的 DNS 管理；本次 0.4.2-r3 沿用该客户端版本，并重新构建完整安装包。

```sh
sh cargo-openwrt.sh build --offline --locked --release --target x86_64-unknown-linux-musl --features openwrt
cp client/target/x86_64-unknown-linux-musl/release/inode dist/inode-sslvpn
```
从 `openwrt-sslvpn/` 执行，输出目录必须不存在：

```sh
python3 packaging/prepare.py --binary dist/inode-sslvpn --output /tmp/inode-apk-stage
```

将 staging 目录放到 Linux x86_64 构建机（也可用目标路由器的临时目录）。
使用含 `mkpkg` 子命令的 apk-tools 3 构建工具，以 root 或 fakeroot 执行：

```sh
cd /tmp/inode-apk-stage
APK=/path/to/build-host/apk sh build-apk.sh
```

路由器自带 apk 未编入 mkpkg，不能直接用它构建。本次使用独立的 Alpine apk-tools-static
3.0.8-r0，只在路由器 /tmp 执行，不替换系统 3.0.5。生成的 APK v3 已由系统 apk 验证和安装。
构建脚本按官方 package-pack.mk 的方式声明依赖、安装脚本与 `/lib/apk/packages/` 清单。
文件所有者标准化为 root:root；配置声明支持 APK 升级保护和 OpenWrt sysupgrade 保留。
可设 `APK_SIGN_KEY` 指向自己的 APK 签名私钥；信任和发布公钥应由发行方另行管理。

准备 makeself 2.5.0 的 `makeself.sh` 和同目录的 `makeself-header.sh`，然后：

```sh
sh packaging/build-offline.sh /path/to/makeself.sh /path/to/stage/output \
  "$PWD/dist/inode-sslvpn-0.4.2-r3-istoreos-25.12-x86_64.run"
```

升级版本时需要同步三个 Makefile、meta JSON、两个 shell 脚本中的版本号。

## SDK 和官方商店

`inode-sslvpn/Makefile`、`luci/Makefile` 可作为 OpenWrt SDK 包定义。
将两目录分别复制到 SDK 的 `package/inode-sslvpn` 和 `package/luci-app-inode-sslvpn`；
将匹配目标的二进制复制到前者目录根部的 `inode-sslvpn`，将 `../licenses/` 复制到前者的 `licenses/`。
选择匹配固件的 x86/64 SDK，用 menuconfig 选中包并构建。
本次产物由独立 mkpkg 流程生成；尚未在完整 SDK 内编译这两个包定义。

`meta/` 应复制为官方 openwrt-app-meta 仓库的 `applications/app-meta-inode-sslvpn/`。
当前网站链接指向客户端上游；正式上架前应改为实际发布本移植的项目地址，并补充教程和图标。
共享依赖只写在主包，避免 iStore 卸载影响其他应用。
官方 istore-repo 的 APK 放入 `bin/apks/x86_64/`，包文件名不能重复覆盖，PR 目标为 pending。
元数据单独向 openwrt-app-meta 提交。

参考：
- https://github.com/istoreos/openwrt-app-meta
- https://github.com/istoreos/istore-repo
- https://github.com/istoreos/istoreos/blob/istoreos-25.12/include/package-pack.mk
- https://github.com/istoreos/istoreos/wiki

## 状态、权限与操作语义

入口为 `/cgi-bin/luci/admin/services/inode-sslvpn`，使用 LuCI 的登录会话、主题及 ACL。
入口默认打开“连接状态”，并提供三个独立子页面：

- `…/inode-sslvpn/status`：状态卡片、连接控制、独立开机启动、接口及路由，每 5 秒刷新。
- `…/inode-sslvpn/config`：连接配置，按网关与认证、证书校验、路由设置、内网 DNS、隧道参数分组。
- `…/inode-sslvpn/logs`：脱敏事件和诊断建议，可手动刷新或暂停每 5 秒自动刷新。

状态页和日志页分别轮询各自的 RPC，不显示配置保存按钮。页面样式限定在应用内部，
继承 LuCI 主题，并适配窄屏布局。
无需独立 Web 服务。只授权 `inode-sslvpn` 的五个 RPC 方法及本应用的 UCI 配置，
不授予通用文件读取、命令执行、服务控制或完整系统日志权限。

页面每 5 秒刷新。procd 报告进程，客户端通过 `/var/run/inode-sslvpn/status` 报告
PID、动态接口名和连接标志。状态文件位于 0700 目录，客户端以 0600 原子替换。
RPC 校验 PID 与 procd 一致，并查询接口实时 IPv4 地址及生效路由。
断线重连期间即便接口和路由仍存在，也显示隧道未连接；进程退出后旧状态不会被信任。
不把 TUN 存在当作端到端业务可达性证明。

先保存并应用配置，再点击连接。允许连接是 UCI 策略，断开只停止当前进程；
开机启动独立且立即保存，不主动建立连接。启用开机启动但禁止连接时，启动服务也不会拨号。
认证失败不通过 procd respawn 重试；隧道重连次数有上限。保存并应用配置可能触发服务重载。

日志接口读取近期 200 行匹配事件，返回最多 40 条固定中文诊断分类，
不返回原始网关文本、密码、Cookie 或完整系统日志。暂不保留原日志时间戳。
证书始终校验；不提供跳过验证或默认路由选项。DNS 分域转发需要显式启用并填写内网域名，全局重绑定保护保持开启。
