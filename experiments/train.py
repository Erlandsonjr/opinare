"""Treine o baseline sem consultar o teste: python -m experiments.train."""

import argparse
import hashlib
import json
import platform
import sys
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import joblib
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import FeatureUnion, Pipeline

from backend.classifier import LABELS, MODEL_PATH, ROOT, prepare_text

REVISION = "874214d64d96599eb869a033c22ec2cc57d19256"
BASE_URL = (
    f"https://raw.githubusercontent.com/cardiffnlp/xlm-t/{REVISION}/data/sentiment/portuguese"
)
RAW = ROOT / "data" / "raw" / "umsab-pt"
LABEL_MAP = {"0": "negativo", "1": "neutro", "2": "positivo"}
EXPECTED_HASHES = {
    "train_text.txt": "7d4ef66e226d073e527a2b7164351cf9c26f2297608e872d0c8c586dce9118ac",
    "train_labels.txt": "1225a2d319fe4831e1dcb859a51e21c6a8a40c627f4a18c4e872554c385d23f5",
    "val_text.txt": "4a0ab0ef9ce458524fc97279c5c3fc47562d21312ca90972feb674f8ba0f8af3",
    "val_labels.txt": "2728c5af0a67fdb89dfbab4663e5df365c529bb7c513192e829771ebe16aef65",
    "test_text.txt": "7509d97cb78f7c9796fe2d6814428febf138e7c4c76285745cc8f05a514b94eb",
    "test_labels.txt": "7977cc5b0346f7ddab596fa6655ee7d2fe9f36c77129bfc14f3307d607a91761",
}


def download_dataset():
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for split in ("train", "val", "test"):
        for kind in ("text", "labels"):
            name = f"{split}_{kind}.txt"
            target = RAW / name
            if not target.exists():
                print(f"Baixando UMSAB português: {name}", flush=True)
                with urllib.request.urlopen(f"{BASE_URL}/{name}", timeout=60) as response:
                    payload = response.read(5_000_001)
                if len(payload) > 5_000_000:
                    raise ValueError("Arquivo de dados excedeu o tamanho esperado.")
                target.write_bytes(payload)
            payload = target.read_bytes()
            if hashlib.sha256(payload).hexdigest() != EXPECTED_HASHES[name]:
                raise ValueError(f"O hash de {name} difere da fonte fixada. Verifique o cache.")
            manifest[name] = {
                "sha256": hashlib.sha256(payload).hexdigest(),
                "lines": len(payload.decode("utf-8").splitlines()),
            }
    manifest_path = ROOT / "reports" / "dataset_manifest.json"
    manifest_path.parent.mkdir(exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "dataset": "UMSAB / Portuguese (SentiBR / TweetSentBR)",
                "repository": "https://github.com/cardiffnlp/xlm-t",
                "revision": REVISION,
                "files": manifest,
                "usage": "Uso acadêmico local; textos brutos não redistribuídos no repositório.",
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def read_split(split: str):
    texts = (RAW / f"{split}_text.txt").read_text(encoding="utf-8").splitlines()
    labels = (RAW / f"{split}_labels.txt").read_text(encoding="utf-8").splitlines()
    if len(texts) != len(labels):
        raise ValueError(f"Textos e rótulos desalinhados em {split}.")
    groups = defaultdict(list)
    for text, label in zip(texts, labels, strict=True):
        if label not in LABEL_MAP:
            raise ValueError(f"Rótulo desconhecido em {split}: {label}")
        key = prepare_text(text).casefold()
        if key:
            groups[key].append((text, LABEL_MAP[label]))
    # Drop conflicting duplicates, rather than making arbitrary label decisions.
    clean = [items[0] for items in groups.values() if len({y for _, y in items}) == 1]
    return clean, len(texts) - len(clean)


def pipeline():
    return Pipeline(
        [
            (
                "tfidf",
                FeatureUnion(
                    [
                        (
                            "word",
                            TfidfVectorizer(
                                preprocessor=prepare_text,
                                lowercase=False,
                                ngram_range=(1, 2),
                                min_df=2,
                                sublinear_tf=True,
                                max_features=20000,
                            ),
                        ),
                        (
                            "char",
                            TfidfVectorizer(
                                preprocessor=prepare_text,
                                analyzer="char_wb",
                                ngram_range=(3, 5),
                                min_df=2,
                                sublinear_tf=True,
                                max_features=30000,
                            ),
                        ),
                    ]
                ),
            ),
            (
                "classifier",
                LogisticRegression(
                    C=2.0,
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=42,
                ),
            ),
        ]
    )


def evaluate(model, data):
    texts, expected = zip(*data, strict=True)
    predicted = model.predict(list(texts))
    return {
        "accuracy": accuracy_score(expected, predicted),
        "f1_macro": f1_score(expected, predicted, labels=list(LABELS), average="macro"),
        "classification_report": classification_report(
            expected,
            predicted,
            labels=list(LABELS),
            output_dict=True,
            zero_division=0,
        ),
        "confusion_matrix": confusion_matrix(expected, predicted, labels=list(LABELS)).tolist(),
        "label_order": list(LABELS),
    }


def train():
    manifest = download_dataset()
    train_data, train_removed = read_split("train")
    validation, validation_removed = read_split("val")
    train_keys = {prepare_text(text).casefold() for text, _ in train_data}
    filtered = [row for row in validation if prepare_text(row[0]).casefold() not in train_keys]
    overlap_removed = len(validation) - len(filtered)
    validation = filtered
    for name, data in [("treino", train_data), ("validação", validation)]:
        if set(y for _, y in data) != set(LABELS):
            raise ValueError(f"As três classes precisam estar presentes no {name}.")
    texts, labels = zip(*train_data, strict=True)
    model = pipeline()
    model.fit(list(texts), list(labels))
    code_hash = hashlib.sha256(
        (
            Path(__file__).read_text(encoding="utf-8")
            + (ROOT / "backend" / "classifier.py").read_text(encoding="utf-8")
        ).encode("utf-8")
    ).hexdigest()
    model_id = (
        "tfidf-logreg-umsab-pt-"
        + hashlib.sha256(f"{REVISION}:{code_hash}:{sklearn.__version__}".encode()).hexdigest()[:12]
    )
    MODEL_PATH.parent.mkdir(exist_ok=True)
    bundle = {"model_id": model_id, "pipeline": model}
    temp = MODEL_PATH.with_suffix(".tmp")
    dummy = DummyClassifier(strategy="most_frequent").fit(list(texts), list(labels))
    report = {
        "model_id": model_id,
        "model_name": "TF-IDF + regressão logística",
        "dataset": "UMSAB · recorte português (SentiBR / TweetSentBR)",
        "source_url": "https://github.com/cardiffnlp/xlm-t",
        "source_revision": REVISION,
        "training_code_sha256": code_hash,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "evaluation_split": "validation",
        "test_evaluated": False,
        "seed": 42,
        "configuration": {
            "word_ngrams": [1, 2],
            "char_ngrams": [3, 5],
            "min_df": 2,
            "C": 2.0,
            "class_weight": "balanced",
            "tuning": "Nenhuma busca de hiperparâmetros",
        },
        "environment": {"python": platform.python_version(), "scikit_learn": sklearn.__version__},
        "samples": {
            "train": len(train_data),
            "validation": len(validation),
            "test_reserved": manifest["test_text.txt"]["lines"],
            "train_removed": train_removed,
            "validation_removed": validation_removed,
            "validation_overlap_removed": overlap_removed,
        },
        "class_distribution": {
            "train": dict(Counter(labels)),
            "validation": dict(Counter(y for _, y in validation)),
        },
        "metrics": evaluate(model, validation),
        "dummy_metrics": evaluate(dummy, validation),
        "limitations": [
            "Resultado preliminar de validação, não avaliação final no teste.",
            "Textos de redes sociais sobre televisão; desempenho em empresas não foi medido.",
            "Classes ambíguas, ironia, negação, gírias e domínio novo podem gerar erros.",
            "Exemplos fictícios do painel não foram usados no treinamento nem nas métricas.",
            "A comparação com Transformer ainda não foi realizada.",
        ],
    }
    report_path = ROOT / "reports" / "baseline_validation.json"
    bundle["report"] = report
    joblib.dump(bundle, temp)
    temp.replace(MODEL_PATH)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"model": model_id, "samples": report["samples"], "metrics": report["metrics"]},
            ensure_ascii=False,
            indent=2,
        )
    )


def evaluate_final_test():
    if not MODEL_PATH.exists():
        raise ValueError("Treine o modelo antes de avaliar o teste.")
    test, removed = read_split("test")
    training, _ = read_split("train")
    validation, _ = read_split("val")
    previous = {prepare_text(text).casefold() for text, _ in training + validation}
    clean = [row for row in test if prepare_text(row[0]).casefold() not in previous]
    bundle = joblib.load(MODEL_PATH)
    report = {
        "model_id": bundle["model_id"],
        "evaluation_split": "test",
        "samples": len(clean),
        "duplicates_removed": removed + len(test) - len(clean),
        "metrics": evaluate(bundle["pipeline"], clean),
        "warning": "Teste final consultado; não ajustar o modelo a partir deste resultado.",
    }
    (ROOT / "reports" / "baseline_test.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--test", action="store_true", help="Consultar o teste final reservado.")
    args = parser.parse_args()
    try:
        evaluate_final_test() if args.test else train()
    except Exception as exc:
        print(f"Não foi possível concluir o experimento: {exc}", file=sys.stderr)
        sys.exit(1)
