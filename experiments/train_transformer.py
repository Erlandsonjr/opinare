"""Ajuste do BERTimbau Base sem consultar o teste: python -m experiments.train_transformer."""

import argparse
import hashlib
import json
import math
import platform
import random
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from backend.classifier import LABELS, ROOT, prepare_text
from experiments import data as datasets
from experiments.train import evaluate_predictions

BASE_MODEL = "neuralmind/bert-base-portuguese-cased"
BASE_REVISION = "94d69c95f98f7d5b2a8700c420230ae10def0baa"
OUTPUT = ROOT / "artifacts" / "bertimbau-sentimento"
CONFIG = {
    "max_length": 128,
    "learning_rate": 2e-5,
    "epochs": 3,
    "per_device_batch": 8,
    "gradient_accumulation": 2,
    "effective_batch": 16,
    "warmup_ratio": 0.1,
    "weight_decay": 0.01,
    "seed": 42,
    "selection": "Maior F1 macro na validação combinada (UMSAB + B2W)",
    "text_preparation": "prepare_text: NFC, URL e @usuário substituídos; acentos, pontuação, "
    "negações e emojis preservados",
    "precision": "fp32 (GPU Pascal sem tensor cores)",
}
SAVED_FILES = (
    "config.json",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def seed_everything(seed: int):
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def batches(rows, size, shuffle, rng=None):
    order = list(range(len(rows)))
    if shuffle:
        rng.shuffle(order)
    for start in range(0, len(order), size):
        yield [rows[index] for index in order[start : start + size]]


def predict_rows(model, tokenizer, texts, device, max_length, batch_size=32):
    import torch

    model.eval()
    predicted = []
    with torch.inference_mode():
        for start in range(0, len(texts), batch_size):
            chunk = [prepare_text(text) for text in texts[start : start + batch_size]]
            inputs = tokenizer(
                chunk, padding=True, truncation=True, max_length=max_length, return_tensors="pt"
            ).to(device)
            logits = model(**inputs).logits
            predicted.extend(LABELS[index] for index in logits.argmax(dim=-1).tolist())
    return predicted


def train(epochs: int, limit: int | None, cpu: bool):
    import torch
    import transformers
    from transformers import (
        AutoModelForSequenceClassification,
        BertTokenizerFast,
        get_linear_schedule_with_warmup,
    )

    config = {**CONFIG, "epochs": epochs}
    seed_everything(config["seed"])
    device = torch.device("cuda" if torch.cuda.is_available() and not cpu else "cpu")
    if device.type == "cuda":
        probe = torch.ones(4, device=device) * 2
        if float(probe.sum()) != 8.0:
            raise RuntimeError("A GPU não executou a operação de teste corretamente.")
    data = datasets.build()
    datasets.write_manifest(data)
    train_rows = data["combined"]["train"]
    validation = data["combined"]["validation"]
    if limit:
        rng = random.Random(config["seed"])
        train_rows = rng.sample(train_rows, min(limit, len(train_rows)))
    label_ids = {label: index for index, label in enumerate(LABELS)}
    tokenizer = BertTokenizerFast.from_pretrained(BASE_MODEL, revision=BASE_REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        revision=BASE_REVISION,
        num_labels=len(LABELS),
        id2label=dict(enumerate(LABELS)),
        label2id=label_ids,
    ).to(device)
    no_decay = ("bias", "LayerNorm.weight")
    groups = [
        {
            "params": [p for n, p in model.named_parameters() if not n.endswith(no_decay)],
            "weight_decay": config["weight_decay"],
        },
        {
            "params": [p for n, p in model.named_parameters() if n.endswith(no_decay)],
            "weight_decay": 0.0,
        },
    ]
    optimizer = torch.optim.AdamW(groups, lr=config["learning_rate"])
    steps_per_epoch = math.ceil(
        math.ceil(len(train_rows) / config["per_device_batch"]) / config["gradient_accumulation"]
    )
    total_steps = steps_per_epoch * config["epochs"]
    scheduler = get_linear_schedule_with_warmup(
        optimizer, int(total_steps * config["warmup_ratio"]), total_steps
    )
    staging = OUTPUT.with_name(OUTPUT.name + ".tmp")
    shutil.rmtree(staging, ignore_errors=True)
    rng = random.Random(config["seed"])
    history, best = [], None
    started = time.perf_counter()
    val_texts = [text for text, _ in validation]
    val_labels = [label for _, label in validation]
    for epoch in range(1, config["epochs"] + 1):
        model.train()
        epoch_start = time.perf_counter()
        running, seen = 0.0, 0
        optimizer.zero_grad()
        for step, chunk in enumerate(
            batches(train_rows, config["per_device_batch"], True, rng), start=1
        ):
            inputs = tokenizer(
                [prepare_text(text) for text, _ in chunk],
                padding=True,
                truncation=True,
                max_length=config["max_length"],
                return_tensors="pt",
            ).to(device)
            labels = torch.tensor([label_ids[y] for _, y in chunk], device=device)
            loss = model(**inputs, labels=labels).loss
            (loss / config["gradient_accumulation"]).backward()
            running += float(loss) * len(chunk)
            seen += len(chunk)
            last = seen == len(train_rows)
            if step % config["gradient_accumulation"] == 0 or last:
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
            if step % 100 == 0:
                print(f"época {epoch} passo {step} perda {running / seen:.4f}", flush=True)
        predicted = predict_rows(model, tokenizer, val_texts, device, config["max_length"])
        metrics = evaluate_predictions(val_labels, predicted)
        record = {
            "epoch": epoch,
            "train_loss": running / seen,
            "validation_accuracy": metrics["accuracy"],
            "validation_f1_macro": metrics["f1_macro"],
            "seconds": round(time.perf_counter() - epoch_start, 1),
        }
        history.append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
        if best is None or metrics["f1_macro"] > best["metrics"]["f1_macro"]:
            best = {"epoch": epoch, "metrics": metrics}
            shutil.rmtree(staging, ignore_errors=True)
            model.save_pretrained(staging, safe_serialization=True)
            tokenizer.save_pretrained(staging)
    elapsed = time.perf_counter() - started
    files = {name: sha256_file(staging / name) for name in SAVED_FILES}
    model_id = (
        "bertimbau-b2w-umsab-"
        + hashlib.sha256(files["model.safetensors"].encode()).hexdigest()[:12]
    )
    code_hash = hashlib.sha256(
        Path(__file__).read_bytes()
        + (ROOT / "experiments" / "data.py").read_bytes()
        + (ROOT / "backend" / "classifier.py").read_bytes()
    ).hexdigest()
    gpu = torch.cuda.get_device_name(0) if device.type == "cuda" else None
    report = {
        "model_id": model_id,
        "model_name": "BERTimbau Base ajustado (UMSAB + B2W)",
        "base_model": BASE_MODEL,
        "base_revision": BASE_REVISION,
        "base_license": "MIT",
        "dataset": "UMSAB português (TweetSentBR) + B2W-Reviews01",
        "source_url": "https://huggingface.co/neuralmind/bert-base-portuguese-cased",
        "training_code_sha256": code_hash,
        "trained_at": datetime.now(UTC).isoformat(),
        "evaluation_split": "validation",
        "test_evaluated": False,
        "seed": config["seed"],
        "configuration": config,
        "limit": limit,
        "best_epoch": best["epoch"],
        "history": history,
        "training_seconds": round(elapsed, 1),
        "hardware": {
            "device": device.type,
            "gpu": gpu,
            "cpu": platform.processor(),
            "os": platform.platform(),
        },
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "cuda": torch.version.cuda,
        },
        "data_manifest": "reports/dataset_manifest_combinado.json",
        "data_hashes": {
            "train": datasets.split_hash(train_rows),
            "validation": datasets.split_hash(validation),
        },
        "samples": {
            "train": len(train_rows),
            "validation": len(validation),
            "test_reserved": len(data["umsab"]["test"]) + len(data["b2w"]["test"]),
        },
        "label_order": list(LABELS),
        "files": files,
        "metrics": best["metrics"],
        "limitations": [
            "Métricas desta seção são de validação; o teste é consultado uma única vez em "
            "reports/comparacao_modelos.json.",
            "Nota 3 do B2W tratada como neutro: aproximação ruidosa da classe neutra.",
            "Ironia, negação, opiniões mistas e mudança de domínio continuam gerando erros.",
            "Exemplos fictícios do painel não foram usados no treinamento nem nas métricas.",
        ],
    }
    (staging / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    shutil.rmtree(OUTPUT, ignore_errors=True)
    staging.replace(OUTPUT)
    (ROOT / "reports" / "bertimbau_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"model": model_id, "best_epoch": best["epoch"], "history": history}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=CONFIG["epochs"])
    parser.add_argument("--limit", type=int, help="Amostra do treino (apenas para fallback).")
    parser.add_argument("--cpu", action="store_true", help="Forçar CPU.")
    args = parser.parse_args()
    try:
        train(args.epochs, args.limit, args.cpu)
    except Exception as exc:
        print(f"Não foi possível treinar o Transformer: {exc}", file=sys.stderr)
        sys.exit(1)
