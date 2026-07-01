import unittest
import re
from app.normalizer import (
    normalize_text,
    normalize_for_ai,
    normalize_text_retry,
    normalize_for_ai_retry
)

class TestNormalizer(unittest.TestCase):
    def test_first_layer_normalization(self):
        # 1. Unicode normalization and leading number removal
        self.assertEqual(normalize_text("1376. employee/employer"), "employee/employer")
        self.assertEqual(normalize_text(" 1376) apple "), "apple")
        self.assertEqual(normalize_text("’apple‘"), "'apple'")
        self.assertEqual(normalize_text("“apple”"), '"apple"')
        self.assertEqual(normalize_text("A–B—C"), "A-B-C")
        
        # 2. Trim and spacing
        self.assertEqual(normalize_text("  hello    world  "), "hello world")
        
        # 3. Trailing ellipsis
        self.assertEqual(normalize_text("apple..."), "apple")
        self.assertEqual(normalize_text("apple…"), "apple")
        self.assertEqual(normalize_text("apple.... "), "apple")
        
        # 4. Trailing punctuation
        self.assertEqual(normalize_text("apple."), "apple")
        self.assertEqual(normalize_text("apple?"), "apple")
        self.assertEqual(normalize_text("apple!"), "apple")
        self.assertEqual(normalize_text("apple,;:"), "apple")
        
        # 5. Punctuation in middle remains intact
        self.assertEqual(normalize_text("not.bad but, good"), "not.bad but, good")

    def test_second_layer_splitting(self):
        # Situation A: No spaces in entire text
        self.assertEqual(normalize_for_ai("crafty/cunning/sly"), ["crafty", "cunning", "sly"])
        self.assertEqual(normalize_for_ai("employee/employer"), ["employee", "employer"])
        self.assertEqual(normalize_for_ai("123. announce/proclaim/declare..."), ["announce", "proclaim", "declare"])
        
        # Situation B: Contains spaces
        self.assertEqual(normalize_for_ai("The storm was imminent/impending"), ["The storm was imminent/impending"])
        self.assertEqual(normalize_for_ai("to stifle a yawn/cough/scream"), ["to stifle a yawn/cough/scream"])

    def test_retry_normalization(self):
        # Standard retry cleaning
        self.assertEqual(normalize_text_retry("the pain will subside…"), "the pain will subside")
        
        # Remove parenthetical info at the end
        self.assertEqual(normalize_text_retry("apple (noun)"), "apple")
        self.assertEqual(normalize_text_retry("run [verb]"), "run")
        
        # Strip quotes
        self.assertEqual(normalize_text_retry("'apple'"), "apple")
        self.assertEqual(normalize_text_retry('"apple"'), "apple")
        self.assertEqual(normalize_text_retry("“apple”"), "apple")
        
        # Situation A splitting on retry
        self.assertEqual(normalize_for_ai_retry("crafty/cunning/sly (adj.)"), ["crafty", "cunning", "sly"])

    def test_filename_sanitization(self):
        def sanitize_filename(name: str) -> str:
            return re.sub(r'[\\/*?:"<>|]', '_', name.lower())
            
        self.assertEqual(sanitize_filename("crafty/cunning/sly"), "crafty_cunning_sly")
        self.assertEqual(sanitize_filename("The storm was imminent/impending"), "the storm was imminent_impending")
        self.assertEqual(sanitize_filename("apple?"), "apple_")

if __name__ == "__main__":
    unittest.main()
