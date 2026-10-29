import csv
import hashlib
import io
from datetime import date

MAX_BYTES = 1_048_576
MAX_ROWS = 1000
MAX_TEXT = 5000
HEADERS = {"texto", "data", "fonte", "id_origem"}


class InvalidCSV(ValueError):
    def __init__(self, message: str, issues: list[dict] | None = None):
        self.message = message
        self.issues = issues or []
        super().__init__(message)


def parse_csv(content: bytes) -> tuple[list[dict], int]:
    if len(content) > MAX_BYTES:
        raise InvalidCSV("O arquivo excede o limite de 1 MB.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidCSV("Salve o arquivo como CSV UTF-8 e tente novamente.") from exc
    if "\x00" in text:
        raise InvalidCSV("O arquivo contém caracteres inválidos.")
    # Excel commonly uses semicolons in Brazilian locales; accept both explicitly.
    first = text.splitlines()[0] if text.splitlines() else ""
    delimiter = ";" if ";" in first and "," not in first else ","
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    try:
        fields = [field.strip().lower() for field in (reader.fieldnames or [])]
        if "texto" not in fields:
            raise InvalidCSV("O CSV precisa ter a coluna obrigatória 'texto'.")
        if len(set(fields)) != len(fields) or any(field not in HEADERS for field in fields):
            raise InvalidCSV("Use apenas texto, data, fonte e id_origem, sem colunas repetidas.")
        reader.fieldnames = fields
        records, issues, seen = [], [], set()
        duplicates = 0
        for index, row in enumerate(reader, start=1):
            if index > MAX_ROWS:
                raise InvalidCSV("Importe no máximo 1.000 registros por arquivo.")
            line = reader.line_num
            if None in row or any(value is None for value in row.values()):
                issues.append(
                    {"line": line, "message": "Número de colunas diferente do cabeçalho."}
                )
                continue
            record = {key: value.strip() for key, value in row.items()}
            value = record["texto"]
            if not value or len(value) > MAX_TEXT:
                issues.append(
                    {"line": line, "message": "O texto deve ter de 1 a 5.000 caracteres."}
                )
                continue
            published_at = record.get("data") or None
            if published_at:
                try:
                    if date.fromisoformat(published_at).isoformat() != published_at:
                        raise ValueError()
                except ValueError:
                    issues.append({"line": line, "message": "Use data no formato AAAA-MM-DD."})
                    continue
            source = record.get("fonte") or "Não informada"
            origin_id = record.get("id_origem") or ""
            if len(source) > 100 or len(origin_id) > 200:
                issues.append({"line": line, "message": "Fonte ou identificador muito longo."})
                continue
            fingerprint = hashlib.sha256(
                repr((value, published_at, source, origin_id)).encode("utf-8")
            ).hexdigest()
            if fingerprint in seen:
                duplicates += 1
                continue
            seen.add(fingerprint)
            records.append(
                {
                    "text": value,
                    "published_at": published_at,
                    "source": source,
                    "origin_id": origin_id,
                    "fingerprint": fingerprint,
                }
            )
    except csv.Error as exc:
        raise InvalidCSV("O CSV está malformado. Confira aspas, colunas e separadores.") from exc
    if issues:
        raise InvalidCSV("Corrija as linhas indicadas. Nenhum registro foi importado.", issues)
    if not records:
        raise InvalidCSV("O arquivo não contém comentários para analisar.")
    return records, duplicates
