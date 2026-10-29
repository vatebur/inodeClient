//! OpenWrt's launcher opts into DNS management with a trusted local helper.
//! Other platforms and standalone CLI invocations retain their resolver settings.
use anyhow::{Context, Result, ensure};
use ipnet::Ipv4Net;
use std::{net::Ipv4Addr, path::PathBuf, process::Command};

pub(super) struct GatewayDns {
    helper: Option<PathBuf>,
    active: bool,
}

fn tunnel_dns(servers: &[Ipv4Addr], routes: &[Ipv4Net]) -> Vec<Ipv4Addr> {
    servers.iter().copied().filter(|ip| routes.iter().any(|route| route.contains(ip))).collect()
}

impl GatewayDns {
    pub(super) fn new() -> Self {
        Self { helper: std::env::var_os("INODE_DNS_HELPER").map(PathBuf::from), active: false }
    }

    pub(super) fn apply(&mut self, servers: &[Ipv4Addr], routes: &[Ipv4Net]) -> Result<()> {
        if let Some(helper) = &self.helper {
            let servers = tunnel_dns(servers, routes);
            ensure!(!servers.is_empty(),
                "No gateway DNS server is covered by the installed VPN routes; add an explicit --route or disable gateway DNS");
            // No shell interpolation: the helper receives validated IPv4 arguments only.
            self.active = true;
            let status = Command::new(helper).arg("up")
                .args(servers.iter().map(ToString::to_string)).status()
                .context("Unable to run the OpenWrt DNS helper")?;
            ensure!(status.success(), "OpenWrt DNS setup failed");
        }
        Ok(())
    }

    pub(super) fn remove(&mut self) -> Result<()> {
        if self.active {
            let status = Command::new(self.helper.as_ref().unwrap()).arg("down").status()
                .context("Unable to run the OpenWrt DNS cleanup helper")?;
            ensure!(status.success(), "OpenWrt DNS cleanup failed");
            self.active = false;
        }
        Ok(())
    }
}

impl Drop for GatewayDns {
    fn drop(&mut self) {
        if let Err(error) = self.remove() {
            eprintln!("Warning: {error:#}; stop the OpenWrt service to retry DNS cleanup");
        }
    }
}
