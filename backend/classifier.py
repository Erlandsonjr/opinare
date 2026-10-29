import logging
import re
import unicodedata
from pathlib import Path

import joblib

ROOT = Path(__file__).resolve().parents[1]
LABELS = ("negativo", "neutro", "positivo")
MODEL_PATH = ROOT / "artifacts" / "baseline.joblib"
logger = logging.getLogger(__name__)


def prepare_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"https?://\S+|www\.\S+", " URL ", text)
    text = re.sub(r"(?<!\w)@\w+", " USUARIO ", text)
    return " ".join(text.split())


class ModelUnavailable(Exception):
    pass


class SentimentClassifier:
    def __init__(self, path: Path | None = None):
        self.path = path or MODEL_PATH
        self.bundle = None
        self.load_error = None
        if path is None and (ROOT / "reports" / "transformer_functional_check.json").exists():
            try:
                from backend.transformer import load_transformer_bundle

                self.bundle = load_transformer_bundle()
            except Exception:
                logger.exception("Falha ao carregar o Transformer local")
                self.load_error = "O modelo de português não está pronto. Execute preparar.ps1."
            return
        if self.path.exists():
            try:
                # Only the locally trained artifact is loaded; uploads never become model files.
                self.bundle = joblib.load(self.path)
                if set(self.bundle["pipeline"].classes_) != set(LABELS):
                    raise ValueError("O modelo não contém as três classes esperadas.")
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
        predictions = self.bundle["pipeline"].predict(texts).tolist()
        if len(predictions) != len(texts) or any(label not in LABELS for label in predictions):
            raise ModelUnavailable("O classificador retornou uma resposta inválida.")
        return predictions
