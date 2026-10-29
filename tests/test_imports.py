import pytest

from backend.imports import MAX_BYTES, InvalidCSV, parse_csv


def test_utf8_bom_semicolon_multiline_and_optional_metadata():
    content = (
        '\ufefftexto;data;fonte;id_origem\r\n"Ótimo!\nVolto logo.";2026-10-28;Loja;1\r\n'.encode()
    )
    rows, duplicates = parse_csv(content)
    assert rows[0]["text"] == "Ótimo!\nVolto logo."
    assert rows[0]["published_at"] == "2026-10-28"
    assert duplicates == 0
    rows, _ = parse_csv(b"texto\nAdorei\n")
    assert rows[0]["published_at"] is None
    assert rows[0]["source"] == "Não informada"


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"outra\ntexto\n",
        b"texto,texto\na,b\n",
        b"texto,autor\na,b\n",
        b"texto\n\xff\n",
        b"texto\n\x00\n",
        b'texto\n"aspas abertas\n',
        b"texto,data\na,2026-02-30\n",
        b"texto,data\na,28/10/2026\n",
        b"texto,data\na,20261028\n",
        b"texto,data\na\n",
        b"texto\na,b\n",
        b"texto\n" + b"a" * 5001,
        b"texto\n" + b"a\n" * 1001,
        b"texto\n" + b"a" * MAX_BYTES,
    ],
)
def test_rejects_invalid_input(content):
    with pytest.raises(InvalidCSV):
        parse_csv(content)


def test_blank_row_is_reported_without_partial_acceptance():
    with pytest.raises(InvalidCSV) as error:
        parse_csv(b"texto,data\nBom,2026-10-28\n,2026-10-28\n")
    assert error.value.issues[0]["line"] == 3


def test_duplicates_and_text_identity():
    rows, duplicates = parse_csv(b"texto\nBom\nBom\nRuim\n")
    assert len(rows) == 2
    assert duplicates == 1
