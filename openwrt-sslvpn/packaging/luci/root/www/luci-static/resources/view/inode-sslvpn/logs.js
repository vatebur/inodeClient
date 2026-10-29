'use strict';
'require view';
'require rpc';
'require poll';
'require ui';

var getLogs = rpc.declare({ object: 'inode-sslvpn', method: 'logs', expect: { '': {} } });
return view.extend({
 render: function() {
  var busy = false;
  var events = E('div', { class: 'inode-events' });
  var updated = E('span', { class: 'inode-hint', role: 'status' }, '正在读取…');
  var errorNode = E('p', { class: 'inode-error', role: 'alert', hidden: true });
  var auto = E('input', { type: 'checkbox', checked: true });
  var button = E('button', { type: 'button', class: 'cbi-button cbi-button-action',
   click: ui.createHandlerFn(this, function() { return refresh(); })
  }, '立即刷新');
  function refresh() {
   if (busy) return Promise.resolve();
   busy = true; button.disabled = true;
   return getLogs().then(function(result) {
    if (result.error) throw new Error(result.error);
    var lines = (result.events || '').split('\n').filter(function(line) { return line.trim(); });
    var rows = lines.length ? lines.map(function(line, index) {
     var warning = /失败|异常|断开|拒绝/.test(line);
     return E('div', { class: 'inode-event' }, [
      E('span', { class: 'inode-event-number' }, String(index + 1).padStart(2, '0')),
      E('span', { class: 'inode-badge ' + (warning ? 'inode-warn' : 'inode-good') }, warning ? '需关注' : '连接事件'),
      E('span', {}, line)
     ]);
    }) : [E('p', { class: 'inode-empty' }, '暂无近期连接事件。建立连接后，可在此查看脱敏诊断。')];
    events.replaceChildren.apply(events, rows);
    errorNode.hidden = true;
    updated.textContent = lines.length + ' 条近期事件 · 更新于 ' + new Date().toLocaleTimeString();
   }).catch(function(error) {
    errorNode.hidden = false;
    errorNode.textContent = '日志读取失败：' + (error.message || String(error)) + '。下方保留上次结果。';
   }).finally(function() { busy = false; button.disabled = false; });
  }
  refresh();
  poll.add(function() { return auto.checked ? refresh() : Promise.resolve(); }, 5);
  return E('div', { class: 'inode-page' }, [
   E('link', { rel: 'stylesheet', href: L.resource('view/inode-sslvpn/style.css') }),
   E('div', { class: 'inode-header' }, [E('div', {}, [
    E('span', { class: 'inode-eyebrow' }, 'iNode SSL VPN'), E('h2', {}, '日志与诊断'),
    E('p', { class: 'inode-hint' }, '快速定位认证、证书与隧道连接问题。')
   ]), E('div', { class: 'inode-actions' }, [E('label', {}, [auto, ' 自动刷新（5 秒）']), button])]),
   E('div', { class: 'inode-grid inode-diagnostics' }, [
    E('div', { class: 'inode-card' }, [E('h3', {}, '认证失败'), E('p', { class: 'inode-hint' }, '检查用户名、密码、认证域及验证码要求。避免重复尝试导致账户锁定。')]),
    E('div', { class: 'inode-card' }, [E('h3', {}, '证书校验'), E('p', { class: 'inode-hint' }, '检查系统时间、CA 文件或独立确认的 SHA-256 指纹。')]),
    E('div', { class: 'inode-card' }, [E('h3', {}, '隧道异常'), E('p', { class: 'inode-hint' }, '检查网关可达性、TUN 驱动及路由冲突；重连次数耗尽后需手动连接。')])
   ]), errorNode,
   E('div', { class: 'cbi-section inode-section' }, [
    E('div', { class: 'inode-header' }, [E('h3', {}, '近期连接事件'), updated]), events,
    E('p', { class: 'inode-hint' }, '按日志原顺序展示，较新的事件位于下方，最多 40 条。仅显示脱敏分类，不含密码、Cookie 或原始网关文本。序号不是时间戳。')
   ])
  ]);
 },
 handleSaveApply: null,
 handleSave: null,
 handleReset: null
});
