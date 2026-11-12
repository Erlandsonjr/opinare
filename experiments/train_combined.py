"""Baseline TF-IDF no treino combinado UMSAB + B2W: python -m experiments.train_combined."""

import hashlib
import json
import platform
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

import joblib
import sklearn
from sklearn.dummy import DummyClassifier

from backend.classifier import ROOT
from experiments import data as datasets
from experiments.train import evaluate, pipeline

COMBINED_MODEL_PATH = ROOT / "artifacts" / "baseline-combinado.joblib"


def train():
    data = datasets.build()
    datasets.write_manifest(data)
    train_rows = data["combined"]["train"]
    validation = data["combined"]["validation"]
    texts, labels = zip(*train_rows, strict=True)
    model = pipeline()
    model.fit(list(texts), list(labels))
    code_hash = hashlib.sha256(
        Path(__file__).read_bytes()
        + (ROOT / "experiments" / "train.py").read_bytes()
        + (ROOT / "experiments" / "data.py").read_bytes()
        + (ROOT / "backend" / "classifier.py").read_bytes()
    ).hexdigest()
    model_id = (
        "tfidf-logreg-b2w-umsab-"
        + hashlib.sha256(
            f"{datasets.split_hash(train_rows)}:{code_hash}:{sklearn.__version__}".encode()
        ).hexdigest()[:12]
    )
    dummy = DummyClassifier(strategy="most_frequent").fit(list(texts), list(labels))
    report = {
        "model_id": model_id,
        "model_name": "TF-IDF + regressão logística (UMSAB + B2W)",
        "dataset": "UMSAB português (TweetSentBR) + B2W-Reviews01",
        "source_url": "https://github.com/americanas-tech/b2w-reviews01",
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
            "tuning": "Nenhuma busca de hiperparâmetros; mesmo pipeline do baseline v1",
        },
        "environment": {"python": platform.python_version(), "scikit_learn": sklearn.__version__},
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
        "class_distribution": {
            "train": dict(Counter(labels)),
            "validation": dict(Counter(y for _, y in validation)),
        },
        "metrics": evaluate(model, validation),
        "dummy_metrics": evaluate(dummy, validation),
        "limitations": [
            "Métricas de validação; o teste é consultado uma única vez na comparação final.",
            "Nota 3 do B2W tratada como neutro: aproximação ruidosa da classe neutra.",
            "Ironia, negação, opiniões mistas e mudança de domínio podem gerar erros.",
            "Exemplos fictícios do painel não foram usados no treinamento nem nas métricas.",
        ],
    }
    COMBINED_MODEL_PATH.parent.mkdir(exist_ok=True)
    temp = COMBINED_MODEL_PATH.with_suffix(".tmp")
    joblib.dump({"model_id": model_id, "pipeline": model, "report": report}, temp)
    temp.replace(COMBINED_MODEL_PATH)
    (ROOT / "reports" / "baseline_combinado_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"model": model_id, "f1_macro": report["metrics"]["f1_macro"]}))


if __name__ == "__main__":
    try:
        train()
    except Exception as exc:
        print(f"Não foi possível treinar o baseline combinado: {exc}", file=sys.stderr)
        sys.exit(1)
