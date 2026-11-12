import { useEffect, useRef, useState } from "react";
import { FlaskConical, LoaderCircle, X } from "lucide-react";
import { api, type AnalysisModel, type AnalyzeResult } from "./types";

const labels = ["negativo", "neutro", "positivo"] as const;
const names = { negativo: "Negativo", neutro: "Neutro", positivo: "Positivo" };

function ResultCard({ title, value }: { title: string; value: AnalysisModel }) {
  return (
    <section className="analysis-card">
      <h3>{title}</h3>
      <p>{value.name}</p>
      <span className={`sentiment-badge ${value.label}`}>
        <i />
        {names[value.label]}
      </span>
      {value.scores ? (
        <div className="score-list">
          {labels.map((label) => (
            <div key={label} className="score-row">
              <span>{names[label]}</span>
              <strong>
                {(value.scores![label] * 100).toLocaleString("pt-BR", {
                  maximumFractionDigits: 1,
                })}
                %
              </strong>
              <progress
                value={value.scores![label]}
                max={1}
                aria-label={`Pontuação ${names[label]}`}
                aria-valuetext={`${(value.scores![label] * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`}
              />
            </div>
          ))}
        </div>
      ) : (
        <p>Pontuações indisponíveis para este modelo.</p>
      )}
    </section>
  );
}

export default function SentenceTester({
  modelReady,
}: {
  modelReady: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const request = useRef<AbortController | null>(null);
  useEffect(() => {
    if (open) {
      dialog.current?.showModal();
      closeButton.current?.focus();
    } else dialog.current?.close();
  }, [open]);
  function close() {
    // Analysis is read-only, so a pending request can be abandoned safely.
    request.current?.abort();
    setOpen(false);
    opener.current?.focus();
  }
  async function analyze(event: React.FormEvent) {
    event.preventDefault();
    if (!text.trim() || text.length > 5000 || loading) return;
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(
        await api<AnalyzeResult>("/api/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
          signal: controller.signal,
        }),
      );
    } catch (issue) {
      if (!controller.signal.aborted)
        setError(
          issue instanceof Error ? issue.message : "Falha ao analisar a frase.",
        );
    } finally {
      if (request.current === controller) request.current = null;
      setLoading(false);
    }
  }
  return (
    <>
      <button
        ref={opener}
        className="button secondary"
        onClick={() => setOpen(true)}
        disabled={!modelReady}
        title={modelReady ? undefined : "O modelo ainda não está disponível."}
      >
        <FlaskConical size={17} />
        Testar uma frase
      </button>
      <dialog
        ref={dialog}
        className="import-dialog analyze-dialog"
        aria-labelledby="analyze-title"
        onCancel={(event) => {
          event.preventDefault();
          close();
        }}
        onClick={(event) => {
          if (event.target === event.currentTarget) close();
        }}
      >
        <div className="dialog-content" aria-busy={loading}>
          <button
            ref={closeButton}
            className="dialog-close"
            aria-label="Fechar análise"
            onClick={close}
          >
            <X size={20} />
          </button>
          <span className="dialog-icon">
            <FlaskConical size={26} />
          </span>
          <h2 id="analyze-title">Testar uma frase</h2>
          <p>
            Veja como os modelos classificam um comentário. Nada é salvo na
            base.
          </p>
          <form onSubmit={analyze}>
            <label className="analysis-label" htmlFor="analysis-text">
              Frase para analisar
            </label>
            <textarea
              id="analysis-text"
              value={text}
              onChange={(event) => {
                setText(event.target.value);
                setResult(null);
                setError("");
              }}
              aria-describedby="analysis-counter-info"
              rows={5}
              disabled={loading}
            />
            <div id="analysis-counter-info" className="analysis-counter">
              <span>
                {!text.trim()
                  ? "Digite uma frase para analisar."
                  : text.length > 5000
                    ? "A frase pode ter até 5.000 caracteres."
                    : "Nada é salvo na base."}
              </span>
              <span>{text.length.toLocaleString("pt-BR")} / 5.000</span>
            </div>
            <button
              className="button primary"
              type="submit"
              disabled={loading || !text.trim() || text.length > 5000}
            >
              {loading && <LoaderCircle size={17} className="spin" />}
              {loading ? "Analisando…" : "Analisar"}
            </button>
          </form>
          {error && (
            <div className="notice error" role="alert">
              {error}
            </div>
          )}
          <div role="status" aria-live="polite" className="sr-only">
            {result
              ? `Análise concluída. ${result.active.name}: ${names[result.active.label]}.`
              : ""}
          </div>
          {result && (
            <div className="analysis-results">
              <div className="analysis-grid">
                <ResultCard title="Modelo ativo" value={result.active} />
                {result.baseline ? (
                  <ResultCard
                    title="Comparação: baseline TF-IDF"
                    value={result.baseline}
                  />
                ) : (
                  <section className="analysis-card">
                    <h3>Comparação: baseline TF-IDF</h3>
                    <p>
                      Não há baseline adicional para comparar com o modelo
                      ativo.
                    </p>
                  </section>
                )}
              </div>
              <p>
                Pontuações do modelo: indicam a preferência entre as classes,
                não a probabilidade garantida de acerto.
              </p>
              <p>Nada é salvo na base.</p>
            </div>
          )}
        </div>
      </dialog>
    </>
  );
}
