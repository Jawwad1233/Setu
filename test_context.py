import json
import unittest
from slang_context_worker import validate, literal_sentence
from slang import normalize_slang


class ContextTests(unittest.TestCase):
    def test_addy_variants_rules_backup(self):
        for text in ["whats the addy", "What's the addy?", "What is your addy?", "Drop the addy."]:
            result, note = normalize_slang(text, "en-bn")
            self.assertIn("address", result)
            self.assertIsNotNone(note)

    def test_model_failure_does_not_invent_text(self):
        for raw in ['not json', '{}', '[]', '{"status":"rewritten","text":""}',
                    '{"status":"rewritten","text":"হ্যালো","reason":"translated"}']:
            result = validate(raw, 'original')
            self.assertEqual(result['text'],'original')
            self.assertEqual(result['status'],'uncertain')

    def test_literal_and_uncertain_preserve_exact_original(self):
        for status in ['literal','uncertain']:
            result = validate(json.dumps(dict(text='changed',status=status,reason='test')), 'Her name is Addy.')
            self.assertEqual(result['text'],'Her name is Addy.')

    def test_physical_context_guards(self):
        for text in ["He placed a bet on the race.", "The soup is too salty.", "She lit the candle.", "They lit a fire.", "She spilled the tea on the floor."]:
            self.assertTrue(literal_sentence(text))
        for text in ["He is salty after losing.", "The concert was lit.", "The soup is salty AF.", "Spill the tea."]:
            self.assertFalse(literal_sentence(text))

    def test_valid_rewrite(self):
        result = validate(json.dumps(dict(text='What is the address?',status='rewritten',reason='address')),'whats the addy')
        self.assertEqual(result['text'],'What is the address?')


if __name__ == '__main__':
    unittest.main()
