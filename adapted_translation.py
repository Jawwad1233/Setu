"""Application pipeline: explicit memory, local interpretation, then full model inference."""
import time
from bilingual import recall, detect_bengali, repair_translation
from slang import prepare_sentences


def release_temporary_memory(engine):
    if engine.device == 'mps':
        engine.torch.mps.empty_cache()


def translate(engine, sentences, direction, beams, limit, enabled=True, clarification='', mode='Context'):
    started = time.perf_counter()
    outputs = [None] * len(sentences)
    notes, records, stats = [], [], {'curated_matches':0, 'model_sentences':0, 'output_cap_reached':False}
    # Explicit clarification and the off switch must bypass curated text.
    use_context = enabled and mode == 'Context' and not clarification.strip()
    for i, sentence in enumerate(sentences):
        match = recall(sentence, direction) if use_context else None
        if match:
            outputs[i] = match['translation']
            stats['curated_matches'] += 1
            notes.append(f'Line {i+1}: Using a saved correction ({match["id"]}). Native-speaker review pending. Meaning: {match["plain_english"]}')
        else:
            records.append((i, sentence))
    source = [s for _, s in records]
    prepared = source
    interpretation_seconds = 0.0
    if source:
        if use_context and direction == 'en-bn':
            from slang_context import prepare_context
            release_temporary_memory(engine)
            before = time.perf_counter()
            prepared, explanation = prepare_context(source, line_numbers=[i+1 for i,_ in records])
            interpretation_seconds += time.perf_counter()-before
            notes.append('Sentence interpretation:\n'+explanation)
        elif use_context and direction == 'bn-en':
            prepared = source
        else:
            prepared, explanation = prepare_sentences(source, direction, enabled, clarification)
            notes.append(explanation)
        bn_jobs, bn_indices = [], []
        for (i, original), text in zip(records, prepared, strict=True):
            entries = detect_bengali(original) if use_context and direction == 'bn-en' else []
            romanized = bool(entries) and not any('\u0980' <= c <= '\u09ff' for c in original)
            fallback = False
            if entries:
                from bengali_context import normalize
                normalized, bn_notes = normalize(original)
                notes.extend(f'Line {i+1}: '+n for n in bn_notes)
                if normalized is not None:
                    text=normalized
                    romanized=False
                else:
                    fallback=True
            if romanized:
                result = ''
            else:
                result_list, detail = engine.translate([text], direction, int(beams), int(limit))
                result = result_list[0]
                stats['model_sentences'] += 1
                stats['generated_tokens'] = stats.get('generated_tokens',0)+detail.get('generated_tokens',0)
                stats['generation_seconds'] = stats.get('generation_seconds',0)+detail.get('generation_seconds',0)
                stats['output_cap_reached'] |= detail.get('output_cap_reached', False)
            if use_context and direction == 'en-bn':
                result, fixes = repair_translation(original, text, result)
                if fixes: notes.append(f'Line {i+1}: Word correction: '+', '.join(fixes))
            if entries and not fallback:
                from bengali_context import repair_english
                result, bn_fixes = repair_english(original,text,result)
                notes.extend(f'Line {i+1}: '+n for n in bn_fixes)
            outputs[i] = result
            if entries and fallback:
                bn_jobs.append({'text':original,'draft':result,'entries':entries,'mode':'bn-en'})
                bn_indices.append(i)
        if bn_jobs:
            from slang_context import call_worker
            release_temporary_memory(engine)
            before = time.perf_counter()
            revised = call_worker(bn_jobs)
            interpretation_seconds += time.perf_counter()-before
            for i, result in zip(bn_indices, revised, strict=True):
                if result['status'] == 'uncertain' and not outputs[i]:
                    raise ValueError('The Banglish meaning is unclear. Try Bengali script or more context.')
                outputs[i] = result['text']
                notes.append(f'Line {i+1}: Bengali context — {result["reason"]}')
    stats['slang_interpretation_seconds'] = round(interpretation_seconds, 3)
    stats['tokens_per_second'] = round(stats.get('generated_tokens',0)/stats['generation_seconds'],3) if stats.get('generation_seconds') else 0
    stats['seconds'] = round(time.perf_counter()-started, 3)
    return outputs, stats, '\n'.join(notes)
