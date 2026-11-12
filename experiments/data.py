"""Dados combinados UMSAB + B2W: python -m experiments.data gera as divisões e o manifesto."""

import csv
import hashlib
import io
import json
import random
import sys
import urllib.request
from collections import Counter, defaultdict

from backend.classifier import LABELS, ROOT, prepare_text
from experiments import train

B2W_REVISION = "4639429ec698d7821fc99a0bc665fa213d9fcd5a"
B2W_URL = (
    "https://raw.githubusercontent.com/americanas-tech/b2w-reviews01/"
    f"{B2W_REVISION}/B2W-Reviews01.csv"
)
B2W_SHA256 = "821fb0bf9f7230b0fba4e4f9fadd75a66d1a9ff0b1657810791d33007eb2ab38"
B2W_RAW = ROOT / "data" / "raw" / "b2w" / "B2W-Reviews01.csv"
MANIFEST_PATH = ROOT / "reports" / "dataset_manifest_combinado.json"
SEED = 42
MIN_CHARS = 10
PER_CLASS = {"test": 500, "validation": 300, "train": 2000}
RATING_MAP = {"1": "negativo", "2": "negativo", "3": "neutro", "4": "positivo", "5": "positivo"}
# Only these two columns are read; reviewer profile fields are never loaded (RNF05).
KEPT_COLUMNS = ("review_text", "overall_rating")
EXAMPLES = ROOT / "data" / "examples"


def key(text: str) -> str:
    return prepare_text(text).casefold()


def download_b2w() -> bytes:
    if not B2W_RAW.exists():
        B2W_RAW.parent.mkdir(parents=True, exist_ok=True)
        print("Baixando B2W-Reviews01 (cerca de 50 MB)...", flush=True)
        with urllib.request.urlopen(B2W_URL, timeout=120) as response:
            payload = response.read(80_000_001)
        if len(payload) > 80_000_000:
            raise ValueError("Arquivo B2W excedeu o tamanho esperado.")
        temp = B2W_RAW.with_suffix(".tmp")
        temp.write_bytes(payload)
        temp.replace(B2W_RAW)
    payload = B2W_RAW.read_bytes()
    if hashlib.sha256(payload).hexdigest() != B2W_SHA256:
        raise ValueError("O hash do B2W difere da fonte fixada. Apague o cache e baixe novamente.")
    return payload


def read_b2w(payload: bytes):
    """Retorna (texto, rótulo) únicos; descarta conflitos, vazios e textos muito curtos."""
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8")))
    missing = set(KEPT_COLUMNS) - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"Colunas ausentes no B2W: {sorted(missing)}")
    groups = defaultdict(list)
    stats = Counter()
    for row in reader:
        stats["rows"] += 1
        text = prepare_text(row["review_text"] or "")
        label = RATING_MAP.get((row["overall_rating"] or "").strip())
        if label is None:
            stats["invalid_rating"] += 1
            continue
        if len(text) < MIN_CHARS:
            stats["empty_or_short"] += 1
            continue
        groups[key(text)].append((text, label))
    unique = []
    for items in groups.values():
        if len({label for _, label in items}) == 1:
            unique.append(items[0])
        else:
            stats["conflicting_duplicate_groups"] += 1
    stats["duplicates_merged"] = sum(len(items) - 1 for items in groups.values())
    return unique, dict(stats)


def example_keys() -> set[str]:
    keys = set()
    for path in EXAMPLES.glob("*.csv"):
        with path.open(encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                if row.get("texto"):
                    keys.add(key(row["texto"]))
    return keys


def umsab_splits():
    train.download_dataset()
    train_rows, _ = train.read_split("train")
    validation, _ = train.read_split("val")
    test, _ = train.read_split("test")
    train_keys = {key(text) for text, _ in train_rows}
    validation = [row for row in validation if key(row[0]) not in train_keys]
    seen = train_keys | {key(text) for text, _ in validation}
    test = [row for row in test if key(row[0]) not in seen]
    return {"train": train_rows, "validation": validation, "test": test}


def b2w_splits(umsab: dict):
    rows, stats = read_b2w(download_b2w())
    blocked = {key(text) for split in umsab.values() for text, _ in split} | example_keys()
    before = len(rows)
    rows = [row for row in rows if key(row[0]) not in blocked]
    stats["removed_overlap_umsab_or_examples"] = before - len(rows)
    stats["available_unique"] = dict(Counter(label for _, label in rows))
    rng = random.Random(SEED)
    by_class = {label: sorted(text for text, y in rows if y == label) for label in LABELS}
    splits = {name: [] for name in PER_CLASS}
    for label in LABELS:
        pool = by_class[label]
        rng.shuffle(pool)
        offset = 0
        for name in ("test", "validation", "train"):
            size = PER_CLASS[name]
            chosen = pool[offset : offset + size]
            if len(chosen) < size:
                raise ValueError(f"B2W não tem exemplos suficientes de {label} para {name}.")
            splits[name].extend((text, label) for text in chosen)
            offset += size
    for name in splits:
        rng.shuffle(splits[name])
    return splits, stats


def split_hash(rows) -> str:
    digest = hashlib.sha256()
    for text, label in rows:
        digest.update(f"{label}\t{text}\n".encode())
    return digest.hexdigest()


def build():
    """Monta as divisões em memória; nada derivado dos textos é gravado no repositório."""
    umsab = umsab_splits()
    b2w, stats = b2w_splits(umsab)
    all_keys = Counter()
    for source in (umsab, b2w):
        for rows in source.values():
            all_keys.update({key(text) for text, _ in rows})
    if any(count > 1 for count in all_keys.values()):
        raise ValueError("Há textos repetidos entre divisões; a separação não é disjunta.")
    combined = {
        "train": umsab["train"] + b2w["train"],
        "validation": umsab["validation"] + b2w["validation"],
    }
    return {"umsab": umsab, "b2w": b2w, "combined": combined, "b2w_stats": stats}


def manifest(data: dict) -> dict:
    def describe(rows):
        return {
            "size": len(rows),
            "classes": dict(sorted(Counter(y for _, y in rows).items())),
            "sha256": split_hash(rows),
        }

    return {
        "description": "Divisões usadas na comparação final de modelos.",
        "seed": SEED,
        "text_key": "prepare_text(texto).casefold()",
        "disjoint_by_normalized_text": True,
        "umsab": {
            "repository": "https://github.com/cardiffnlp/xlm-t",
            "revision": train.REVISION,
            "usage": "Uso acadêmico local; restrições dos datasets originais podem se aplicar.",
            "splits": {name: describe(rows) for name, rows in data["umsab"].items()},
        },
        "b2w": {
            "repository": "https://github.com/americanas-tech/b2w-reviews01",
            "revision": B2W_REVISION,
            "file": "B2W-Reviews01.csv",
            "file_sha256": B2W_SHA256,
            "license": "CC BY-NC-SA 4.0",
            "columns_used": list(KEPT_COLUMNS),
            "columns_discarded": "Todas as demais, incluindo perfil do avaliador (RNF05).",
            "rating_map": {"1-2": "negativo", "3": "neutro", "4-5": "positivo"},
            "min_chars": MIN_CHARS,
            "per_class": PER_CLASS,
            "preparation": data["b2w_stats"],
            "splits": {name: describe(rows) for name, rows in data["b2w"].items()},
        },
        "combined": {name: describe(rows) for name, rows in data["combined"].items()},
        "excluded_from_training": "CSVs de data/examples (demonstração e livraria fictícia).",
    }


def write_manifest(data: dict) -> dict:
    content = manifest(data)
    MANIFEST_PATH.parent.mkdir(exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return content


if __name__ == "__main__":
    try:
        result = write_manifest(build())
    except Exception as exc:
        print(f"Não foi possível preparar os dados: {exc}", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(result["combined"], ensure_ascii=False, indent=2))
    print(json.dumps(result["b2w"]["preparation"], ensure_ascii=False, indent=2))
