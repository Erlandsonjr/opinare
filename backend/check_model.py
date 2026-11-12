"""Mostra qual modelo a aplicação usará: python -m backend.check_model."""

from backend.classifier import SentimentClassifier

if __name__ == "__main__":
    model = SentimentClassifier()
    if not model.ready:
        print("Nenhum modelo pronto. Execute .\\preparar.ps1 com internet.")
    elif model.active == "bertimbau":
        print(f"BERTimbau válido e ativo ({model.version}).")
    else:
        print(f"Modelo ativo: baseline TF-IDF ({model.version}).")
        if model.fallback_reason:
            print(model.fallback_reason)
        print(
            "Para usar o BERTimbau, copie a pasta artifacts/bertimbau-sentimento do computador "
            "onde ele foi treinado (veja o README)."
        )
