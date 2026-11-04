import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


RPC = Path(__file__).resolve().parents[1] / 'packaging/luci/root/usr/libexec/rpcd/inode-sslvpn'
MARKER = 'inode-rpc-test-only'

JSHN = '''
json_init() { unset rpc_error; }
json_add_string() { export rpc_error="$2"; }
json_dump() { jshn -w; }
json_load() { eval "$(jshn -r "$1")"; }
json_get_var() { export "$1=$J_V_password"; }
'''

# Always observe subprocess arguments and environment. When an OpenWrt-compatible
# interpreter is available, INODE_TEST_UCODE runs the actual parser after the check.
COMMANDS = r'''
import json
import os
from pathlib import Path
import shlex
import shutil
import sys

name = Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['RPC_TEST_TRACE'], 'a') as trace:
    print(json.dumps([name, args, dict(os.environ)]), file=trace)
if name == 'jshn':
    if args == ['-w']:
        print(json.dumps({'error': os.environ['rpc_error']}))
    elif len(args) == 2 and args[0] == '-r':
        value = json.loads(args[1]).get('password', '')
        print('export J_V_password=' + shlex.quote(value))
elif name == 'ucode':
    assert len(args) == 2 and args[0] == '-e'
    real = os.environ.get('INODE_TEST_UCODE')
    if real:
        os.execv(real, [real, *args])
    try:
        request = json.load(sys.stdin)
    except ValueError:
        sys.exit(1)
    if not isinstance(request, dict):
        sys.exit(1)
    value = request.get('password', '')
    if not isinstance(value, str):
        sys.exit(1)
    if len(value.encode()) > 4096:
        sys.exit(2)
    if any(byte in value for byte in '\x00\r\n'):
        sys.exit(3)
    print(value, end='')
elif name == 'chown':
    assert args[0] == '0:0'
    assert Path(args[1]).stat().st_mode & 0o777 == 0o600
elif name == 'mv' and os.environ.get('RPC_TEST_FAIL_MOVE') == '1':
    sys.exit(1)
else:
    target = shutil.which(name, path=os.defpath)
    os.execv(target, [target, *args])
'''


class PasswordRpcTests(unittest.TestCase):
    def setUp(self):
        scratch = TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        root = Path(scratch.name)
        self.password_dir = root / 'inode-sslvpn'
        self.password = self.password_dir / 'password'
        self.trace = root / 'trace.jsonl'
        self.rpc = root / 'rpcd-plugin'
        binaries = root / 'bin'
        binaries.mkdir()
        jshn = root / 'jshn.sh'
        jshn.write_text(JSHN)
        shim = root / 'command.py'
        shim.write_text(f'#!{sys.executable}\n{COMMANDS}')
        shim.chmod(0o755)
        for name in ('ucode', 'jshn', 'mkdir', 'chmod', 'mktemp', 'chown', 'mv', 'rm', 'printf'):
            (binaries / name).symlink_to(shim)
        self.rpc.write_text(RPC.read_text().replace('/usr/share/libubox/jshn.sh', str(jshn))
                            .replace('/etc/inode-sslvpn', str(self.password_dir)))
        self.env = {'PATH': f'{binaries}:{os.defpath}', 'RPC_TEST_TRACE': str(self.trace),
                    'password': MARKER + '-inherited'}
        if real := os.environ.get('INODE_TEST_UCODE'):
            self.env['INODE_TEST_UCODE'] = str(Path(real).resolve())

    def call(self, request):
        self.trace.write_text('')
        result = subprocess.run(['/bin/sh', self.rpc, 'call', 'password'], input=request,
                                text=True, capture_output=True, check=True, env=self.env, timeout=5)
        self.assertNotIn(MARKER, result.stdout + result.stderr)
        commands = [json.loads(line) for line in self.trace.read_text().splitlines()]
        self.assertEqual(commands[0][0], 'ucode')
        for name, args, environment in commands:
            self.assertNotEqual(name, 'printf', 'password writing must use the shell builtin')
            self.assertNotIn('password', environment)
            self.assertNotIn(MARKER, json.dumps([args, environment]))
        return json.loads(result.stdout)

    def test_password_stays_off_argv_and_environment_and_replaces_file(self):
        original = 'old password\n'
        self.password_dir.mkdir()
        self.password.write_text(original)
        value = '  ' + MARKER + ' café \'" $HOME `false` $(false) \\  '
        with self.password.open() as previous:
            self.assertEqual(self.call(json.dumps({'password': value})), {})
            self.assertEqual(previous.read(), original)
        self.assertEqual(self.password.read_text(), value + '\n')
        self.assertEqual(stat.S_IMODE(self.password.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.password_dir.stat().st_mode), 0o700)
        self.assertEqual(list(self.password_dir.iterdir()), [self.password])

    def test_empty_or_absent_password_preserves_existing_value(self):
        self.password_dir.mkdir()
        self.password.write_text('previous\n')
        for request in ({}, {'password': ''}):
            with self.subTest(request=request):
                self.assertEqual(self.call(json.dumps(request)), {})
                self.assertEqual(self.password.read_text(), 'previous\n')

    def test_rejects_invalid_requests_without_creating_files(self):
        for request in ('', '{', '[]', '{"password":null}', '{"password":123}', '{"password":"x"}x',
                        *(json.dumps({'password': MARKER + suffix})
                          for suffix in ('\n', '\r', '\x00', 'a' * 4096)),
                        json.dumps({'password': 'é' * 2049})):
            with self.subTest(request_length=len(request)):
                self.assertIn('error', self.call(request))
                self.assertFalse(self.password_dir.exists())

    def test_accepts_password_at_byte_limit(self):
        value = 'é' * 2048
        self.assertEqual(self.call(json.dumps({'password': value})), {})
        self.assertEqual(self.password.read_text(), value + '\n')

    def test_rename_failure_keeps_original_and_removes_temporary_file(self):
        self.password_dir.mkdir()
        self.password.write_text('previous\n')
        self.env['RPC_TEST_FAIL_MOVE'] = '1'
        self.assertIn('error', self.call(json.dumps({'password': MARKER})))
        self.assertEqual(self.password.read_text(), 'previous\n')
        self.assertEqual(list(self.password_dir.iterdir()), [self.password])

    def test_rejects_symlink_and_directory_at_password_path(self):
        self.password_dir.mkdir()
        target = self.password_dir / 'target'
        target.write_text('previous\n')
        self.password.symlink_to(target)
        request = json.dumps({'password': MARKER})
        self.assertIn('error', self.call(request))
        self.assertEqual(target.read_text(), 'previous\n')
        self.password.unlink()
        self.password.mkdir()
        self.assertIn('error', self.call(request))
        self.assertEqual(list(self.password.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
