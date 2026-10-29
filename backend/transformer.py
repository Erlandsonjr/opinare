"""Inferência local de um checkpoint português fixado, sem código remoto ou downloads."""

import hashlib
import importlib.metadata
import json
import threading
import unicodedata
from pathlib import Path

import numpy as np

from backend.vendor.pysentimiento_preprocessing import preprocess_tweet

ROOT = Path(__file__).resolve().parents[1]
MODEL_NAME = "pysentimiento/bertweet-pt-sentiment"
REVISION = "726612815d49447cbfe3f55bbfc2993c1f5fad10"
MODEL_DIR = ROOT / "var" / "models" / "bertweet-pt"
REPORT_PATH = ROOT / "reports" / "transformer_functional_check.json"
LABEL_MAP = {"NEG": "negativo", "NEU": "neutro", "POS": "positivo"}
MAX_TOKENS = 128
BATCH_SIZE = 8
FILE_HASHES = {
    "config.json": "7f0b6fbd123333201c8a60db66c159ad204e236bccfd2c1184df70c70a4fda73",
    "tokenizer_config.json": "b5c75a92c5ffb7276ec8e9ecff387d631faddb7be75a296e35c08979004e1400",
    "special_tokens_map.json": "d05497f1da52c5e09554c0cd874037a083e1dc1b9cfd48034d1c717f1afc07a7",
    "added_tokens.json": "73912929ac0f567224032a57d3b3e6a54613afcdc851aba46c3059b4d4ef5254",
    "vocab.txt": "fb6b15bc5d77bef93b8ddbd86e32bda786d4394029b2a9a1d060edb58a7890f1",
    "bpe.codes": "398a63a3ea4137a5a4205e5913cf8e0cccc4dee7a461dc385ea50546a0f543c4",
    "model.safetensors": "ff666dd48ce086345516ff2e2ee1e38a90235505d1193ed64461cf295875bace",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify_assets(directory: Path = MODEL_DIR):
    for name, expected in FILE_HASHES.items():
        if sha256_file(directory / name) != expected:
            raise ValueError(f"O arquivo do modelo {name} está diferente da versão fixada.")


def model_version() -> str:
    identity = {
        "revision": REVISION,
        "files": FILE_HASHES,
        "runtime_code": hashlib.sha256(
            Path(__file__).read_text(encoding="utf-8").encode()
        ).hexdigest(),
        "preprocessing_code": hashlib.sha256(
            (ROOT / "backend/vendor/pysentimiento_preprocessing.py")
            .read_text(encoding="utf-8")
            .encode()
        ).hexdigest(),
        "libraries": {
            name: importlib.metadata.version(name) for name in ("torch", "transformers", "emoji")
        },
    }
    signature = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:12]
    return f"bertweet-pt-{signature}"


def token_windows(token_ids: list[int], capacity: int) -> list[list[int]]:
    """Preserva todos os tokens; textos longos não são cortados silenciosamente."""
    if capacity < 1:
        raise ValueError("Capacidade de tokens inválida.")
    return [
        token_ids[start : start + capacity] for start in range(0, len(token_ids), capacity)
    ] or [[]]


def prepare_portuguese_text(text: str) -> str:
    text = " ".join(unicodedata.normalize("NFC", text).split())
    # Use upstream Portuguese preprocessing before the tokenizer. Keeping char_replace
    # disabled prevents upstream's legacy character map from discarding ❤ in ❤️.
    return preprocess_tweet(text, lang="pt", char_replace=False)


class TransformerPipeline:
    classes_ = np.array(["negativo", "neutro", "positivo"])

    def __init__(self, directory: Path = MODEL_DIR):
        verify_assets(directory)
        import torch
        from transformers import BertweetTokenizer, RobertaForSequenceClassification

        torch.set_num_threads(4)
        self.torch = torch
        self.lock = threading.Lock()
        self.tokenizer = BertweetTokenizer.from_pretrained(
            directory,
            normalization=False,
            local_files_only=True,
        )
        # Concrete built-in architecture and safetensors: no remote Python/pickle weights.
        self.model = RobertaForSequenceClassification.from_pretrained(
            directory,
            local_files_only=True,
            use_safetensors=True,
        ).eval()
        mapping = self.model.config.id2label
        if mapping != {0: "NEG", 1: "NEU", 2: "POS"}:
            raise ValueError("O checkpoint não contém o mapeamento esperado das três classes.")
        self.output_labels = [LABEL_MAP[mapping[index]] for index in range(3)]
        self.version = model_version()

    def predict(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.array([], dtype=str)
        with self.lock, self.torch.inference_mode():
            chunks, owners, weights = [], [], []
            capacity = MAX_TOKENS - self.tokenizer.num_special_tokens_to_add(False)
            for owner, text in enumerate(texts):
                text = prepare_portuguese_text(text)
                tokens = self.tokenizer.encode(text, add_special_tokens=False, truncation=False)
                for window in token_windows(tokens, capacity):
                    chunks.append(self.tokenizer.build_inputs_with_special_tokens(window))
                    owners.append(owner)
                    weights.append(max(1, len(window)))
            scores = np.zeros((len(texts), 3), dtype=float)
            for offset in range(0, len(chunks), BATCH_SIZE):
                inputs = self.tokenizer.pad(
                    {"input_ids": chunks[offset : offset + BATCH_SIZE]},
                    padding=True,
                    return_tensors="pt",
                )
                probabilities = (
                    self.torch.softmax(self.model(**inputs).logits, dim=-1).cpu().numpy()
                )
                if not np.isfinite(probabilities).all():
                    raise ValueError("O modelo retornou valores inválidos.")
                weighted = probabilities * np.array(weights[offset : offset + BATCH_SIZE])[:, None]
                np.add.at(scores, owners[offset : offset + BATCH_SIZE], weighted)
            # Length weighting avoids giving a short final fragment a full window's weight.
            return np.array([self.output_labels[index] for index in scores.argmax(axis=1)])


def load_transformer_bundle() -> dict:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    if report["model_id"] != model_version():
        raise ValueError("O relatório não corresponde à versão do modelo. Execute preparar.ps1.")
    pipeline = TransformerPipeline()
    return {"model_id": pipeline.version, "pipeline": pipeline, "report": report}
