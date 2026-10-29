#!/usr/bin/env python3
"""Prepare APK v3 payloads; never reads local VPN credentials."""
import argparse, hashlib, json, shutil
from pathlib import Path
ap=argparse.ArgumentParser(); ap.add_argument('--binary',required=True); ap.add_argument('--output',required=True)
a=ap.parse_args()
elf=Path(a.binary).read_bytes()[:20]
if elf[:6] != b'\x7fELF\x02\x01' or int.from_bytes(elf[18:20], 'little') != 62:
 raise SystemExit('Expected a little-endian x86_64 Linux ELF binary')
here=Path(__file__).resolve().parent; out=Path(a.output).resolve()
if out.exists(): raise SystemExit('Output must be a new directory')
out.mkdir(parents=True)
def copy(root,src,dst,mode=0o644):
 p=root/dst; p.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,p); p.chmod(mode)
core=out/'inode-sslvpn'
copy(core,a.binary,'usr/sbin/inode-sslvpn',0o755)
for src,dst,mode in [('inode-sslvpn-run','usr/libexec/inode-sslvpn-run',0o755),('inode-sslvpn-firewall','usr/libexec/inode-sslvpn-firewall',0o755),('inode-sslvpn-dns','usr/libexec/inode-sslvpn-dns',0o755),('inode-sslvpn.init','etc/init.d/inode-sslvpn',0o755),('inode-sslvpn.config','etc/config/inode-sslvpn',0o600)]:
 copy(core,here/'inode-sslvpn/files'/src,dst,mode)
copy(core,here.parent/'client/LICENSE','usr/share/licenses/inode-sslvpn/LICENSE')
for license in (here.parent/'licenses').iterdir():
 copy(core,license,'usr/share/licenses/inode-sslvpn/'+license.name)
copy(core,here.parent/'THIRD_PARTY.md','usr/share/licenses/inode-sslvpn/THIRD_PARTY.md')
keep=core/'lib/upgrade/keep.d/inode-sslvpn'; keep.parent.mkdir(parents=True); keep.write_text('/etc/config/inode-sslvpn\n/etc/inode-sslvpn/\n')
shutil.copytree(here/'luci/root',out/'luci-app-inode-sslvpn')
m=out/'app-meta-inode-sslvpn/lib/apk/meta'; m.mkdir(parents=True)
shutil.copyfile(here/'meta/inode-sslvpn.json',m/'inode-sslvpn.json')
for name in ['inode-sslvpn','luci-app-inode-sslvpn','app-meta-inode-sslvpn']:
 root=out/name; d=root/'lib/apk/packages'; d.mkdir(parents=True,exist_ok=True)
 if name=='inode-sslvpn':
  (d/(name+'.conffiles')).write_text('/etc/config/inode-sslvpn\n/etc/inode-sslvpn/\n')
  cfg=root/'etc/config/inode-sslvpn'
  (d/(name+'.conffiles_static')).write_text('/etc/config/inode-sslvpn '+hashlib.sha256(cfg.read_bytes()).hexdigest()+'\n')
 paths=sorted('/'+str(f.relative_to(root)) for f in root.rglob('*') if f.is_file())
 (d/(name+'.list')).write_text('\n'.join(paths)+'\n')
shutil.copyfile(here/'build-apk.sh',out/'build-apk.sh')
