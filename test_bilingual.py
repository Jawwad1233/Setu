import unittest
from unittest.mock import patch
from bilingual import recall, memory_entries, detect_bengali, repair_translation
from adapted_translation import translate

class Engine:
    device='cpu'
    def __init__(self): self.inputs=[]
    def translate(self,texts,direction,beams,limit):
        self.inputs.append((texts,direction))
        return ['MODEL: '+s for s in texts], {'output_cap_reached':False}

class BilingualTests(unittest.TestCase):
    def test_all_saved_corrections_are_retrievable(self):
        for e in memory_entries():
            self.assertEqual(recall(e['source'],'en-bn')['translation'],e['translation'])
            self.assertIsNone(recall(e['source'],'bn-en'))
    def test_no_fuzzy_memory_or_substring_override(self):
        self.assertIsNone(recall('This biryani is not fire.','en-bn'))
        self.assertIsNone(recall('He said: This biryani is fire.','en-bn'))
        self.assertIsNone(recall('That biryani is fire.','en-bn'))
    def test_off_switch_and_clarification_bypass_memory(self):
        engine=Engine()
        result,stats,_=translate(engine,['This biryani is fire.'],'en-bn',5,128,False)
        self.assertEqual(stats['curated_matches'],0)
        result,stats,_=translate(engine,['This biryani is fire.'],'en-bn',5,128,True,'This food is spicy.')
        self.assertEqual(stats['curated_matches'],0)
        self.assertEqual(engine.inputs[-1][0],['This food is spicy.'])
    def test_memory_uses_no_model(self):
        engine=Engine();result,stats,notes=translate(engine,['This biryani is fire.'],'en-bn',5,128)
        self.assertEqual(stats['curated_matches'],1);self.assertEqual(engine.inputs,[])
        self.assertIn('saved correction',notes)
    def test_bn_matching_boundaries(self):
        self.assertTrue(detect_bengali('এত প্যারা নিস না।'))
        self.assertTrue(detect_bengali('mama, eta joss!'))
        self.assertFalse(detect_bengali('মামাবাড়ি'))
        self.assertFalse(detect_bengali('mammal'))
    def test_repairs_need_source_evidence(self):
        self.assertEqual(repair_translation('My electrical plug broke.','', 'খুঁটি ভাঙা')[0],'প্লাগ ভাঙা')
        self.assertEqual(repair_translation('The pole broke.','', 'খুঁটি ভাঙা')[0],'খুঁটি ভাঙা')
        self.assertEqual(repair_translation('My hat is blue.','', 'টুপি নীল')[0],'টুপি নীল')
    def test_mixed_line_order_and_single_sentence_model_calls(self):
        engine=Engine()
        with patch('slang_context.prepare_context',return_value=(['Hello.'], 'one interpretation')):
            result,stats,_=translate(engine,['This biryani is fire.','Hello.'],'en-bn',5,128)
        self.assertEqual(result,['এই বিরিয়ানিটা দারুণ মজার।','MODEL: Hello.'])
        self.assertEqual(stats['model_sentences'],1)
    def test_bn_literal_and_slang_context(self):
        from bengali_context import normalize
        self.assertIn('দুশ্চিন্তা',normalize('eto pera nish na')[0])
        self.assertEqual(normalize('আমার মামা আজ আসবেন।')[0],'আমার মায়ের ভাই আজ আসবেন।')
        self.assertEqual(normalize('এই সমীকরণটা জটিল।')[0],'এই সমীকরণটা জটিল।')
        self.assertIn('অনুচ্ছেদ',normalize('এই প্যারা পড়ো।')[0])
        self.assertIn('দারুণ',normalize('তোর বাইকটা অস্থির!')[0])
        self.assertIn('অস্থির',normalize('ঘুম আসছে না, অস্থির লাগছে।')[0])
        self.assertIn('গানটা',normalize('mama, gaan ta joss!')[0])
    def test_hat_repair_does_not_replace_worn_hat(self):
        got,_=repair_translation('I am wearing a hat, not a bottle cap.','', 'আমি টুপি পরেছি, বোতলের টুপি নয়।')
        self.assertEqual(got,'আমি টুপি পরেছি, বোতলের ঢাকনা নয়।')

    def test_condition_preservation(self):
        from english_context import rewrite
        self.assertEqual(rewrite('LMS to join the competition.')[0],'Like my post to join the competition.')
        self.assertEqual(rewrite('LMS if you are not entering.')[0],'Like my post if you are not entering.')
        self.assertIsNone(rewrite('The LMS platform is offline.'))
    def test_bn_repairs_preserve_relationships_and_insult(self):
        from bengali_context import repair_english
        self.assertEqual(repair_english('আমার মামা','আমার মায়ের ভাই',"My mother's brother")[0],'My maternal uncle')
        self.assertEqual(repair_english('এই প্যারা পড়ো।','এই অনুচ্ছেদ পড়ো।','Read this article.')[0],'Read this paragraph.')
        self.assertIn('bastard',repair_english('শালা, মিথ্যা বলছিস।','বদমাশ, মিথ্যা বলছিস।',"You're lying.")[0])
        self.assertNotIn('bastard',repair_english('সে আমার শালা।','সে আমার শালা।','He is my brother-in-law.')[0])
    def test_lexical_repairs_skip_conflicting_senses(self):
        self.assertEqual(repair_translation('The waterslide survived the flood.','', 'জলোচ্ছ্বাস')[0],'জলোচ্ছ্বাস')
        self.assertEqual(repair_translation('I texted her about a letter.','', 'চিঠি')[0],'চিঠি')

    def test_bn_refinement_and_uncertain_banglish(self):
        engine=Engine()
        with patch('slang_context.call_worker',return_value=[{'text':'This song is awesome.','status':'rewritten','reason':'Praise'}]):
            result,_,_=translate(engine,['mama, tomorrow?'],'bn-en',5,128)
        self.assertEqual(result,['This song is awesome.']);self.assertEqual(engine.inputs,[])
        with patch('slang_context.call_worker',return_value=[{'text':'','status':'uncertain','reason':'ambiguous'}]):
            with self.assertRaises(ValueError):translate(engine,['mama unknownphrase'],'bn-en',5,128)

if __name__=='__main__':unittest.main()
