import logging
import os
import re
import unicodedata
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[1]
LABELS = ("negativo", "neutro", "positivo")
MODEL_PATH = ROOT / "artifacts" / "baseline.joblib"
COMBINED_BASELINE_PATH = ROOT / "artifacts" / "baseline-combinado.joblib"
TRANSFORMER_DIR = ROOT / "artifacts" / "bertimbau-sentimento"
logger = logging.getLogger(__name__)


def prepare_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"https?://\S+|www\.\S+", " URL ", text)
    text = re.sub(r"(?<!\w)@\w+", " USUARIO ", text)
    return " ".join(text.split())


class ModelUnavailable(Exception):
    pass


class BaselineClassifier:
    def __init__(self, path: Path = MODEL_PATH):
        self.path = path
        self.bundle = None
        self.load_error = None
        if path.exists():
            try:
                self.bundle = joblib.load(path)
                if set(self.bundle["pipeline"].classes_) != set(LABELS):
                    raise ValueError("Classes inválidas")
            except Exception:
                self.bundle = None
                self.load_error = "O modelo local está inválido. Execute o treinamento novamente."

    @property
    def ready(self) -> bool:
        return self.bundle is not None

    @property
    def version(self) -> str:
        return self.bundle["model_id"] if self.ready else "indisponível"

    @property
    def report(self) -> dict | None:
        return self.bundle.get("report") if self.ready else None

    def predict(self, texts: list[str]) -> list[str]:
        if not self.ready:
            raise ModelUnavailable(
                self.load_error or "Execute o treinamento para preparar o modelo."
            )
        predictions = list(self.bundle["pipeline"].predict(texts))
        if len(predictions) != len(texts) or any(label not in LABELS for label in predictions):
            raise ModelUnavailable("O classificador retornou uma resposta inválida.")
        return predictions

    def predict_proba(self, texts: list[str]) -> list[dict[str, float]]:
        if not self.ready:
            raise ModelUnavailable(
                self.load_error or "Execute o treinamento para preparar o modelo."
            )
        pipeline = self.bundle["pipeline"]
        rows = pipeline.predict_proba(texts)
        classes = list(pipeline.classes_)
        return [{label: float(row[classes.index(label)]) for label in LABELS} for row in rows]


class SentimentClassifier:
    def __init__(self, path: Path | None = None):
        self.baseline = None
        self.fallback_reason = None
        self.active = "indisponível"
        paths = [path] if path is not None else [COMBINED_BASELINE_PATH, MODEL_PATH]
        comparison = next(
            (item for item in (BaselineClassifier(p) for p in paths) if item.ready), None
        )
        self._model = None
        if os.environ.get("OPINARE_MODEL", "auto") == "auto" and path is None:
            try:
                if not TRANSFORMER_DIR.is_dir():
                    raise FileNotFoundError("Modelo BERTimbau não encontrado")
                from backend.transformer import TransformerClassifier

                self._model = TransformerClassifier(TRANSFORMER_DIR)
                self.active = "bertimbau"
                self.baseline = comparison
            except Exception as exc:
                if isinstance(exc, FileNotFoundError):
                    reason = "Modelo BERTimbau não encontrado"
                elif isinstance(exc, ImportError) and "torch" in str(exc).lower():
                    reason = "PyTorch não instalado"
                else:
                    reason = "Modelo BERTimbau indisponível ou inválido"
                self.fallback_reason = (
                    f"{reason}; usando o baseline TF-IDF."
                    if comparison
                    else f"{reason}; nenhum baseline disponível."
                )
                logger.warning(self.fallback_reason)
        if self._model is None:
            self._model = comparison
            if comparison:
                self.active = "baseline"
        self.active_name = (self.report or {}).get("model_name") or (
            "Baseline TF-IDF" if self.active == "baseline" else "Indisponível"
        )

    @property
    def ready(self) -> bool:
        return self._model is not None and self._model.ready

    @property
    def version(self) -> str:
        return self._model.version if self.ready else "indisponível"

    @property
    def report(self) -> dict | None:
        return self._model.report if self.ready else None

    @property
    def bundle(self) -> dict | None:
        return self._model.bundle if isinstance(self._model, BaselineClassifier) else None

    def predict(self, texts: list[str]) -> list[str]:
        if not self.ready:
            raise ModelUnavailable("Execute o treinamento para preparar o modelo.")
        return self._model.predict(texts)

    def predict_proba(self, texts: list[str]) -> list[dict[str, float]]:
        if not self.ready:
            raise ModelUnavailable("Execute o treinamento para preparar o modelo.")
        return self._model.predict_proba(texts)
