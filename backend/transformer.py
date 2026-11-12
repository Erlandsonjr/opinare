"""Local BERTimbau inference with verified artifacts and complete token coverage."""

import hashlib
import json
import math
import os
import threading
from pathlib import Path

from backend.classifier import LABELS, ModelUnavailable, prepare_text

REQUIRED_FILES = {
    "config.json",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


class TransformerClassifier:
    def __init__(self, directory: Path):
        self.report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
        if self.report["label_order"] != list(LABELS):
            raise ValueError("O relatório contém classes inválidas")
        if not REQUIRED_FILES <= set(self.report["files"]):
            raise ValueError("O relatório não lista todos os arquivos do modelo")
        for name, expected in self.report["files"].items():
            path = directory / name
            if path.name != name or not path.is_file() or sha256_file(path) != expected:
                raise ValueError(f"O arquivo do modelo {name} é inválido")
        config = json.loads((directory / "config.json").read_text(encoding="utf-8"))
        if [config["id2label"].get(str(i)) for i in range(3)] != list(LABELS):
            raise ValueError("O checkpoint contém classes inválidas")
        import torch
        from transformers import AutoModelForSequenceClassification, BertTokenizerFast

        self.torch = torch
        self.lock = threading.Lock()
        device = os.environ.get("OPINARE_DEVICE", "auto")
        if device not in ("auto", "cpu", "cuda"):
            raise ValueError("Dispositivo do modelo inválido")
        if device == "cuda" and not torch.cuda.is_available():
            raise ValueError("CUDA indisponível")
        self.device = (
            "cuda"
            if device == "cuda" or (device == "auto" and torch.cuda.is_available())
            else "cpu"
        )
        self.tokenizer = BertTokenizerFast.from_pretrained(directory, local_files_only=True)
        self.model = (
            AutoModelForSequenceClassification.from_pretrained(
                directory, local_files_only=True, use_safetensors=True
            )
            .to(self.device)
            .eval()
        )
        if [self.model.config.id2label.get(i) for i in range(3)] != list(LABELS):
            raise ValueError("O modelo carregado contém classes inválidas")
        self.version = self.report["model_id"]
        self.max_length = int(self.report["configuration"]["max_length"])
        self.capacity = self.max_length - self.tokenizer.num_special_tokens_to_add(pair=False)
        if self.capacity < 1:
            raise ValueError("Comprimento de tokens inválido")

    @property
    def ready(self) -> bool:
        return True

    def predict_proba(self, texts: list[str]) -> list[dict[str, float]]:
        if not texts:
            return []
        windows = []
        for owner, text in enumerate(texts):
            tokens = self.tokenizer.encode(
                prepare_text(text), add_special_tokens=False, truncation=False
            )
            for start in range(0, max(1, len(tokens)), self.capacity):
                part = tokens[start : start + self.capacity]
                windows.append(
                    (
                        owner,
                        max(1, len(part)),
                        self.tokenizer.build_inputs_with_special_tokens(part),
                    )
                )
        ordered = sorted(enumerate(windows), key=lambda item: len(item[1][2]))
        totals = [[0.0] * 3 for _ in texts]
        weights = [0] * len(texts)
        with self.lock, self.torch.inference_mode():
            for offset in range(0, len(ordered), 16):
                batch = ordered[offset : offset + 16]
                encoded = self.tokenizer.pad(
                    {"input_ids": [item[1][2] for item in batch]}, padding=True, return_tensors="pt"
                )
                encoded = {key: value.to(self.device) for key, value in encoded.items()}
                scores = self.torch.softmax(self.model(**encoded).logits, dim=-1).cpu().tolist()
                for (_, (owner, weight, _)), row in zip(batch, scores, strict=True):
                    if len(row) != 3 or any(not math.isfinite(value) for value in row):
                        raise ModelUnavailable("O modelo retornou pontuações inválidas.")
                    for i, value in enumerate(row):
                        totals[owner][i] += weight * value
                    weights[owner] += weight
        return [
            {label: totals[owner][i] / weights[owner] for i, label in enumerate(LABELS)}
            for owner in range(len(texts))
        ]

    def predict(self, texts: list[str]) -> list[str]:
        scores = self.predict_proba(texts)
        return [max(LABELS, key=row.get) for row in scores]
