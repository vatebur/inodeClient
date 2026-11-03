'use strict';
'require view';
'require rpc';
'require poll';
'require ui';
'require uci';

var getStatus = rpc.declare({ object: 'inode-sslvpn', method: 'status', expect: { '': {} } });
var control = rpc.declare({ object: 'inode-sslvpn', method: 'control', params: ['action'], expect: { '': {} } });
var setBoot = rpc.declare({ object: 'inode-sslvpn', method: 'boot', params: ['enabled'], expect: { '': {} } });
function checked(result) {
 if (result.error) throw new Error(result.error);
 return result;
}
function card(title, value, detail) {
 return E('div', { class: 'inode-card' }, [E('div', { class: 'inode-label' }, title), value, E('p', { class: 'inode-hint' }, detail)]);
}

return view.extend({
 load: function() { return uci.load('inode-sslvpn'); },
 render: function() {
  var busy = false, buttons = [], allowed = uci.get('inode-sslvpn', 'main', 'enabled') === '1';
  var process = E('strong', { class: 'inode-value' }, '读取中…');
  var tunnel = E('strong', { class: 'inode-value' }, '读取中…');
  var tunnelHint = E('span', {}, '实际隧道状态；进程运行不代表已连接。');
  var secret = E('strong', { class: 'inode-value' }, '读取中…');
  var iface = E('dd', { class: 'inode-mono' }, '—');
  var address = E('dd', { class: 'inode-mono' }, '—');
  var routes = E('pre', { class: 'inode-routes' }, '正在读取路由…');
  var updated = E('span', { class: 'inode-hint', role: 'status' }, '每 5 秒自动刷新');
  var errorNode = E('p', { class: 'inode-error', role: 'alert', hidden: true });
  var boot = E('input', { type: 'checkbox', disabled: true });
  var bootLabel = E('span', {}, '正在读取…');
  function lock() { buttons.forEach(function(button) { button.disabled = true; }); boot.disabled = true; }
  function failure(error) {
   lock(); errorNode.hidden = false;
   errorNode.textContent = '操作或状态读取失败：' + (error.message || String(error));
   process.textContent = '状态未知'; tunnel.textContent = '状态未知';
   tunnel.className = 'inode-value';
  }
  function refresh() {
   return getStatus().then(checked).then(function(st) {
    process.textContent = st.running ? '运行中' : '未运行';
    tunnel.textContent = st.connected ? '已连接' : '未连接';
    tunnelHint.textContent = st.connected ? '隧道已建立，可使用下方的 VPN 内网路由。' : st.running ? '进程运行中，可能正在连接、重连或出现异常。' : '启动客户端后可建立 VPN 隧道。';
    tunnel.className = 'inode-value ' + (st.connected ? 'inode-good' : st.running ? 'inode-warn' : '');
    secret.textContent = st.password_set ? '已设置' : '未设置或权限异常';
    iface.textContent = st.interface || '—'; address.textContent = st.address || '—';
    routes.textContent = st.routes || '暂无生效的 VPN 路由';
    boot.checked = !!st.boot; boot.disabled = busy;
    bootLabel.textContent = st.boot ? '已启用' : '已关闭';
    buttons[0].disabled = busy || st.running || !allowed;
    buttons[1].disabled = busy || !st.running;
    buttons[2].disabled = busy || !allowed;
    errorNode.hidden = true;
    updated.textContent = '更新于 ' + new Date().toLocaleTimeString() + ' · 每 5 秒刷新';
   });
  }
  function perform(task) {
   busy = true; lock();
   return Promise.resolve().then(task).then(checked).then(function() {
    busy = false; return refresh();
   }).catch(function(error) { busy = false; failure(error); });
  }
  ['connect', 'disconnect', 'reconnect'].forEach(function(action, index) {
   buttons.push(E('button', { type: 'button', disabled: true,
    class: 'cbi-button ' + (index === 0 ? 'cbi-button-apply' : index === 1 ? 'cbi-button-reset' : 'cbi-button-action'),
    click: ui.createHandlerFn(this, function() { return perform(function() { return control(action); }); })
   }, ['连接 VPN', '断开连接', '重新连接'][index]));
  }, this);
  boot.addEventListener('change', function() {
   var enabled = boot.checked;
   return perform(function() { return setBoot(enabled); });
  });
  refresh().catch(failure);
  poll.add(function() { return busy ? Promise.resolve() : refresh().catch(failure); }, 5);
  return E('div', { class: 'inode-page' }, [
   E('link', { rel: 'stylesheet', href: L.resource('view/inode-sslvpn/style.css') }),
   E('div', { class: 'inode-header' }, [E('div', {}, [
    E('div', { class: 'inode-brand' }, [
     E('img', { class: 'inode-logo', src: L.resource('view/inode-sslvpn/logo.svg'), alt: '', width: 40, height: 40 }),
     E('span', { class: 'inode-eyebrow' }, 'iNode SSL VPN')
    ]), E('h2', {}, '连接状态'),
    E('p', { class: 'inode-hint' }, '查看服务与隧道的实时状态，管理当前连接。')
   ]), updated]), errorNode,
   E('div', { class: 'inode-grid' }, [
    card('VPN 隧道', tunnel, tunnelHint),
    card('服务进程', process, '由 procd 管理的客户端进程。'),
    card('连接策略', E('strong', { class: 'inode-value' }, allowed ? '允许连接' : '禁止连接'), '在“连接配置”中修改并保存应用。'),
    card('账户密码', secret, '只显示设置状态，不读取已有密码。')
   ]),
   E('div', { class: 'cbi-section inode-section' }, [E('h3', {}, '连接控制'),
    E('div', { class: 'inode-actions' }, buttons),
    E('p', { class: 'inode-hint' }, '连接使用已保存并应用的配置。手动断开不会更改连接策略或开机启动。'),
    E('div', { class: 'inode-boot' }, [E('label', {}, [boot, ' 开机启动']), bootLabel]),
    E('p', { class: 'inode-hint' }, '开机启动独立保存，切换后不会立即连接。')
   ]),
   E('div', { class: 'cbi-section inode-section' }, [E('h3', {}, '隧道与路由'),
    E('dl', { class: 'inode-details' }, [E('dt', {}, 'TUN 接口'), iface, E('dt', {}, '分配的 IPv4'), address]),
    E('div', { class: 'inode-label' }, '生效的 VPN 路由'), routes,
    E('p', { class: 'inode-hint' }, '重连期间接口和路由可能仍保留。默认路由保持原状；启用内网 DNS 后，断线时清理解析规则，重连后更新。')
   ])
  ]);
 },
 handleSaveApply: null,
 handleSave: null,
 handleReset: null
});
