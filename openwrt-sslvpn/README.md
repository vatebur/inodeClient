# OpenWrt H3C SSL VPN 客户端

这是开源协议兼容实现，不是对官方闭源 iNode 的重新编译。基于 inode-cli 0.3.2，源码基线为 `200572a70d0402354a3e3cfa46ecfe9ce0d58b86`。本地移植添加 UCI/procd 服务、静态 TLS 构建 feature，以及可选的网关 DNS 分域转发。

## 结构

- `client/`：Rust 运行源码与 Cargo.lock，保留上游许可。
- `files/`：UCI 模板、前台启动包装脚本和 procd 服务。
- `install.sh`：首次安装；拒绝覆盖已有文件，默认禁用，不覆盖已有密码。
- `cargo-openwrt.sh`、`build/`：交叉构建入口、Zig 工具适配器及静态 OpenSSL 构建。
- `local/`：本地实际配置，忽略且不提交。

当前安装包版本为 `0.4.2-r4`，客户端版本为 `0.4.2`。连接参数可通过 LuCI 配置，命令行选项见 `inode-sslvpn connect --help`。

## 构建与验证

本次使用 Rust 1.92.0、Zig 0.13.0、Python 3、Perl、make。Rust 安装在 `toolchain/rustup` 与 `toolchain/cargo`，需包含 `x86_64-unknown-linux-musl` target；这些工具链不纳入 Git。可用 `INODE_ZIG=/absolute/path/to/zig` 指定 Zig。默认路径复用同一工作目录的早期构建工具。

```sh
./cargo-openwrt.sh build --locked --release \
  --target x86_64-unknown-linux-musl --features openwrt
```

输出为 `client/target/x86_64-unknown-linux-musl/release/inode`。Zig 负责目标平台 C 编译、ar 和 ranlib；Rust 自带 LLD 负责最终链接，避免重复 CRT 和 macOS ranlib 破坏 ELF 归档。产物为 Linux x86_64 musl 静态 PIE。

交叉构建首次从 OpenSSL 官方站点获取 3.5.9 LTS 源码，核对固定的 SHA-256 后编译静态库。已验证的归档和构建产物缓存在 `build/openssl/`。也可通过 `INODE_OPENSSL_ARCHIVE=/absolute/path/to/openssl-3.5.9.tar.gz` 使用同一官方归档。准备好依赖缓存后，可加 `--offline` 离线重建。

发布流程执行协议解码限制、RPC 密码处理、离线升级恢复和 OpenSSL 相对 CRL 分发点处理的自动测试，并检查产物静态链接及嵌入的 OpenSSL 版本。现场验证记录留在本地。

## 安装与运行

先复制程序为 `inode-sslvpn`，与 `install.sh` 和 `files/` 放在同一个部署目录，然后在目标路由器执行安装脚本。需要 root、TUN 与 iproute2；程序静态包含 TLS 库。

安装后填写 `/etc/config/inode-sslvpn` 和权限为 600 的 `/etc/inode-sslvpn/password`。通过 LuCI 的「连接状态」页面连接或断开；命令行可执行 `/etc/init.d/inode-sslvpn start` 或 `stop`。不要将真实密码写入模板、命令参数或 Git。

当前支持 IPv4 和密码认证，并提供默认关闭的「允许局域网通过 VPN 访问」和「使用网关下发的内网 DNS」开关，按需配置 LAN 转发、NAT 及内网域名解析；断线时清理本插件 DNS 规则，重连后更新。检测到运行中的 Passwall DNS 时同步刷新。需要 firewall4。不提供业务系统自动登录。默认路由保持原状，DNS 功能及开机自启均需显式启用。

## 内网 DNS

在 LuCI「连接配置 → 内网 DNS」启用「使用网关下发的内网 DNS」，填写内网域名或后缀，保存并应用。
例如 `internal.example.com` 包含该域名及其子域名。客户端设备需使用 OpenWrt 作为 DNS。
解析器从网关下发的地址中选择，且必须被已安装的 VPN 路由覆盖；否则需补充实际授权的 DNS 主机路由（`/32`）。

程序仅对配置域名添加转发与重绑定例外，保留全局保护及用户已有规则。断线时清理，重连后更新；异常退出遗留的规则在下次服务启停时清理。
检测到运行中的 Passwall DNS 时会重启它以加载配置，期间代理连接可能短暂中断。独立 CLI 默认不修改系统 DNS。

## iStore 安装包

已为实测 iStoreOS 25.12.5 / x86_64 / APK 提供三个标准 APK 和离线 `.run` 安装包，包含 LuCI 配置页及 iStore 元数据。构建、安装与验证范围见 [打包说明](packaging/README.md)。
