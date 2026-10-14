import json
import tempfile
import unittest
from pathlib import Path

from audit import AuditLogger, digest_payload


class AuditLoggerTests(unittest.TestCase):
    def test_valid_chain_and_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            logger = AuditLogger(directory)
            logger.append(actor="test", action="created", target="demo", outcome="success", details={"count": 1}, session_id="run-1")
            logger.append(actor="test", action="verified", target="demo", outcome="success", details={"digest": digest_payload({"ok": True})}, session_id="run-1")
            status = logger.verify()
            self.assertTrue(status["valid"])
            self.assertEqual(status["events"], 2)
            self.assertEqual(Path(directory).stat().st_mode & 0o777, 0o700)
            self.assertEqual(logger.key_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(logger.log_path.stat().st_mode & 0o777, 0o600)

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            logger = AuditLogger(directory)
            logger.append(actor="test", action="created", target="demo", outcome="success", details={"count": 1}, session_id="run-1")
            record = json.loads(logger.log_path.read_text())
            record["outcome"] = "failure"
            logger.log_path.write_text(json.dumps(record) + "\n")
            with self.assertRaisesRegex(ValueError, "signature mismatch"):
                logger.verify()

    def test_sensitive_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            logger = AuditLogger(directory)
            with self.assertRaisesRegex(ValueError, "sensitive audit field"):
                logger.append(actor="test", action="bad", target="demo", outcome="failure", details={"api_key": "must-not-log"}, session_id="run-1")


if __name__ == "__main__":
    unittest.main()
