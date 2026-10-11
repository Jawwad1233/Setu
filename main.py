"""Local full-size IndicTrans2 app and Apple GPU benchmark."""
import argparse
import gc
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("HF_HUB_CACHE", str(ROOT / ".cache" / "hub"))
os.environ.setdefault("HF_MODULES_CACHE", str(ROOT / ".cache" / "modules"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("GRADIO_ANALYTICS_ENABLED", "false")

MODELS = {
    "en-bn": ("ai4bharat/indictrans2-en-indic-1B", "eng_Latn", "ben_Beng"),
    "bn-en": ("ai4bharat/indictrans2-indic-en-1B", "ben_Beng", "eng_Latn"),
}
SAMPLES = {
    "en-bn": "My friend and I went to the market in Dhaka yesterday. We bought fresh vegetables and talked about our plans for the weekend.",
    "bn-en": "গতকাল আমি আর আমার বন্ধু ঢাকার বাজারে গিয়েছিলাম। আমরা তাজা সবজি কিনেছি এবং সপ্তাহান্তের পরিকল্পনা নিয়ে কথা বলেছি।",
}


def download():
    from huggingface_hub import HfApi, snapshot_download
    from huggingface_hub.errors import GatedRepoError
    lock_path = ROOT / "models.lock.json"
    previous = json.loads(lock_path.read_text()) if lock_path.exists() else {}
    locked = {}
    for model, _, _ in MODELS.values():
        revision = previous.get(model) or HfApi().model_info(model).sha
        print(f"Downloading {model} at {revision}", flush=True)
        try:
            snapshot_download(model, revision=revision,
                              allow_patterns=["*.json", "*.py", "*.safetensors", "*.model", "*.txt", "model.SRC", "model.TGT"])
        except GatedRepoError:
            raise SystemExit(
                f"Model access required: https://huggingface.co/{model}\n"
                "Accept the conditions for both full models, then run '.venv/bin/hf auth login' "
                "in Terminal and retry this download."
            ) from None
        locked[model] = revision
    lock_path.write_text(json.dumps(locked, indent=2) + "\n")
    print("Both full models downloaded. Revisions saved in models.lock.json.")


class Engine:
    def __init__(self, precision="fp16", device="mps", keep_both=False):
        import torch
        from IndicTransToolkit import IndicProcessor
        self.torch = torch
        if device == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("Apple GPU unavailable. Run 'doctor', or explicitly choose --device cpu.")
        self.device = device
        self.dtype = {"fp16": torch.float16, "fp32": torch.float32}[precision]
        self.processor = IndicProcessor(inference=True)
        self.keep_both = keep_both
        self.loaded = {}
        self.mutex = threading.Lock()
        lock_path = ROOT / "models.lock.json"
        if not lock_path.exists():
            raise RuntimeError("Run 'python main.py download' before starting translation.")
        self.revisions = json.loads(lock_path.read_text())

    def load(self, direction):
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        if direction in self.loaded:
            return self.loaded[direction]
        if not self.keep_both:
            self.loaded.clear()
            gc.collect()
            if self.device == "mps":
                self.torch.mps.empty_cache()
        model_id = MODELS[direction][0]
        opts = dict(revision=self.revisions[model_id], trust_remote_code=True,
                    local_files_only=True)
        tokenizer = AutoTokenizer.from_pretrained(model_id, **opts)
        if tokenizer.src_spm.get_piece_size() == 0 or tokenizer.tgt_spm.get_piece_size() == 0:
            raise RuntimeError("Tokenizer files are missing. Run 'python main.py download', then restart the app.")
        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_id, **opts, torch_dtype=self.dtype,
            attn_implementation="eager", use_safetensors=True,
        ).to(self.device).eval()
        self.loaded[direction] = (tokenizer, model)
        return tokenizer, model

    def sync(self):
        if self.device == "mps":
            self.torch.mps.synchronize()

    def translate(self, sentences, direction, beams=5, max_new_tokens=128):
        with self.mutex:
            tokenizer, model = self.load(direction)
            _, source, target = MODELS[direction]
            self.sync()
            start = time.perf_counter()
            prepared = self.processor.preprocess_batch(sentences, src_lang=source, tgt_lang=target)
            inputs = tokenizer(prepared, padding=True, truncation=False, return_tensors="pt")
            # The base models are for short inputs; avoid silently truncating a benchmark.
            input_length = inputs["input_ids"].shape[1]
            if input_length > 256:
                raise ValueError(f"Input has {input_length} tokens; split it into shorter sentences (limit 256).")
            inputs = inputs.to(self.device)
            self.sync()
            generate_start = time.perf_counter()
            with self.torch.inference_mode():
                output = model.generate(**inputs, num_beams=int(beams), do_sample=False,
                                        max_new_tokens=int(max_new_tokens), use_cache=True)
            self.sync()
            generate_seconds = time.perf_counter() - generate_start
            ids = output.cpu().tolist()
            special = set(tokenizer.all_special_ids)
            tokens = sum(sum(token not in special for token in row) for row in ids)
            eos = tokenizer.eos_token_id
            capped = [len(row) - 1 >= max_new_tokens and eos not in row[1:] for row in ids]
            decoded = tokenizer.batch_decode(ids, skip_special_tokens=True,
                                             clean_up_tokenization_spaces=True)
            translations = self.processor.postprocess_batch(decoded, lang=target)
            elapsed = time.perf_counter() - start
            return translations, dict(seconds=elapsed, generation_seconds=generate_seconds,
                                      generated_tokens=tokens, tokens_per_second=tokens / generate_seconds,
                                      sentences_per_second=len(sentences) / elapsed,
                                      padded_input_tokens=input_length, output_cap_reached=any(capped))


def doctor():
    import platform
    import psutil
    import torch
    import transformers
    from IndicTransToolkit import IndicProcessor
    data = dict(python=platform.python_version(), architecture=platform.machine(),
                torch=torch.__version__, transformers=transformers.__version__,
                memory_gib=round(psutil.virtual_memory().total / 2**30, 1),
                mps_available=torch.backends.mps.is_available())
    if data["mps_available"]:
        a = torch.ones((256, 256), device="mps")
        data["gpu_matrix_test"] = bool((a @ a)[0, 0].item() == 256)
    processor = IndicProcessor(inference=True)
    data["bangla_preprocess_test"] = bool(processor.preprocess_batch(
        ["আমি ভালো আছি।"], src_lang="ben_Beng", tgt_lang="eng_Latn"))
    print(json.dumps(data, indent=2))


def app(args):
    import gradio as gr
    from speech import Speech
    from slang import prepare_sentences, glossary_entries, glossary_rows
    voice = Speech()
    engine = Engine(args.precision, args.device, args.keep_both)
    if args.keep_both:
        for direction in MODELS:
            engine.load(direction)

    def run(text, direction, beams, limit, slang_enabled, clarification, slang_mode):
        sentences = [line.strip() for line in text.splitlines() if line.strip()]
        if not sentences:
            return "", "Enter a sentence.", None, "", [], gr.update(interactive=False)
        if len(sentences) > 32:
            raise gr.Error("Use up to 32 sentences at a time.")
        try:
            from adapted_translation import translate
            translations, stats, explanation = translate(engine, sentences, direction, beams, limit,
                                                          slang_enabled, clarification, slang_mode)
            translated = "\n".join(translations)
            rows = glossary_rows(sentences, direction) if slang_enabled else []
            return translated, json.dumps(stats, indent=2), (translated, direction), explanation, rows, gr.update(interactive=True)
        except Exception as exc:
            raise gr.Error(str(exc)) from exc

    def listen(translation):
        if not translation:
            raise gr.Error("Translate a sentence first, then click Listen.")
        try:
            return voice.synthesize(*translation)
        except Exception as exc:
            raise gr.Error(str(exc)) from exc

    from interface import HEADER, FOOTER, theme

    def reset_result():
        return "", "", None, None, "", [], gr.update(interactive=False)

    with gr.Blocks(title="Setu · English & Bangla", analytics_enabled=False) as demo:
        gr.HTML(HEADER)
        with gr.Column(elem_id="workspace"):
            with gr.Row(elem_id="language-bar"):
                direction = gr.Radio([("English → বাংলা", "en-bn"), ("বাংলা → English", "bn-en")],
                                     value="en-bn", label="Translation direction", show_label=False,
                                     container=False, elem_id="direction")
                swap = gr.Button("⇄  Swap languages", elem_id="swap", scale=0, min_width=164)
            with gr.Row(elem_id="translation-columns"):
                with gr.Column(elem_classes="translation-card", min_width=260):
                    gr.HTML('<p class="card-heading">YOUR WORDS</p>')
                    source = gr.Textbox(lines=5, max_lines=10, label="Text to translate", show_label=False,
                                        placeholder="What would you like to say?", container=False,
                                        elem_id="source")
                    with gr.Row(elem_id="input-actions"):
                        slang_enabled = gr.Checkbox(value=True, label="Understand slang", container=False,
                                                    elem_id="slang-switch")
                        clear = gr.Button("Clear", elem_id="clear", scale=0)
                    button = gr.Button("Translate  →", variant="primary", elem_id="translate")
                with gr.Column(elem_classes="translation-card", elem_id="target-card", min_width=260):
                    gr.HTML('<p class="card-heading">THE TRANSLATION</p>')
                    output = gr.Textbox(lines=5, max_lines=10, label="Translation", show_label=False,
                                        placeholder="A new way to say it…", interactive=False,
                                        container=False, buttons=["copy"], elem_id="translation")
                    listen_button = gr.Button("▷  Listen to translation", elem_id="listen", interactive=False)
                    audio = gr.Audio(label="Translation audio", show_label=False, interactive=False,
                                     autoplay=True, elem_id="audio")
            gr.Markdown("TRY A LITTLE SOMETHING", elem_id="try-label")
            with gr.Row(elem_id="example-row"):
                sample_music = gr.Button("This song slaps!", elem_classes="example-chip", scale=1, min_width=140)
                sample_hello = gr.Button("How are you?", elem_classes="example-chip", scale=1, min_width=140)
                sample_bangla = gr.Button("তোমার নাম কী?", elem_classes="example-chip", scale=1, min_width=140)

        with gr.Tabs(elem_id="details"):
            with gr.Tab("Meaning & slang"):
                gr.Markdown("Slang can mean different things in different contexts. See what was interpreted, "
                            "or clarify a phrase when it misses the mark.", elem_classes="helper-copy")
                interpretation = gr.Textbox(label="How your words were understood", interactive=False, lines=2,
                                            placeholder="Translate something to see the interpretation.")
                with gr.Accordion("A meaning needs a little help?", open=False, elem_classes="disclosure"):
                    gr.Markdown("Write your intended meaning in plain English, one line for each original line. "
                                "Then press Translate again. Available for English → Bangla.", elem_classes="helper-copy")
                    clarification = gr.Textbox(lines=2, label="Your intended meaning", placeholder="For example: This song is really good.")
                with gr.Accordion("Possible slang in your text", open=False, elem_classes="disclosure"):
                    detected = gr.Dataframe(headers=["Line", "Expression", "Supplied meaning", "Status"],
                                            datatype=["number", "str", "str", "str"], interactive=False)
                gr.Markdown("**Context matters.** A local interpreter uses 248 English entries, 12 Bengali entries, and saved corrections. "
                            "Uncertain meanings are kept unchanged. Check the interpretation: slang can still be misunderstood.",
                            elem_classes="helper-copy")
            with gr.Tab("Phrasebook"):
                gr.Markdown("### A little context goes a long way\nExplore English slang and a Bangladeshi starter glossary, with meanings and examples.",
                            elem_classes="helper-copy")
                from bilingual import bengali_entries, memory_entries
                entries = {entry["term"]: entry for entry in glossary_entries() + bengali_entries()}
                term = gr.Dropdown(choices=list(entries), label="Find an expression", filterable=True)
                definition = gr.Textbox(label="Meaning & examples", interactive=False, lines=7)
                def lookup(name):
                    entry = entries.get(name)
                    if not entry:
                        return ""
                    saved = next((r for r in memory_entries() if r['id']==entry['id']), None)
                    suggested = saved['translation'] if saved else entry.get('example_translation','')
                    return (entry["definition"] + "\n\nExamples:\n" + "\n".join(entry["examples"]) +
                            ("\n\nReference wording:\n" + suggested if suggested else "") +
                            "\n\nReview status: " + entry["review_status"] +
                            ("\nSource: " + entry["source"] if entry.get("source") else ""))
                term.change(lookup, [term], [definition])
            with gr.Tab("Settings"):
                gr.Markdown("### Make it yours\nTranslation and speech are generated on your Mac.", elem_classes="helper-copy")
                slang_mode = gr.Radio([("Understand the sentence", "Context"), ("Quick phrase rules", "Rules")],
                                      value="Context", label="Slang interpretation",
                                      info="Sentence interpretation handles varied wording and takes a few extra seconds.")
                with gr.Accordion("Advanced translation settings", open=False, elem_classes="disclosure"):
                    beams = gr.Slider(1, 10, value=5, step=1, label="Search alternatives",
                                      info="Higher values explore more options and take longer.")
                    limit = gr.Slider(32, 256, value=128, step=32, label="Output length limit (tokens)")
                    stats = gr.Textbox(label="Last translation performance", elem_id="stats", interactive=False)
                gr.Markdown("Use one short sentence per line. Speech supports up to 1,500 translated characters. "
                            "Voices are generated with Meta MMS; Bangladeshi pronunciation still needs review.",
                            elem_classes="helper-copy")
        gr.HTML(FOOTER)
        spoken_translation = gr.State(None)
        result_components = [output, stats, spoken_translation, audio, interpretation, detected, listen_button]
        button.click(reset_result, outputs=result_components, concurrency_id="translation-and-speech").then(
            run, [source, direction, beams, limit, slang_enabled, clarification, slang_mode],
            [output, stats, spoken_translation, interpretation, detected, listen_button],
            concurrency_limit=1, concurrency_id="translation-and-speech")
        listen_button.click(listen, [spoken_translation], [audio], concurrency_limit=1,
                            concurrency_id="translation-and-speech")
        source.input(lambda: "", outputs=[clarification], queue=False)
        direction.change(lambda: ("", *reset_result()), outputs=[clarification, *result_components],
                         concurrency_id="translation-and-speech")
        clear.click(lambda: ("", "", *reset_result()), outputs=[source, clarification, *result_components],
                    concurrency_id="translation-and-speech")
        swap.click(lambda d, result: ("bn-en" if d == "en-bn" else "en-bn", result or "", "", *reset_result()),
                   [direction, output], [direction, source, clarification, *result_components],
                   concurrency_id="translation-and-speech")
        for sample_button, sample_text, sample_direction in [
            (sample_music, "This song slaps!", "en-bn"), (sample_hello, "How are you?", "en-bn"),
            (sample_bangla, "তোমার নাম কী?", "bn-en")]:
            sample_button.click(lambda t=sample_text, d=sample_direction: (t, d, "", *reset_result()),
                                outputs=[source, direction, clarification, *result_components],
                                concurrency_id="translation-and-speech")
    demo.queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1", server_port=getattr(args, "port", 7860), share=False,
        inbrowser=not getattr(args, "no_browser", False), theme=theme(),
        css_paths=[ROOT / "interface.css"], footer_links=[])



def benchmark_case(args):
    import psutil
    engine = Engine(args.precision, args.device, args.keep_both)
    if args.keep_both:
        for direction in MODELS:
            engine.load(direction)
    engine.load(args.direction)
    engine.translate([SAMPLES[args.direction]], args.direction, args.beams, args.tokens)
    peak = {"sampled_peak_rss_gib": 0.0, "sampled_peak_mps_driver_gib": 0.0}
    stop = threading.Event()
    process = psutil.Process()

    def sample():
        while not stop.is_set():
            peak["sampled_peak_rss_gib"] = max(peak["sampled_peak_rss_gib"], process.memory_info().rss / 2**30)
            if args.device == "mps":
                peak["sampled_peak_mps_driver_gib"] = max(
                    peak["sampled_peak_mps_driver_gib"], engine.torch.mps.driver_allocated_memory() / 2**30)
            stop.wait(0.05)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    runs = []
    try:
        for _ in range(args.repeats):
            outputs, stats = engine.translate([SAMPLES[args.direction]] * args.batch,
                                               args.direction, args.beams, args.tokens)
            runs.append(stats)
    finally:
        stop.set()
        sampler.join()
    result = dict(status="ok", batch=args.batch, precision=args.precision, device=args.device,
                  direction=args.direction, beams=args.beams, max_new_tokens=args.tokens,
                  keep_both=args.keep_both, runs=runs, example_translation=outputs[0], **peak)
    result["models"] = engine.revisions
    result["torch"] = engine.torch.__version__
    Path(args.result).write_text(json.dumps(result, indent=2) + "\n")


def benchmark(args):
    directory = ROOT / "results" / time.strftime("%Y%m%d-%H%M%S")
    directory.mkdir(parents=True)
    summary = directory / "summary.jsonl"
    for batch in args.batches:
        result_path = directory / f"batch-{batch}.json"
        command = [sys.executable, str(Path(__file__).resolve()), "case", "--batch", str(batch),
                   "--precision", args.precision, "--device", args.device, "--direction", args.direction,
                   "--beams", str(args.beams), "--tokens", str(args.tokens), "--repeats", str(args.repeats),
                   "--result", str(result_path)]
        if args.keep_both:
            command.append("--keep-both")
        print(f"Testing batch {batch} ({args.precision}, {args.direction})…", flush=True)
        with (directory / f"batch-{batch}.log").open("w") as log:
            try:
                run = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout)
                result = json.loads(result_path.read_text()) if run.returncode == 0 else {
                    "status": "failed", "batch": batch, "exit_code": run.returncode}
            except subprocess.TimeoutExpired:
                result = {"status": "timeout", "batch": batch}
        with summary.open("a") as stream:
            stream.write(json.dumps(result) + "\n")
        print(json.dumps(result), flush=True)
        if result["status"] != "ok":
            print(f"Stopped. Inspect {directory / f'batch-{batch}.log'} for the cause.")
            break
    print(f"Results: {directory}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("download")
    sub.add_parser("download-speech")
    sub.add_parser("download-context")
    for name in ["app", "benchmark", "case"]:
        p = sub.add_parser(name)
        p.add_argument("--precision", choices=["fp16", "fp32"], default="fp16")
        p.add_argument("--device", choices=["mps", "cpu"], default="mps")
        p.add_argument("--keep-both", action="store_true")
        if name == "app":
            p.add_argument("--port", type=int, default=7860)
            p.add_argument("--no-browser", action="store_true")
        if name != "app":
            p.add_argument("--direction", choices=list(MODELS), default="en-bn")
            p.add_argument("--beams", type=int, choices=range(1, 11), default=5)
            p.add_argument("--tokens", type=int, choices=[64, 128, 256], default=128)
            p.add_argument("--repeats", type=int, choices=range(1, 11), default=3)
        if name == "benchmark":
            p.add_argument("--batches", type=int, nargs="+", default=[1, 2, 4, 8, 16, 32])
            p.add_argument("--timeout", type=int, default=300)
        if name == "case":
            p.add_argument("--batch", type=int, required=True)
            p.add_argument("--result", required=True)
    args = parser.parse_args()
    if args.command == "benchmark" and (any(x < 1 for x in args.batches) or args.timeout < 1):
        parser.error("Batch sizes and timeout must be positive.")
    if args.command == "doctor":
        doctor()
    elif args.command == "download":
        download()
    elif args.command == "download-speech":
        from speech import download_speech
        download_speech()
    elif args.command == "download-context":
        from slang_context import download_context
        download_context()
    elif args.command == "app":
        app(args)
    elif args.command == "benchmark":
        benchmark(args)
    else:
        benchmark_case(args)


if __name__ == "__main__":
    main()
