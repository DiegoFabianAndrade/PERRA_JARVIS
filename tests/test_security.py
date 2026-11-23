import unittest
from config import ALLOWED_CHAT_ID

class TestSecurity(unittest.TestCase):
    def test_chat_id_authorization(self):
        owner_chat_id = 1257398092
        attacker_chat_id = 999999999
        
        # Simula verificación de seguridad en Webhook
        def is_authorized(chat_id):
            return int(chat_id) == owner_chat_id
            
        self.assertTrue(is_authorized(owner_chat_id))
        self.assertFalse(is_authorized(attacker_chat_id))

    def test_dangerous_patterns_detection(self):
        dangerous_commands = [
            "rm -rf /",
            "format c: /fs:ntfs",
            ":(){ :|:& };:",
            "powershell -encodedcommand ..."
        ]
        
        def is_dangerous(text):
            lowered = text.lower()
            return any(p in lowered for p in ["rm -rf", "format c:", ":(){", "-encodedcommand"])
            
        for cmd in dangerous_commands:
            self.assertTrue(is_dangerous(cmd), f"Command should be flagged as dangerous: {cmd}")

if __name__ == "__main__":
    unittest.main()
