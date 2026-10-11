# Setu — English ↔ Bangla

Setu (সেতু) means “bridge” in Bangla. I built this project to help my parents and Bangla-speaking relatives communicate, including when internet access is unavailable.

## Current status

Setu is a Python application running locally on a Mac with a browser interface. An iOS version and broader distribution are planned; this repository is the Mac prototype.

## Features

- English-to-Bangla and Bangla-to-English translation with pretrained IndicTrans2 models.
- Optional local interpretation of slang using Qwen through MLX.
- English slang glossary, a Bangladeshi starter glossary, and limited Banglish handling.
- Curated examples and exact-match translation corrections.
- Optional local Bengali and English speech synthesis.
- Side-by-side translation, language switching, phrasebook, and interpretation review.
- Local inference after the initial model downloads.

The project integrates existing pretrained models with custom interface code, glossary handling, context guidance, and correction logic. It does not train a new translation model. Slang coverage is limited and translations can be incorrect; saved corrections require further native-speaker review. Development tests do not establish general translation accuracy.

## Setup

An Apple Silicon Mac and Python 3.12 are recommended. The optional MLX interpreter requires Apple Silicon. Model downloads require several GB of storage and sufficient memory.

Open Terminal in this project folder:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Accept access conditions for both models:

- https://huggingface.co/ai4bharat/indictrans2-en-indic-1B
- https://huggingface.co/ai4bharat/indictrans2-indic-en-1B

Authenticate locally and download them:

```bash
hf auth login
python main.py download
```

Never commit your authentication token. Model weights and local environments are excluded from this repository.

### Optional context interpreter

Its dependencies use a separate environment:

```bash
python3.12 -m venv .slang-venv
.slang-venv/bin/python -m pip install -r requirements-context.lock.txt
.venv/bin/python main.py download-context
```

Without this installation, select **Quick phrase rules** in Settings.

### Optional speech

```bash
.venv/bin/python main.py download-speech
```

### Run

```bash
.venv/bin/python main.py app
```

Keep Terminal open while using the local browser interface. Press Control-C to stop. Default translation uses Apple's GPU through PyTorch MPS. Add `--device cpu --precision fp32` for explicit CPU operation. Add `--keep-both` to retain both translation models if memory permits.

Model revision files record downloaded versions. The translation loader runs custom code supplied by the model authors.

## Project files

- `main.py`: application, translation engine, downloads, and benchmarks.
- `interface.py`, `interface.css`: interface layout and styling.
- `adapted_translation.py`: translation pipeline.
- `slang.py`, `slang_context.py`, `slang_context_worker.py`: slang matching and interpretation.
- `bilingual.py`, `bengali_context.py`, `english_context.py`: language-specific handling.
- `speech.py`: speech synthesis.
- JSON files: glossaries, curated examples, corrections, and model revisions.
- `test_*.py`: regression checks.
- Evaluation and report scripts: development tools.

## Regression checks

```bash
.venv/bin/python -m unittest test_slang test_bilingual test_context
```

Full translation and speech checks require downloaded models.

## Future work

- Review translations with additional Bangla speakers.
- Expand informal Bangla and mixed-language coverage.
- Improve ambiguous-expression handling.
- Explore smaller models and an iOS implementation.
- Expand testing and distribution.

## Credits and terms

- [AI4Bharat IndicTrans2](https://github.com/AI4Bharat/IndicTrans2): translation models.
- [IndicTransToolkit](https://github.com/VarunGumma/IndicTransToolkit): text processing.
- [Qwen3 through MLX](https://huggingface.co/mlx-community/Qwen3-4B-Instruct-2507-4bit): optional interpretation; model card lists Apache-2.0.
- Meta MMS [Bengali](https://huggingface.co/facebook/mms-tts-ben) and [English](https://huggingface.co/facebook/mms-tts-eng): speech models licensed CC BY-NC 4.0, requiring attribution and noncommercial use.
- `bengali_sources.md` records Bangladeshi glossary references. English glossary definitions and examples were supplied as reference material and are not independently verified linguistic facts.

Model weights are not redistributed here. Consult upstream model and dependency terms before redistribution or commercial use. No blanket license is assigned to third-party reference material.

Created by Jawwad Kamal.
