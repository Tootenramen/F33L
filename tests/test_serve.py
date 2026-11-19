import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import serve as S

class Validate(unittest.TestCase):
    def test_accepts_normal_links(self):
        for u in ("https://www.youtube.com/watch?v=abc123", "https://youtu.be/abc123", "https://music.youtube.com/watch?v=x"):
            self.assertEqual(S.validate_url(u), u)
    def test_rejects_everything_else(self):
        bad = ("http://youtube.com/watch?v=a", "https://evil.com/watch?v=a", "https://youtube.com.evil.com/x", "-o /etc/passwd",
               "https://user:pw@youtube.com/x", "https://youtube.com/x y", "file:///c:/x", "", None, "https://youtube.com/" + "a" * 400)
        for u in bad: self.assertIsNone(S.validate_url(u), u)
    def test_host_check_blocks_rebinding(self):
        self.assertTrue(S.host_ok("127.0.0.1:8765", 8765)); self.assertTrue(S.host_ok("localhost:8765", 8765))
        self.assertFalse(S.host_ok("evil.com:8765", 8765)); self.assertFalse(S.host_ok("127.0.0.1:9999", 8765))

if __name__ == "__main__": unittest.main()
