import unittest
import json
import time

class TestOfflineOrders(unittest.TestCase):
    def test_order_structure(self):
        order = {
            "id": int(time.time() * 1000),
            "command": "screenshot",
            "args": "toma una captura de pantalla",
            "created_at": time.time(),
            "status": "pending"
        }
        self.assertEqual(order["status"], "pending")
        self.assertIn("screenshot", order["command"])
        
        # Simulate completion
        order["status"] = "completed"
        order["completed_at"] = time.time()
        order["result"] = "Screenshot captured successfully"
        self.assertEqual(order["status"], "completed")
        self.assertIsNotNone(order["completed_at"])

    def test_order_filtering(self):
        orders = [
            {"id": 1, "status": "completed"},
            {"id": 2, "status": "pending"},
            {"id": 3, "status": "pending"}
        ]
        pending = [o for o in orders if o.get("status") == "pending"]
        self.assertEqual(len(pending), 2)
        self.assertEqual([o["id"] for o in pending], [2, 3])

if __name__ == "__main__":
    unittest.main()
