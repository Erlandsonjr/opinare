"""Avaliação final única nos testes reservados: python -m experiments.compare.

A regra de seleção usa somente a validação e é aplicada antes de ler o teste.
O script se recusa a rodar de novo se a comparação já existir (use --force apenas
para reproduzir o mesmo procedimento, nunca para ajustar modelos).
"""

import argparse
import csv
import json
import random
import sys
from datetime import UTC, datetime

import joblib
from sklearn.dummy import DummyClassifier

from backend.classifier import COMBINED_BASELINE_PATH, MODEL_PATH, ROOT, TRANSFORMER_DIR
from experiments import data as datasets
from experiments.train import evaluate_predictions

REPORT_PATH = ROOT / "reports" / "comparacao_modelos.json"
ERRORS_PATH = ROOT / "reports" / "erros_teste_b2w.json"
# UMSAB tweets are not republished: their errors stay local, outside git.
UMSAB_ERRORS_PATH = ROOT / "var" / "erros_teste_umsab_local.json"
SANITY_FILE = ROOT / "data" / "examples" / "teste_livraria_horizonte.csv"
# Drafted by the coordinator from the text alone; pending human review by the team.
PROPOSED = {
    "horizonte-teste-001": "positivo", "horizonte-teste-002": "negativo",
    "horizonte-teste-003": "neutro", "horizonte-teste-004": "positivo",
    "horizonte-teste-005": "negativo", "horizonte-teste-006": "neutro",
    "horizonte-teste-007": "positivo", "horizonte-teste-008": "negativo",
    "horizonte-teste-009": "neutro", "horizonte-teste-010": "positivo",
    "horizonte-teste-011": "negativo", "horizonte-teste-012": "neutro",
    "horizonte-teste-013": "positivo", "horizonte-teste-014": "negativo",
    "horizonte-teste-015": "neutro", "horizonte-teste-016": "positivo",
    "horizonte-teste-017": "negativo", "horizonte-teste-018": "neutro",
    "horizonte-teste-019": "positivo", "horizonte-teste-020": "negativo",
    "horizonte-teste-021": "neutro", "horizonte-teste-022": "positivo",
    "horizonte-teste-023": "negativo", "horizonte-teste-024": "neutro",
}  # fmt: skip
CANDIDATES = ("baseline_combinado", "bertimbau")


def load_models():
    from backend.transformer import TransformerClassifier

    v1 = joblib.load(MODEL_PATH)
    v2 = joblib.load(COMBINED_BASELINE_PATH)
    bert = TransformerClassifier(TRANSFORMER_DIR)
    return {
        "baseline_v1": {
            "name": "TF-IDF + regressão logística (baseline v1)",
            "model_id": v1["model_id"],
            "training_data": "UMSAB treino (1.839 tweets)",
            "validation_f1_macro": v1["report"]["metrics"]["f1_macro"],
            "validation_note": "Validação UMSAB (323 textos), não comparável à combinada.",
            "predict": lambda texts: v1["pipeline"].predict(texts).tolist(),
        },
        "baseline_combinado": {
            "name": "TF-IDF + regressão logística (UMSAB + B2W)",
            "model_id": v2["model_id"],
            "training_data": "UMSAB treino + B2W treino (7.839 textos)",
            "validation_f1_macro": v2["report"]["metrics"]["f1_macro"],
            "validation_note": "Validação combinada UMSAB + B2W (1.223 textos).",
            "predict": lambda texts: v2["pipeline"].predict(texts).tolist(),
            "proba": lambda texts: v2["pipeline"].predict_proba(texts),
        },
        "bertimbau": {
            "name": "BERTimbau Base ajustado (UMSAB + B2W)",
            "model_id": bert.version,
            "training_data": "UMSAB treino + B2W treino (7.839 textos)",
            "validation_f1_macro": bert.report["metrics"]["f1_macro"],
            "validation_note": "Validação combinada UMSAB + B2W (1.223 textos).",
            "predict": bert.predict,
            "scores": bert.predict_proba,
        },
    }


def sanity_rows(models):
    with SANITY_FILE.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    texts = [row["texto"] for row in rows]
    predictions = {key: model["predict"](texts) for key, model in models.items()}
    return [
        {
            "id": row["id_origem"],
            "text": row["texto"],
            "proposed_label": PROPOSED[row["id_origem"]],
            "predictions": {key: predictions[key][index] for key in models},
        }
        for index, row in enumerate(rows)
    ]


def compare(force: bool):
    if REPORT_PATH.exists() and not force:
        raise ValueError(
            "O teste já foi consultado (reports/comparacao_modelos.json existe). "
            "Não repita a avaliação para ajustar modelos."
        )
    models = load_models()
    # Selection uses validation only, before any test prediction is computed.
    selected = max(CANDIDATES, key=lambda key: models[key]["validation_f1_macro"])
    data = datasets.build()
    datasets.write_manifest(data)
    test_sets = {"umsab": data["umsab"]["test"], "b2w": data["b2w"]["test"]}
    train_texts, train_labels = zip(*data["combined"]["train"], strict=True)
    dummy = DummyClassifier(strategy="most_frequent").fit(list(train_texts), list(train_labels))
    results, dummy_results, predictions = {}, {}, {}
    for test_key, rows in test_sets.items():
        texts = [text for text, _ in rows]
        gold = [label for _, label in rows]
        dummy_results[test_key] = evaluate_predictions(gold, dummy.predict(texts).tolist())
        for model_key, model in models.items():
            predicted = model["predict"](texts)
            predictions[(model_key, test_key)] = predicted
            results.setdefault(model_key, {})[test_key] = evaluate_predictions(gold, predicted)
    errors = {}
    for test_key, rows in test_sets.items():
        selected_pred = predictions[(selected, test_key)]
        wrong = [
            {
                "text": text,
                "gold": gold,
                "predicted": selected_pred[index],
                "baseline_combinado": predictions[("baseline_combinado", test_key)][index],
                "baseline_v1": predictions[("baseline_v1", test_key)][index],
            }
            for index, (text, gold) in enumerate(rows)
            if selected_pred[index] != gold
        ]
        random.Random(datasets.SEED).shuffle(wrong)
        errors[test_key] = {"total_errors": len(wrong), "sample": wrong[:80]}
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "protocol": (
            "Treino e seleção de época apenas com treino/validação. Divisões disjuntas por texto "
            "normalizado. Teste consultado uma única vez, depois da seleção do modelo; nenhum "
            "ajuste foi feito a partir destes números."
        ),
        "selection_rule": (
            "Entre os modelos treinados nos mesmos dados combinados, foi escolhido o de maior "
            "F1 macro na validação combinada (UMSAB + B2W). A regra foi aplicada antes do teste."
        ),
        "selected_model": selected,
        "models": [
            {
                key: value
                for key, value in {"key": model_key, **model}.items()
                if key not in ("predict", "proba", "scores")
            }
            for model_key, model in models.items()
        ],
        "test_sets": [
            {
                "key": "umsab",
                "name": "UMSAB · teste",
                "size": len(test_sets["umsab"]),
                "description": "Tweets sobre programas de TV (TweetSentBR), divisão oficial.",
                "license": "Uso acadêmico; restrições dos datasets originais podem se aplicar.",
            },
            {
                "key": "b2w",
                "name": "B2W · teste",
                "size": len(test_sets["b2w"]),
                "description": "Avaliações reais de e-commerce, 500 por classe; nota 3 = neutro.",
                "license": "CC BY-NC-SA 4.0",
            },
        ],
        "results": results,
        "dummy": dummy_results,
        "dummy_note": "Classe majoritária do treino combinado (classes empatadas: 'negativo').",
        "data_sources": [
            {
                "name": "UMSAB · recorte português (SentiBR / TweetSentBR)",
                "url": "https://github.com/cardiffnlp/xlm-t",
                "license": "Uso acadêmico; restrições dos datasets originais podem se aplicar.",
                "use": "Treino, validação e teste (tweets sobre TV).",
            },
            {
                "name": "B2W-Reviews01 (Americanas)",
                "url": "https://github.com/americanas-tech/b2w-reviews01",
                "license": "CC BY-NC-SA 4.0",
                "use": "Treino, validação e teste (avaliações de produtos). Só texto e nota.",
            },
            {
                "name": "BERTimbau Base (neuralmind/bert-base-portuguese-cased)",
                "url": "https://huggingface.co/neuralmind/bert-base-portuguese-cased",
                "license": "MIT",
                "use": "Modelo pré-treinado, ajustado pela equipe para três classes.",
            },
        ],
        "limitations": [
            "A classe neutra é a mais difícil; no B2W ela vem da nota 3, que mistura "
            "opiniões mornas, mistas e ambíguas (rótulo ruidoso).",
            "Ironia, sarcasmo e opiniões mistas continuam gerando erros.",
            "B2W são avaliações de produtos de e-commerce; comentários de pequenos negócios "
            "locais (atendimento, ambiente) ainda são um domínio diferente.",
            "O teste UMSAB é de tweets sobre TV, domínio distinto dos comentários de empresas.",
            "O CSV fictício da livraria serve só como checagem de sanidade, não como métrica.",
        ],
        "sanity_check": {
            "file": "data/examples/teste_livraria_horizonte.csv",
            "note": (
                "Checagem de sanidade, não é métrica. Rótulos propostos — revisar pela equipe. "
                "Frases fictícias; não usadas em treino nem em avaliação."
            ),
            "rows": sanity_rows(models),
        },
    }
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    ERRORS_PATH.write_text(
        json.dumps(
            {
                "model": selected,
                "note": "Amostra aleatória (semente 42) de erros do modelo selecionado no teste "
                "B2W. Textos do B2W-Reviews01, CC BY-NC-SA 4.0.",
                **errors["b2w"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        "utf-8",
    )
    UMSAB_ERRORS_PATH.parent.mkdir(exist_ok=True)
    UMSAB_ERRORS_PATH.write_text(json.dumps(errors["umsab"], ensure_ascii=False, indent=2), "utf-8")
    print(f"\nModelo selecionado pela validação: {selected}\n")
    print(f"{'modelo':<22}{'teste':<8}{'F1 macro':>10}{'acurácia':>10}")
    for model_key in [*models, "classe_majoritaria"]:
        source = dummy_results if model_key == "classe_majoritaria" else results[model_key]
        for test_key in test_sets:
            metrics = source[test_key]
            print(
                f"{model_key:<22}{test_key:<8}"
                f"{metrics['f1_macro']:>10.4f}{metrics['accuracy']:>10.4f}"
            )
    agree = sum(
        row["predictions"][selected] == row["proposed_label"]
        for row in report["sanity_check"]["rows"]
    )
    print(f"\nChecagem de sanidade (livraria fictícia, não é métrica): {agree}/24 coincidem "
          "com os rótulos propostos.")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Reproduzir a avaliação existente.")
    args = parser.parse_args()
    try:
        compare(args.force)
    except Exception as exc:
        print(f"Não foi possível comparar os modelos: {exc}", file=sys.stderr)
        sys.exit(1)
