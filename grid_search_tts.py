import argparse
import itertools
import json
import os
import shutil
import time

from voice_clone import generate_speech


def grid_search_tts(
    text: str,
    voice_id: str,
    stability_values: list[float],
    similarity_values: list[float],
    consent: bool,
):
    results = []
    for stab, sim in itertools.product(stability_values, similarity_values):
        res = generate_speech(
            text=text,
            voice_id=voice_id,
            stability=stab,
            similarity_boost=sim,
            use_cache=True,
            consent=consent,
        )
        if res.get("ok"):
            file_path = res.get("file")
            results.append({"stability": stab, "similarity": sim, "file": file_path})
        time.sleep(1)
    return results


def _load_sentences(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get("sentences", [])


def generate_ab_samples(
    sentences_path: str,
    output_dir: str,
    voice_id: str,
    a_stability: float,
    a_similarity: float,
    b_stability: float,
    b_similarity: float,
    consent: bool,
):
    os.makedirs(output_dir, exist_ok=True)
    items = _load_sentences(sentences_path)
    results = []
    for idx, item in enumerate(items, start=1):
        sid = str(item.get("id", idx))
        text = item.get("text", "")
        if not text:
            continue
        res_a = generate_speech(
            text=text,
            voice_id=voice_id,
            stability=a_stability,
            similarity_boost=a_similarity,
            use_cache=True,
            consent=consent,
        )
        if res_a.get("ok"):
            file_a = res_a.get("file")
            if file_a:
                out_a = os.path.join(output_dir, f"out_A_{sid}.wav")
                shutil.copyfile(file_a, out_a)
        res_b = generate_speech(
            text=text,
            voice_id=voice_id,
            stability=b_stability,
            similarity_boost=b_similarity,
            use_cache=True,
            consent=consent,
        )
        if res_b.get("ok"):
            file_b = res_b.get("file")
            if file_b:
                out_b = os.path.join(output_dir, f"out_B_{sid}.wav")
                shutil.copyfile(file_b, out_b)
        results.append({"id": sid, "text": text})
        time.sleep(1)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="TTS grid search and A/B sample generator"
    )
    parser.add_argument("--voice-id", default="21m00Tcm4TlvDq8ikWAM")
    parser.add_argument(
        "--text",
        default="สวัสดีครับ นี่คือการทดสอบเสียงภาษาไทย เพื่อหาค่าที่เหมาะสมที่สุด",
    )
    parser.add_argument("--consent", action="store_true")
    parser.add_argument("--ab", action="store_true")
    parser.add_argument(
        "--sentences", default=os.path.join("mos", "mos_sentences.json")
    )
    parser.add_argument("--output-dir", default=os.path.join("mos", "ab_samples"))
    parser.add_argument("--a-stability", type=float, default=0.4)
    parser.add_argument("--a-similarity", type=float, default=0.1)
    parser.add_argument("--b-stability", type=float, default=0.3)
    parser.add_argument("--b-similarity", type=float, default=0.0)
    parser.add_argument("--stability", nargs="*", type=float, default=[0.3, 0.5, 0.7])
    parser.add_argument("--similarity", nargs="*", type=float, default=[0.5, 0.75, 0.9])
    args = parser.parse_args()
    if args.ab:
        generate_ab_samples(
            sentences_path=args.sentences,
            output_dir=args.output_dir,
            voice_id=args.voice_id,
            a_stability=args.a_stability,
            a_similarity=args.a_similarity,
            b_stability=args.b_stability,
            b_similarity=args.b_similarity,
            consent=args.consent,
        )
    else:
        grid_search_tts(
            text=args.text,
            voice_id=args.voice_id,
            stability_values=args.stability,
            similarity_values=args.similarity,
            consent=args.consent,
        )
