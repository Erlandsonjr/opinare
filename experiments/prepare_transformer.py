"""Baixa uma versão fixada do checkpoint e compara sem treinar nos exemplos."""

import json
import sys
import time
import urllib.request
from datetime import UTC, datetime

from backend.classifier import MODEL_PATH, ROOT, SentimentClassifier
from backend.transformer import (
    FILE_HASHES,
    MODEL_DIR,
    MODEL_NAME,
    REPORT_PATH,
    REVISION,
    TransformerPipeline,
    model_version,
    sha256_file,
)
from experiments.train import evaluate

CHECK_PATH = ROOT / "data" / "evaluation" / "checagem_sentimentos.json"


def download_model():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    for name, expected in FILE_HASHES.items():
        target = MODEL_DIR / name
        if target.exists() and sha256_file(target) == expected:
            continue
        print(f"Preparando modelo português: {name}", flush=True)
        url = f"https://huggingface.co/{MODEL_NAME}/resolve/{REVISION}/{name}"
        temporary = target.with_suffix(target.suffix + ".part")
        with urllib.request.urlopen(url, timeout=90) as response, temporary.open("wb") as output:
            total = 0
            while chunk := response.read(4 * 1024 * 1024):
                total += len(chunk)
                if total > 600_000_000:
                    raise ValueError("Arquivo remoto acima do tamanho permitido.")
                output.write(chunk)
        if sha256_file(temporary) != expected:
            raise ValueError(f"O arquivo {name} não corresponde ao hash fixado.")
        temporary.replace(target)


def prepare():
    download_model()
    fixture = json.loads(CHECK_PATH.read_text(encoding="utf-8"))
    fixture_hash = sha256_file(CHECK_PATH)
    baseline = SentimentClassifier(MODEL_PATH)
    if not baseline.ready:
        raise ValueError("Prepare o baseline com python -m experiments.train antes da comparação.")
    if REPORT_PATH.exists():
        previous = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        if (
            previous.get("model_id") == model_version()
            and previous.get("check_sha256") == fixture_hash
            and previous.get("baseline_model_id") == baseline.version
        ):
            print("Modelo português e relatório já preparados.", flush=True)
            return
    examples = [(item["text"], item["label"]) for item in fixture["examples"]]
    candidate = TransformerPipeline()
    started = time.monotonic()
    candidate_metrics = evaluate(candidate, examples)
    inference_seconds = time.monotonic() - started
    baseline_metrics = evaluate(baseline, examples)
    if (
        candidate_metrics["f1_macro"] <= baseline_metrics["f1_macro"]
        or candidate_metrics["accuracy"] <= baseline_metrics["accuracy"]
    ):
        raise ValueError("O candidato não superou o baseline na checagem; promoção interrompida.")
    report = {
        "model_kind": "pretrained_transformer",
        "model_id": candidate.version,
        "model_name": "Transformer em português · BERTweet",
        "dataset": f"Checagem funcional · {len(examples)} frases sintéticas",
        "source_url": f"https://huggingface.co/{MODEL_NAME}",
        "source_revision": REVISION,
        "evaluation_split": "synthetic_functional_check",
        "evaluation_note": (
            "Checagem funcional com frases sintéticas novas. Estes números ajudam a comparar "
            "as versões, mas não representam desempenho comprovado em comentários reais."
        ),
        "model_description": (
            "Checkpoint externo já treinado para sentimentos em português, executado neste "
            "computador. Nenhum comentário importado ou de demonstração foi usado para "
            "treinar ou ajustar o modelo. Textos longos são divididos em trechos e todas "
            "as partes entram na classificação."
        ),
        "data_note": (
            "A mesma amostra de frases e rótulos propostos pelo assistente Codex foi apresentada "
            "ao baseline e ao Transformer, sem ajuste de pesos ou busca de parâmetros. A amostra "
            "foi criada após observar erros do baseline; não é cega nem revisada por humanos. "
            "O checkpoint "
            "externo usa TweetSentBR; uma avaliação em UMSAB poderia ter sobreposição com "
            "seus dados de treinamento, por isso não foi tratada como teste independente."
        ),
        "test_evaluated": False,
        "samples": {"train": None, "validation": len(examples), "test_reserved": 870},
        "metrics": candidate_metrics,
        "baseline_model_id": baseline.version,
        "baseline_metrics_same_sample": baseline_metrics,
        "baseline_umsab_validation": baseline.report["metrics"],
        "check_sha256": fixture_hash,
        "check_authorship": fixture["labeling"],
        "evaluated_at": datetime.now(UTC).isoformat(),
        "inference_seconds": inference_seconds,
        "files_sha256": FILE_HASHES,
        "limitations": [
            "A amostra funcional é pequena, sintética e não representa o uso em produção.",
            "O checkpoint pode ter visto dados relacionados ao UMSAB; "
            "não há comparação científica independente nesses dados.",
            "O teste UMSAB não foi consultado pelo projeto nesta atualização; "
            "sua independência para o checkpoint externo não está garantida.",
            "Ironia, ambiguidade, opiniões mistas e mudanças de domínio ainda podem gerar erros.",
            "Textos longos são agregados por trechos; "
            "uma opinião curta pode ser diluída pelo restante do texto.",
            "A validação com comentários reais rotulados "
            "e a avaliação científica final continuam pendentes.",
        ],
    }
    REPORT_PATH.parent.mkdir(exist_ok=True)
    temporary = REPORT_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(REPORT_PATH)
    print(
        json.dumps(
            {
                "model_id": candidate.version,
                "samples": len(examples),
                "baseline_accuracy": baseline_metrics["accuracy"],
                "candidate_accuracy": candidate_metrics["accuracy"],
                "baseline_f1_macro": baseline_metrics["f1_macro"],
                "candidate_f1_macro": candidate_metrics["f1_macro"],
                "seconds": inference_seconds,
            },
            indent=2,
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    try:
        prepare()
    except Exception as exc:
        print(f"Não foi possível preparar o Transformer: {exc}", file=sys.stderr)
        sys.exit(1)
