This port uses inode-cli 0.3.2, upstream commit 200572a70d0402354a3e3cfa46ecfe9ce0d58b86 (MIT).
The binary statically includes OpenSSL 3.5.9 LTS (Apache-2.0), Rust musl runtime and Rust dependencies pinned by client/Cargo.lock.
The port adds the OpenWrt service/configuration and a SHA-256-pinned static OpenSSL build in build/openssl-static.py. See licenses/ and the original per-dependency notices for redistribution.
