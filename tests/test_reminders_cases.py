import datetime
import unittest
from azure.function_app import parse_reminder_expression, BOGOTA_TZ

class TestReminders(unittest.TestCase):
    def test_reminder_cases(self):
        cases = [
            ("recuerdame en 15 minutos sacar la ropa", "sacar la ropa"),
            ("recuerdame a las 5:30 pm revisar el correo", "revisar el correo"),
            ("avisame a las 11:00 am reunion de equipo", "reunion de equipo"),
            ("recuerdame comprar cafe en 20 minutos", "comprar cafe"),
            ("haz un recordatorio a las 9 pm leer el libro", "leer el libro"),
            ("crear recordatorio en 45 min apagar horno", "apagar horno"),
            ("avisame de terminar el reporte en 10 minutos", "terminar el reporte")
        ]
        
        now = datetime.datetime.now(BOGOTA_TZ)
        for text, expected_task in cases:
            task, target_dt = parse_reminder_expression(text)
            self.assertIsNotNone(task, f"Failed parsing: {text}")
            self.assertIn(expected_task.lower(), task.lower(), f"Expected '{expected_task}' in '{task}'")
            self.assertGreater(target_dt, now, f"Target '{target_dt}' should be in future of '{now}'")

if __name__ == "__main__":
    unittest.main()

