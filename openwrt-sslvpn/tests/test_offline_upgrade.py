"""Exercise the offline installer with synthetic files and package commands."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


INSTALLER = Path(__file__).resolve().parents[1] / "packaging" / "install-offline.sh"
ORIGINAL_CONFIG = "synthetic existing configuration\n"
ORIGINAL_PASSWORD = "synthetic existing password\n"
PACKAGE_CONFIG = "package configuration\n"
PACKAGE_PASSWORD = "package password fixture\n"


class OfflineUpgradeTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="inode-upgrade-test-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.config = self.root / "etc/config/inode-sslvpn"
        self.password = self.root / "etc/inode-sslvpn/password"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.write_command("id", "echo 0")
        self.write_command("uname", "echo x86_64")
        self.write_command(
            "apk",
            """
: > "$TEST_ROOT/apk-called"
printf 'package configuration\n' > "$TEST_ROOT/etc/config/inode-sslvpn"
printf 'package password fixture\n' > "$TEST_ROOT/etc/inode-sslvpn/password"
chmod 644 "$TEST_ROOT/etc/config/inode-sslvpn" "$TEST_ROOT/etc/inode-sslvpn/password"
if [ "$APK_TERMINATE" = 1 ]; then
 kill -TERM "$PPID"
fi
exit "$APK_EXIT"
""",
        )
        self.write_command(
            "cp",
            """
case "$2:$3" in
 */backup.*/config:*) phase=restore-config ;;
 */backup.*/password:*) phase=restore-password ;;
 *:*/backup.*/config) phase=backup-config ;;
 *:*/backup.*/password) phase=backup-password ;;
 *) phase=other ;;
esac
if [ "$phase" = "$COPY_FAILURE" ]; then
 printf 'incomplete copy\n' > "$3"
 exit 1
fi
exec /bin/cp "$@"
""",
        )
        source = INSTALLER.read_text().replace("/etc/config/inode-sslvpn", str(self.config))
        source = source.replace("/etc/inode-sslvpn", str(self.password.parent))
        source = source.replace("/tmp/inode-package-config.", str(self.root / "backup."))
        self.script = self.root / "install.sh"
        self.script.write_text(source)

    def write_command(self, name, script):
        command = self.bin / name
        command.write_text("#!/bin/sh\n" + script + "\n")
        command.chmod(0o755)

    def reset_originals(self):
        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.password.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        self.config.write_text(ORIGINAL_CONFIG)
        self.password.write_text(ORIGINAL_PASSWORD)
        self.config.chmod(0o600)
        self.password.chmod(0o600)
        (self.root / "apk-called").unlink(missing_ok=True)

    def run_installer(self, apk_exit=0, copy_failure="none", terminate=False):
        return subprocess.run(
            ["sh", str(self.script)],
            env={
                **os.environ,
                "PATH": f"{self.bin}:/usr/bin:/bin",
                "TEST_ROOT": str(self.root),
                "APK_EXIT": str(apk_exit),
                "APK_TERMINATE": str(int(terminate)),
                "COPY_FAILURE": copy_failure,
            },
            capture_output=True,
            text=True,
            timeout=10,
        )

    def assert_originals_preserved(self):
        self.assertEqual(self.config.read_text(), ORIGINAL_CONFIG)
        self.assertEqual(self.password.read_text(), ORIGINAL_PASSWORD)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.password.stat().st_mode & 0o777, 0o600)

    def test_partial_backup_does_not_run_apk_or_replace_originals(self):
        for copy_failure in ("backup-config", "backup-password"):
            with self.subTest(copy_failure=copy_failure):
                self.reset_originals()
                result = self.run_installer(copy_failure=copy_failure)
                self.assertEqual(result.returncode, 1)
                self.assertFalse((self.root / "apk-called").exists())
                self.assert_originals_preserved()
                self.assertFalse(list(self.root.glob("backup.*")))

    def test_termination_during_apk_restores_originals(self):
        self.reset_originals()
        result = self.run_installer(terminate=True)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertTrue((self.root / "apk-called").exists())
        self.assertNotIn("Installed.", result.stdout)
        self.assert_originals_preserved()
        self.assertFalse(list(self.root.glob("backup.*")))

    def test_package_success_and_failure_preserve_originals(self):
        for apk_exit in (0, 17):
            with self.subTest(apk_exit=apk_exit):
                self.reset_originals()
                result = self.run_installer(apk_exit)
                self.assertEqual(result.returncode, apk_exit, result.stderr)
                self.assertTrue((self.root / "apk-called").exists())
                self.assertEqual("Installed." in result.stdout, apk_exit == 0)
                self.assert_originals_preserved()
                self.assertFalse(list(self.root.glob("backup.*")))

    def test_partial_restore_leaves_destination_intact_and_retains_backup(self):
        for copy_failure, apk_exit in (("restore-config", 0), ("restore-password", 17)):
            with self.subTest(copy_failure=copy_failure, apk_exit=apk_exit):
                self.reset_originals()
                result = self.run_installer(apk_exit, copy_failure)
                self.assertEqual(result.returncode, apk_exit or 1, result.stderr)
                self.assertNotIn("Installed.", result.stdout)
                self.assertIn("Backup retained", result.stderr)
                self.assertEqual(
                    self.config.read_text(),
                    PACKAGE_CONFIG if copy_failure == "restore-config" else ORIGINAL_CONFIG,
                )
                self.assertEqual(
                    self.password.read_text(),
                    PACKAGE_PASSWORD if copy_failure == "restore-password" else ORIGINAL_PASSWORD,
                )
                self.assertFalse(list(self.root.rglob("*.inode-restore.*")))
        backups = list(self.root.glob("backup.*"))
        self.assertEqual(len(backups), 2)
        for backup in backups:
            self.assertEqual(backup.stat().st_mode & 0o777, 0o700)
            self.assertEqual((backup / "config").read_text(), ORIGINAL_CONFIG)
            self.assertEqual((backup / "password").read_text(), ORIGINAL_PASSWORD)


if __name__ == "__main__":
    unittest.main()
