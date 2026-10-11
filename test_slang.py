import unittest
from slang import normalize_slang, prepare_sentences, glossary_entries, detect_glossary


class SlangTests(unittest.TestCase):
    def test_music_praise(self):
        for text in ["This song slaps.", "that track really slaps!", "THE BEAT SLAPS", "This album absolutely slaps!!"]:
            with self.subTest(text=text):
                result, note = normalize_slang(text, "en-bn")
                self.assertIn("is really good", result)
                self.assertEqual(note["rule"], "music_slaps")

    def test_literal_and_unsupported_contexts_unchanged(self):
        for text in ["He slaps the table.", "The drummer slaps the drum.",
                     "This song slaps me in the face.", "This song doesn't slap.",
                     "Does this song slap?", "This song slaps, said nobody ever.",
                     "The song is about a man who slaps people.", "I heard that this song slaps.",
                     "This song slaps?", "These slapsticks belong to the band."]:
            with self.subTest(text=text):
                self.assertEqual(normalize_slang(text, "en-bn"), (text, None))

    def test_direction_and_toggle(self):
        text = "This song slaps."
        self.assertEqual(normalize_slang(text, "bn-en"), (text, None))
        prepared, _ = prepare_sentences([text], "en-bn", False)
        self.assertEqual(prepared, [text])

    def test_multiple_lines_preserve_order_and_explain_match(self):
        prepared, explanation = prepare_sentences(["He slaps the table.", "This song slaps."], "en-bn", True)
        self.assertEqual(prepared, ["He slaps the table.", "This song is really good."])
        self.assertIn("Line 2:", explanation)

    def test_full_import_and_detection(self):
        entries = glossary_entries()
        self.assertEqual(len(entries), 248)
        self.assertEqual(len({e['id'] for e in entries}), 248)
        for entry in entries:
            with self.subTest(term=entry['term']):
                self.assertIn(entry['id'], [e['id'] for e in detect_glossary(entry['aliases'][0])])

    def test_context_pairs(self):
        cases = [
            ('The song is fire.', 'The song is excellent.'),
            ('Spill the tea!', 'Tell me the gossip.'),
            ("I'm cooked for tomorrow's exam.", "I'm in serious trouble for tomorrow's exam"),
            ("He's ghosting me.", 'He is ignoring me without explanation.'),
            ('He is ghosting me.', 'He is ignoring me without explanation.'),
            ('He left me on read.', 'He read the messages from me but did not reply.'),
            ('Send me the addy.', 'Send me the address.'),
            ('NGL, that movie was mid.', 'to be honest, that movie was mediocre.'),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                output, note = normalize_slang(source,'en-bn')
                if expected is None:
                    self.assertEqual(output, source)
                else:
                    self.assertEqual(output, expected)
                    self.assertIsNotNone(note)

    def test_literal_homonyms_are_preserved(self):
        for text in ['The building is on fire.', 'Pour the tea.', 'She spilled the tea on him.',
                     'The chicken is cooked.', 'I cooked dinner.', 'The soup is salty.',
                     'The nurse is an RN.', 'The goat ate grass.', 'The bottle has no cap.',
                     'The candle was lit.', 'He reads a book.', 'The ship docked.',
                     'She felt sick.', 'The electrical plug is broken.', 'The score is 41.',
                     'We leave at 6-7.', 'Her name is Addy.']:
            with self.subTest(text=text):
                self.assertEqual(normalize_slang(text,'en-bn'),(text,None))

    def test_clarification_is_explicit_and_validated(self):
        result, note = prepare_sentences(['The food is fire.'],'en-bn',True,'The food is excellent.')
        self.assertEqual(result,['The food is excellent.'])
        self.assertIn('your clarified',note)
        with self.assertRaises(ValueError):
            prepare_sentences(['a','b'],'en-bn',True,'one line')
        with self.assertRaises(ValueError):
            prepare_sentences(['a'],'en-bn',False,'b')


if __name__ == "__main__":
    unittest.main()
