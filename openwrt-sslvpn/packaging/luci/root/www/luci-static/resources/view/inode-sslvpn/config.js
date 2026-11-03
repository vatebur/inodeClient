'use strict';
'require view';
'require form';
'require rpc';

var password = rpc.declare({ object: 'inode-sslvpn', method: 'password', params: ['password'], expect: { "": {} } });
function checked(result) {
 if (result.error) throw new Error(result.error);
 return result;
}

return view.extend({
 render: function() {
  var m = new form.Map('inode-sslvpn', '连接配置',
   '设置网关、认证及隧道参数。保存并应用后，可在“连接状态”页面管理连接。');
  var s = m.section(form.NamedSection, 'main', 'vpn');
  s.tab('account', '网关与认证');
  s.tab('trust', '证书校验');
  s.tab('routes', '路由设置');
  s.tab('dns', '内网 DNS');
  s.tab('advanced', '隧道参数');
  var o = s.taboption('account', form.Flag, 'enabled', '允许连接'); o.rmempty = false; o.default = '0';
  o.description = '取消后保存并应用将停止服务；启用后仍可手动断开。';
  o = s.taboption('account', form.Value, 'gateway', '网关 HTTPS URL'); o.placeholder = 'https://vpn.example.com:443'; o.rmempty = false;
  o.validate = function(section, value) {
   try {
    var u = new URL(value);
    if (u.protocol === 'https:' && u.hostname && !u.username && !u.password && !u.search && !u.hash && u.pathname === '/') return true;
   } catch (e) {}
   return '请输入 HTTPS 网关地址，可带端口；不能包含账号、密码、路径或查询参数。';
  };
  o = s.taboption('account', form.Value, 'domain', '认证域'); o.default = 'local'; o.rmempty = false;
  o = s.taboption('account', form.Value, 'username', '用户名'); o.rmempty = false;
  [s.children[s.children.length - 2], o].forEach(function(field) {
   field.validate = function(section, value) { return value && !/[\x00-\x1f\x7f]/.test(value) ? true : '不能为空或包含控制字符。'; };
  });
  o = s.taboption('account', form.Value, '_password', '设置或更新密码'); o.password = true;
  o.description = '留空保留原密码。仅保存到 /etc/inode-sslvpn/password（root，0600），不会读取或显示已有密码。';
  o.cfgvalue = function() { return ''; };
  o.write = function(section, value) { return value ? password(value).then(checked).then(function() { var field = this.getUIElement(section); if (field) field.setValue(''); }.bind(this)) : Promise.resolve(); };
  o.remove = function() {};
  o.validate = function(section, value) { return !value || (value.length <= 4096 && !/[\x00\r\n]/.test(value)) ? true : '密码不能包含换行、NUL 或超过 4096 个字符。'; };
  o = s.taboption('trust', form.Value, 'servercert', '已确认的证书 SHA-256 指纹');
  o.description = '私有或自签名证书请使用独立渠道确认的指纹；留空使用 CA 校验。始终验证证书。';
  o.validate = function(section, value) { return !value || /^[0-9a-fA-F]{64}$/.test(value) ? true : '请输入 64 位十六进制 SHA-256 指纹（不含冒号）。'; };
  o = s.taboption('trust', form.Value, 'ca_file', 'CA 文件路径（可选）');
  o.validate = function(section, value) { return !value || /^\/(?:[a-zA-Z0-9_.-]+\/)*[a-zA-Z0-9_.-]+$/.test(value) && !/(^|\/)\.\.?($|\/)/.test(value) ? true : '请输入路由器上 CA 文件的绝对路径。'; };
  o = s.taboption('routes', form.Flag, 'gateway_routes', '安装网关下发路由'); o.default = '1'; o.rmempty = false;
  o.description = '客户端拒绝默认路由及覆盖 VPN 网关的路由。';
  o = s.taboption('routes', form.Flag, 'lan_access', '允许局域网通过 VPN 访问'); o.default = '0'; o.rmempty = false;
  o.description = '为 LAN 启用到 VPN 的转发和地址转换。电脑需将网关或内网静态路由指向本设备；关闭或断开连接时移除本插件规则。默认关闭，不修改 DNS。';
  o = s.taboption('routes', form.DynamicList, 'route', '额外 IPv4 路由');
  // cidr4 changes LuCI's validation value to the prefix; validate the full CIDR here.
  o.validate = function(section, value) {
   if (!value) return true;
   var match = /^(\d+)\.(\d+)\.(\d+)\.(\d+)\/(\d+)$/.exec(value);
   if (!match) return '请输入 IPv4 网络 CIDR，例如 192.0.2.0/24。';
   var a = match.slice(1, 5).map(Number), n = Number(match[5]);
   if (a.some(function(v) { return v > 255; }) || n < 1 || n > 32) return '前缀必须为 1–32，禁止默认路由。';
   var ip = ((a[0] * 16777216) + (a[1] << 16) + (a[2] << 8) + a[3]) >>> 0;
   return (n === 32 || (ip & (0xffffffff >>> n)) === 0) ? true : '请输入网络地址，主机位必须为零。';
  };
  o = s.taboption('dns', form.Flag, 'gateway_dns', '使用网关下发的内网 DNS'); o.default = '0'; o.rmempty = false;
  o.description = '仅解析下方域名，使用 VPN 路由覆盖的 DNS；连接时应用，断线时清理，重连时更新。启用后至少填写一个域名。';
  o = s.taboption('dns', form.DynamicList, 'dns_domain', '内网域名');
  o.description = '填写域名或后缀，例如 internal.example.com，包含其子域名。仅对这些域名允许 DNS 返回内网地址。公网域名继续使用原 DNS。检测到运行中的 Passwall DNS 时会重启它，代理连接可能短暂中断。';
  o.validate = function(section, value) {
   if (!value) return true;
   return value.length <= 253 && value.split('.').every(function(label) {
    return label.length <= 63 && /^[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?$/.test(label);
   }) ? true : '请输入有效域名，不含协议、端口、通配符或末尾的点。';
  };
  o = s.taboption('advanced', form.Value, 'reconnect_attempts', '隧道重连次数'); o.datatype = 'and(uinteger,range(0,100))'; o.default = '5'; o.rmempty = false;
  o.description = '仅重试已认证会话的隧道，0 表示断线即退出。';
  o = s.taboption('advanced', form.Value, 'keepalive', '保活间隔（秒）'); o.datatype = 'and(uinteger,range(0,3600))'; o.default = '30'; o.rmempty = false;
  o.description = '0 表示禁用 TCP 保活。';
  o = s.taboption('advanced', form.Value, 'mtu', 'MTU'); o.datatype = 'and(uinteger,range(576,1500))'; o.default = '1400'; o.rmempty = false;

  return m.render().then(function(formNode) {
   return E('div', { class: 'inode-page' }, [
    E('link', { rel: 'stylesheet', href: L.resource('view/inode-sslvpn/style.css') }),
    E('div', { class: 'inode-intro' }, [
     E('div', { class: 'inode-brand' }, [
      E('img', { class: 'inode-logo', src: L.resource('view/inode-sslvpn/logo.svg'), alt: '', width: 40, height: 40 }),
      E('span', { class: 'inode-eyebrow' }, 'iNode SSL VPN')
     ]),
     E('p', {}, '只将指定内网流量送入 VPN，保留系统默认路由；可按域名启用内网 DNS。')
    ]),
    formNode
   ]);
  });
 }
});
