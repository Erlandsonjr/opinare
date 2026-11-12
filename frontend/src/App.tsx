import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  BarChart3,
  BookOpen,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  FileSpreadsheet,
  FlaskConical,
  Frown,
  LayoutDashboard,
  LoaderCircle,
  MessageCircle,
  MessageSquareText,
  Minus,
  Search,
  ShieldCheck,
  Smile,
  Sparkles,
  Upload,
  X,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  api,
  ApiError,
  type Dashboard,
  type Metrics,
  type ImportResult,
  type ModelInfo,
  type Sentiment,
} from "./types";
import SentenceTester from "./SentenceTester";

const labels: Record<Sentiment, string> = {
  positivo: "Positivo",
  negativo: "Negativo",
  neutro: "Neutro",
};
const colors = { positivo: "#287c65", negativo: "#b85b49", neutro: "#737d69" };
const configurationNames: Record<string, string> = {
  max_length: "Comprimento máximo",
  learning_rate: "Taxa de aprendizado",
  epochs: "Épocas",
  per_device_batch: "Lote por dispositivo",
  gradient_accumulation: "Acumulação de gradientes",
  effective_batch: "Lote efetivo",
  warmup_ratio: "Proporção de aquecimento",
  weight_decay: "Decaimento de pesos",
  seed: "Semente",
  selection: "Seleção",
  text_preparation: "Preparação do texto",
  precision: "Precisão numérica",
};
const percent = (value: number) =>
  new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 }).format(value) +
  "%";
const number = (value: number) => new Intl.NumberFormat("pt-BR").format(value);
const dateLabel = (value: string) =>
  new Date(value + "T12:00:00").toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
  });
type Filters = {
  sentiment: string;
  source: string;
  start: string;
  end: string;
  import_id: string;
  q: string;
};
const emptyFilters: Filters = {
  sentiment: "",
  source: "",
  start: "",
  end: "",
  import_id: "",
  q: "",
};

export default function App() {
  const [view, setView] = useState<"dashboard" | "method">("dashboard");
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [model, setModel] = useState<ModelInfo | null>(null);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshError, setRefreshError] = useState<ApiError | null>(null);
  const [importError, setImportError] = useState<ApiError | null>(null);
  const [notice, setNotice] = useState("");
  const [importing, setImporting] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [search, setSearch] = useState("");
  const openButton = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);
  const paginationRef = useRef<HTMLSpanElement>(null);
  const previousView = useRef(view);

  useEffect(() => {
    document.title = `${view === "dashboard" ? "Visão geral" : "Modelo e metodologia"} · Opinare`;
    if (previousView.current !== view) headingRef.current?.focus();
    previousView.current = view;
  }, [view]);
  useEffect(() => {
    if (importError && importOpen) errorRef.current?.focus();
  }, [importError, importOpen]);

  useEffect(() => {
    const timer = setTimeout(
      () => setFilters((f) => (f.q === search ? f : { ...f, q: search })),
      300,
    );
    return () => clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setRefreshError(null);
    if (filters.start && filters.end && filters.start > filters.end) {
      setRefreshError(
        new ApiError(
          "A data inicial deve ser anterior ou igual à final.",
          [],
          422,
        ),
      );
      setLoading(false);
      return;
    }
    const query = new URLSearchParams({ page: String(page) });
    Object.entries(filters).forEach(([key, value]) => {
      if (value) query.set(key, value);
    });
    Promise.all([
      api<Dashboard>(`/api/dashboard?${query}`),
      api<ModelInfo>("/api/model"),
    ])
      .then(([data, info]) => {
        if (!cancelled) {
          setDashboard(data);
          setModel(info);
        }
      })
      .catch((error) => {
        if (!cancelled) setRefreshError(error as ApiError);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [filters, page, revision]);

  useEffect(() => {
    setPage(1);
  }, [filters]);
  useEffect(() => {
    if (importOpen) {
      dialogRef.current?.showModal();
      closeButton.current?.focus();
    } else {
      dialogRef.current?.close();
    }
  }, [importOpen]);
  useEffect(() => {
    // The dialog-close effect above must run before focusing the page heading.
    if (notice) headingRef.current?.focus();
  }, [notice]);

  const updateFilter = (key: keyof Filters, value: string) =>
    setFilters((previous) => ({ ...previous, [key]: value }));
  const resetFilters = () => {
    setFilters(emptyFilters);
    setSearch("");
    setPage(1);
  };
  const closeImport = useCallback(() => {
    if (importing) return;
    setImportOpen(false);
    setFile(null);
    setImportError(null);
    openButton.current?.focus();
  }, [importing]);

  async function importData(demo: boolean) {
    if (importing || (!demo && !file)) return;
    setImporting(true);
    setImportError(null);
    setNotice("");
    try {
      const body = new FormData();
      if (file) body.append("file", file);
      const result = await api<ImportResult>(
        demo ? "/api/demo" : "/api/imports",
        {
          method: "POST",
          ...(demo ? {} : { body }),
        },
      );
      setNotice(
        `${number(result.inserted)} ${result.inserted === 1 ? "comentário analisado e salvo" : "comentários analisados e salvos"}.${result.duplicates ? ` ${result.duplicates} ${result.duplicates === 1 ? "duplicado foi ignorado" : "duplicados foram ignorados"}.` : ""}`,
      );
      resetFilters();
      setRevision((r) => r + 1);
      setView("dashboard");
      setImportOpen(false);
      setFile(null);
      openButton.current?.focus();
    } catch (error) {
      setImportError(error as ApiError);
      if (!demo) {
        setFile(null);
        setFileInputKey((key) => key + 1);
      }
    } finally {
      setImporting(false);
    }
  }

  const activeFilters = Object.values(filters).some(Boolean);
  const empty = dashboard?.total_all === 0;
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Ir para o conteúdo principal
      </a>
      <aside className="sidebar" aria-label="Menu principal">
        <a className="brand" href="/" aria-label="Opinare, início">
          <span className="brand-mark">
            <MessageCircle size={24} strokeWidth={2.2} />
          </span>
          opinare<span className="brand-period">.</span>
        </a>
        <div className="workspace">
          <span className="workspace-avatar">O</span>
          <div>
            Opinare<small>Análise de sentimentos</small>
          </div>
        </div>
        <p className="nav-label">ACOMPANHAMENTO</p>
        <nav>
          <button
            title="Visão geral"
            aria-label="Visão geral"
            className={view === "dashboard" ? "nav-item active" : "nav-item"}
            aria-current={view === "dashboard" ? "page" : undefined}
            onClick={() => setView("dashboard")}
          >
            <LayoutDashboard size={18} />
            Visão geral
          </button>
          <button
            title="Modelo e metodologia"
            aria-label="Modelo e metodologia"
            className={view === "method" ? "nav-item active" : "nav-item"}
            aria-current={view === "method" ? "page" : undefined}
            onClick={() => setView("method")}
          >
            <FlaskConical size={18} />
            Modelo e metodologia
          </button>
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <BookOpen size={20} />
            <strong>Opiniões com contexto.</strong>
            <p>
              Uma visão inicial dos comentários, com espaço para a análise
              humana.
            </p>
          </div>
        </div>
      </aside>

      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Opinare <ChevronRight size={14} />
            <strong>
              {view === "dashboard" ? "Visão geral" : "Modelo e metodologia"}
            </strong>
          </div>
        </header>
        <main id="main-content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">PAINEL DE ANÁLISE</p>
              <h1 ref={headingRef} tabIndex={-1}>
                {view === "dashboard"
                  ? "Visão geral dos sentimentos"
                  : "Modelo e metodologia"}
              </h1>
              <p className="subtitle">
                {view === "dashboard"
                  ? "Entenda os sentimentos presentes nos seus comentários, em um só lugar."
                  : "Dados, resultados e limites do modelo ativo do Opinare."}
              </p>
            </div>
            <div className="heading-actions">
              <SentenceTester />
              <button
                ref={openButton}
                className="button primary"
                onClick={() => {
                  setImportError(null);
                  setImportOpen(true);
                }}
                disabled={importing}
              >
                <Upload size={17} />
                Importar CSV
              </button>
            </div>
          </div>

          {model && (
            <div className="active-model-note">
              <span className="model-tag">
                <ShieldCheck size={14} />
                Modelo ativo: {model.active_name}
              </span>
              {model.fallback_reason && <span>{model.fallback_reason}</span>}
            </div>
          )}

          {notice && (
            <div className="notice success" role="status">
              <CheckCircle2 size={19} />
              <span>{notice}</span>
              <button
                aria-label="Fechar confirmação"
                onClick={() => setNotice("")}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {refreshError &&
            (view === "method"
              ? refreshError.status !== 422
              : !dashboard || dashboard.total_all === 0) && (
              <div className="notice error" role="alert">
                <CircleHelp size={19} />
                <span>{refreshError.message}</span>
                <button
                  className="text-button"
                  onClick={() =>
                    refreshError.status === 422
                      ? resetFilters()
                      : setRevision((r) => r + 1)
                  }
                >
                  {refreshError.status === 422
                    ? "Limpar filtros"
                    : "Tentar novamente"}
                </button>
              </div>
            )}
          {model && !model.ready && (
            <div className="notice error" role="alert">
              <CircleHelp size={19} />
              <span>
                O modelo ainda não está pronto. Siga a etapa de treinamento do
                README e reinicie a aplicação.
              </span>
            </div>
          )}

          {view === "method" ? (
            <Methodology model={model} loading={loading} error={refreshError} />
          ) : (
            <>
              {loading && (!dashboard || empty) ? (
                <div className="loading-state" role="status">
                  <LoaderCircle className="spin" />
                  Carregando seu painel…
                </div>
              ) : empty ? (
                <div className="empty-welcome">
                  <div className="empty-art">
                    <MessageSquareText size={42} />
                    <span>
                      <Sparkles size={19} />
                    </span>
                  </div>
                  <p className="eyebrow">SEU PRIMEIRO PASSO</p>
                  <h2>As opiniões começam uma conversa.</h2>
                  <p>
                    Importe um arquivo de comentários e descubra como os
                    sentimentos se distribuem. Você também pode conhecer o
                    painel com um exemplo fictício.
                  </p>
                  <button
                    className="button primary"
                    onClick={() => importData(true)}
                    disabled={
                      importing || loading || Boolean(notice) || !model?.ready
                    }
                    aria-describedby={
                      !model?.ready ? "demo-unavailable" : undefined
                    }
                  >
                    {importing ? (
                      <LoaderCircle size={17} className="spin" />
                    ) : (
                      <Sparkles size={17} />
                    )}
                    Explorar demonstração
                    <ArrowRight size={16} />
                  </button>
                  <a className="download-link" href="/api/example.csv" download>
                    <ArrowDownToLine size={15} />
                    Baixar modelo CSV
                  </a>
                  <small>
                    30 comentários fictícios · nenhuma conta necessária
                  </small>
                  {!model?.ready && (
                    <p id="demo-unavailable">
                      Prepare o modelo seguindo o README para habilitar a
                      demonstração.
                    </p>
                  )}
                  {importError && !importOpen && (
                    <div className="notice error" role="alert">
                      {importError.message}
                    </div>
                  )}
                </div>
              ) : dashboard ? (
                <div
                  aria-busy={loading}
                  className={loading ? "dashboard refreshing" : "dashboard"}
                >
                  <div className="overview-caption">
                    <span>
                      <span className="status-dot" />
                      {refreshError
                        ? "Dados da última consulta válida"
                        : activeFilters
                          ? "Resultados filtrados"
                          : "Visão consolidada"}
                      <span className="caption-divider">/</span>
                      {number(dashboard.total)} comentários
                    </span>
                    <span className="model-tag">
                      <ShieldCheck size={14} />
                      Classificação automática
                    </span>
                  </div>
                  {dashboard.demo_count > 0 && (
                    <div className="demo-banner">
                      <FlaskConical size={17} />
                      <span>
                        <strong>Dados de demonstração.</strong>{" "}
                        {dashboard.demo_count} comentários fictícios nesta
                        seleção. As classificações são previsões reais do
                        modelo.
                      </span>
                    </div>
                  )}
                  <section
                    className="stats-grid"
                    aria-label="Resumo de sentimentos"
                  >
                    <Stat
                      label="Comentários analisados"
                      value={dashboard.total}
                      total={dashboard.total}
                      kind="total"
                    />
                    <Stat
                      label="Positivos"
                      value={dashboard.counts.positivo}
                      total={dashboard.total}
                      kind="positivo"
                    />
                    <Stat
                      label="Negativos"
                      value={dashboard.counts.negativo}
                      total={dashboard.total}
                      kind="negativo"
                    />
                    <Stat
                      label="Neutros"
                      value={dashboard.counts.neutro}
                      total={dashboard.total}
                      kind="neutro"
                    />
                  </section>
                  <section
                    className="charts-grid"
                    aria-label="Gráficos de sentimentos"
                  >
                    <div className="panel distribution">
                      <div className="panel-heading">
                        <div>
                          <h2>Distribuição de sentimentos</h2>
                          <p>Como os comentários se dividem</p>
                        </div>
                        <BarChart3 size={19} />
                      </div>
                      <div
                        className="stacked-bar"
                        role="img"
                        aria-label={Object.entries(dashboard.counts)
                          .map(
                            ([key, value]) =>
                              `${labels[key as Sentiment]}: ${value}`,
                          )
                          .join(", ")}
                      >
                        {(
                          ["positivo", "negativo", "neutro"] as Sentiment[]
                        ).map((key) => (
                          <span
                            key={key}
                            style={{
                              width: `${dashboard.total ? (dashboard.counts[key] / dashboard.total) * 100 : 0}%`,
                              background: colors[key],
                            }}
                          />
                        ))}
                      </div>
                      <div className="distribution-rows">
                        {(
                          ["positivo", "negativo", "neutro"] as Sentiment[]
                        ).map((key) => (
                          <div key={key}>
                            <span>
                              <i style={{ background: colors[key] }} />
                              {labels[key]}
                            </span>
                            <strong>
                              {number(dashboard.counts[key])}
                              <small>
                                {percent(
                                  dashboard.total
                                    ? (dashboard.counts[key] /
                                        dashboard.total) *
                                        100
                                    : 0,
                                )}
                              </small>
                            </strong>
                          </div>
                        ))}
                      </div>
                      <p className="chart-footnote">
                        Sentimento previsto para o texto completo.
                      </p>
                    </div>
                    <div className="panel timeline">
                      <div className="panel-heading">
                        <div>
                          <h2>Sentimentos ao longo do tempo</h2>
                          <p>Comentários agrupados pela data de publicação</p>
                        </div>
                        <span className="soft-tag">POR DIA</span>
                      </div>
                      {dashboard.timeline.length ? (
                        <>
                          <div className="chart-area">
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart
                                data={dashboard.timeline}
                                margin={{
                                  top: 10,
                                  right: 12,
                                  left: -25,
                                  bottom: 0,
                                }}
                                accessibilityLayer
                              >
                                <CartesianGrid
                                  stroke="#ebede7"
                                  vertical={false}
                                />
                                <XAxis
                                  dataKey="date"
                                  tickFormatter={dateLabel}
                                  tickLine={false}
                                  axisLine={false}
                                  fontSize={11}
                                  minTickGap={30}
                                />
                                <YAxis
                                  allowDecimals={false}
                                  tickLine={false}
                                  axisLine={false}
                                  fontSize={11}
                                />
                                <Tooltip
                                  labelFormatter={(value) =>
                                    dateLabel(String(value))
                                  }
                                  formatter={(value, name) => [
                                    value,
                                    labels[name as Sentiment],
                                  ]}
                                  contentStyle={{
                                    border: "1px solid #e4e7df",
                                    borderRadius: 10,
                                    fontSize: 12,
                                  }}
                                />
                                {(
                                  [
                                    "positivo",
                                    "negativo",
                                    "neutro",
                                  ] as Sentiment[]
                                ).map((key) => (
                                  <Line
                                    key={key}
                                    name={key}
                                    type="linear"
                                    dataKey={key}
                                    stroke={colors[key]}
                                    strokeWidth={2.2}
                                    strokeDasharray={
                                      key === "neutro"
                                        ? "3 4"
                                        : key === "negativo"
                                          ? "8 4"
                                          : undefined
                                    }
                                    dot={{ r: 3, strokeWidth: 0 }}
                                    activeDot={{ r: 5 }}
                                    isAnimationActive={false}
                                  />
                                ))}
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                          <div className="sr-only">
                            <table>
                              <caption>
                                Sentimentos por data de publicação
                              </caption>
                              <thead>
                                <tr>
                                  <th scope="col">Data</th>
                                  <th scope="col">Positivo</th>
                                  <th scope="col">Negativo</th>
                                  <th scope="col">Neutro</th>
                                </tr>
                              </thead>
                              <tbody>
                                {dashboard.timeline.map((item) => (
                                  <tr key={item.date}>
                                    <th scope="row">{item.date}</th>
                                    <td>{item.positivo}</td>
                                    <td>{item.negativo}</td>
                                    <td>{item.neutro}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                          <div className="chart-legend">
                            {(
                              ["positivo", "negativo", "neutro"] as Sentiment[]
                            ).map((key) => (
                              <span key={key}>
                                <i style={{ background: colors[key] }} />
                                {labels[key]}
                              </span>
                            ))}
                          </div>
                        </>
                      ) : (
                        <div className="chart-empty">
                          <BarChart3 size={27} />
                          <p>Sem datas para mostrar nesta seleção.</p>
                        </div>
                      )}
                      <p className="chart-footnote">
                        {dashboard.undated
                          ? `${dashboard.undated} comentários sem data não aparecem no gráfico.`
                          : "As datas são as informadas no arquivo importado."}
                      </p>
                    </div>
                  </section>
                  <section
                    className="panel mentions"
                    aria-labelledby="mentions-title"
                  >
                    <div className="panel-heading">
                      <div>
                        <h2 id="mentions-title">
                          Por trás dos números, comentários.
                        </h2>
                        <p>
                          Leia os textos e considere o contexto de cada opinião.
                        </p>
                      </div>
                      <span className="soft-tag">
                        {number(dashboard.total)} REGISTROS
                      </span>
                    </div>
                    <div className="filter-row">
                      <label className="search-input">
                        <Search size={16} />
                        <span className="sr-only">Buscar nos comentários</span>
                        <input
                          value={search}
                          onChange={(e) => setSearch(e.target.value)}
                          placeholder="Buscar nos comentários…"
                          maxLength={200}
                        />
                      </label>
                      <label>
                        <span className="sr-only">Filtrar sentimento</span>
                        <select
                          aria-label="Filtrar sentimento"
                          value={filters.sentiment}
                          onChange={(e) =>
                            updateFilter("sentiment", e.target.value)
                          }
                        >
                          <option value="">Todos os sentimentos</option>
                          {(
                            ["positivo", "negativo", "neutro"] as Sentiment[]
                          ).map((key) => (
                            <option key={key} value={key}>
                              {labels[key]}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        <span className="sr-only">Filtrar fonte</span>
                        <select
                          aria-label="Filtrar fonte"
                          value={filters.source}
                          onChange={(e) =>
                            updateFilter("source", e.target.value)
                          }
                        >
                          <option value="">Todas as fontes</option>
                          {dashboard.sources.map((source) => (
                            <option key={source} value={source}>
                              {source}
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>
                    <div className="date-filters">
                      <label>
                        Data inicial
                        <input
                          type="date"
                          aria-label="Data inicial"
                          max={filters.end || undefined}
                          value={filters.start}
                          onChange={(e) =>
                            updateFilter("start", e.target.value)
                          }
                        />
                      </label>
                      <label>
                        Data final
                        <input
                          type="date"
                          aria-label="Data final"
                          min={filters.start || undefined}
                          value={filters.end}
                          onChange={(e) => updateFilter("end", e.target.value)}
                        />
                      </label>
                      <label className="batch-filter">
                        <span className="sr-only">Filtrar importação</span>
                        <select
                          aria-label="Filtrar importação"
                          value={filters.import_id}
                          onChange={(e) =>
                            updateFilter("import_id", e.target.value)
                          }
                        >
                          <option value="">Todas as importações</option>
                          {dashboard.imports.map((batch) => (
                            <option key={batch.id} value={batch.id}>
                              {batch.filename} · #{batch.id} · {batch.total}{" "}
                              comentários
                            </option>
                          ))}
                        </select>
                      </label>
                      {activeFilters && (
                        <button className="text-button" onClick={resetFilters}>
                          <X size={13} />
                          Limpar filtros
                        </button>
                      )}
                    </div>
                    {refreshError && (
                      <div className="notice error filter-error" role="alert">
                        {refreshError.message} Os resultados exibidos são da
                        última consulta válida.
                        <button
                          className="text-button"
                          onClick={() =>
                            refreshError.status === 422
                              ? resetFilters()
                              : setRevision((r) => r + 1)
                          }
                        >
                          {refreshError.status === 422
                            ? "Limpar filtros"
                            : "Tentar novamente"}
                        </button>
                      </div>
                    )}
                    <div
                      className="table-wrap"
                      role="region"
                      aria-label="Comentários classificados"
                      tabIndex={0}
                    >
                      <table>
                        <caption className="sr-only">
                          Comentários, sentimento previsto, fonte e data
                        </caption>
                        <thead>
                          <tr>
                            <th scope="col">Comentário</th>
                            <th scope="col">Sentimento</th>
                            <th scope="col">Fonte</th>
                            <th scope="col">Data</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dashboard.mentions.map((mention) => (
                            <tr key={mention.id}>
                              <td>
                                <p>{mention.text}</p>
                                <div className="mobile-details">
                                  <span
                                    className={`sentiment-badge ${mention.sentiment}`}
                                  >
                                    <i />
                                    {labels[mention.sentiment]}
                                  </span>
                                  <span>
                                    {mention.source} ·{" "}
                                    {mention.published_at
                                      ? dateLabel(mention.published_at)
                                      : "Sem data"}
                                  </span>
                                </div>
                                {Boolean(mention.is_demo) && (
                                  <small className="fictitious">
                                    Exemplo fictício
                                  </small>
                                )}
                              </td>
                              <td>
                                <span
                                  className={`sentiment-badge ${mention.sentiment}`}
                                >
                                  <i />
                                  {labels[mention.sentiment]}
                                </span>
                              </td>
                              <td className="source-cell">{mention.source}</td>
                              <td className="date-cell">
                                {mention.published_at
                                  ? new Date(
                                      mention.published_at + "T12:00:00",
                                    ).toLocaleDateString("pt-BR")
                                  : "Sem data"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {!dashboard.mentions.length && (
                      <div className="no-results">
                        <Search size={24} />
                        <h3>Nenhum comentário nesta seleção.</h3>
                        <p>Tente outro termo ou ajuste os filtros.</p>
                        <button className="text-button" onClick={resetFilters}>
                          Limpar filtros
                        </button>
                      </div>
                    )}
                    <div className="pagination">
                      <span>
                        {dashboard.total
                          ? `${(dashboard.pagination.page - 1) * dashboard.pagination.page_size + 1}–${Math.min(dashboard.pagination.page * dashboard.pagination.page_size, dashboard.total)} de ${number(dashboard.total)} comentários`
                          : "0 comentários"}
                      </span>
                      <div>
                        <button
                          aria-label="Página anterior"
                          disabled={dashboard.pagination.page <= 1}
                          aria-disabled={
                            loading || dashboard.pagination.page <= 1
                          }
                          onClick={() => {
                            if (!loading) {
                              setPage(dashboard.pagination.page - 1);
                              paginationRef.current?.focus();
                            }
                          }}
                        >
                          <ChevronLeft size={16} />
                        </button>
                        <span
                          ref={paginationRef}
                          tabIndex={-1}
                          aria-live="polite"
                        >
                          Página {dashboard.pagination.page} de{" "}
                          {dashboard.pagination.pages}
                        </span>
                        <button
                          aria-label="Próxima página"
                          disabled={
                            dashboard.pagination.page >=
                            dashboard.pagination.pages
                          }
                          aria-disabled={
                            loading ||
                            dashboard.pagination.page >=
                              dashboard.pagination.pages
                          }
                          onClick={() => {
                            if (!loading) {
                              setPage(dashboard.pagination.page + 1);
                              paginationRef.current?.focus();
                            }
                          }}
                        >
                          <ChevronRight size={16} />
                        </button>
                      </div>
                    </div>
                  </section>
                </div>
              ) : null}
            </>
          )}

          <div className="sr-only" role="status" aria-live="polite">
            {loading
              ? "Atualizando resultados."
              : dashboard
                ? `${dashboard.total} comentários na seleção. Página ${dashboard.pagination.page} de ${dashboard.pagination.pages}.`
                : ""}
          </div>
        </main>
        <footer className="page-footer">
          <span>Opinare · Análise de sentimentos</span>
        </footer>
      </div>

      <dialog
        ref={dialogRef}
        className="import-dialog"
        aria-labelledby="import-title"
        onCancel={(e) => {
          e.preventDefault();
          closeImport();
        }}
        onClick={(e) => {
          if (e.target === e.currentTarget) closeImport();
        }}
      >
        <div className="dialog-content">
          <button
            ref={closeButton}
            className="dialog-close"
            aria-label="Fechar importação"
            onClick={closeImport}
            disabled={importing}
          >
            <X size={20} />
          </button>
          <span className="dialog-icon">
            <FileSpreadsheet size={26} />
          </span>
          <p className="eyebrow">UMA NOVA PERSPECTIVA</p>
          <h2 id="import-title">Importar comentários</h2>
          <p>
            Envie um arquivo CSV em UTF-8. O modelo vai analisar e salvar os
            comentários para você consultar aqui.
          </p>
          <div className="csv-guide">
            <strong>Como organizar o arquivo</strong>
            <p>
              <code>texto</code> é obrigatório. <code>data</code>,{" "}
              <code>fonte</code> e <code>id_origem</code> são opcionais.
            </p>
            <p>
              Datas: AAAA-MM-DD · até 1.000 linhas · até 1 MB
              <br />
              Separador: vírgula ou ponto e vírgula.
            </p>
            <a href="/api/example.csv" download>
              <ArrowDownToLine size={14} />
              Baixar modelo CSV
            </a>
          </div>
          <label className={`file-picker ${file ? "has-file" : ""}`}>
            <Upload size={24} />
            <strong>{file ? file.name : "Escolher arquivo CSV"}</strong>
            <span>
              {file
                ? `${number(file.size)} bytes · clique para trocar`
                : "Selecione o arquivo no seu computador"}
            </span>
            <input
              key={fileInputKey}
              type="file"
              accept=".csv,text/csv"
              disabled={importing}
              aria-label="Escolher arquivo CSV"
              onChange={(e) => {
                setFile(e.target.files?.[0] || null);
                setImportError(null);
              }}
            />
          </label>
          {importError && (
            <div
              ref={errorRef}
              tabIndex={-1}
              className="notice error import-errors"
              role="alert"
            >
              <strong>{importError.message}</strong>
              <p>Após corrigir o arquivo, selecione-o novamente.</p>
              {importError.issues?.length > 0 && (
                <ul>
                  {importError.issues.slice(0, 10).map((issue, i) => (
                    <li key={i}>
                      Linha {issue.line}: {issue.message}
                    </li>
                  ))}
                  {importError.issues.length > 10 && (
                    <li>
                      Mais {importError.issues.length - 10} linhas precisam de
                      correção.
                    </li>
                  )}
                </ul>
              )}
            </div>
          )}
          {model && !model.ready && (
            <div className="notice error" role="alert">
              O modelo ainda não está pronto. Execute a preparação descrita no
              README e reinicie a aplicação.
            </div>
          )}
          {!model && (
            <p role="status">
              {refreshError
                ? "Não foi possível consultar o modelo. Feche esta janela e tente novamente."
                : "Consultando a disponibilidade do modelo…"}
            </p>
          )}
          <p className="privacy-note">
            <ShieldCheck size={15} />
            Use textos sem informações pessoais desnecessárias. Os dados ficam
            neste computador.
          </p>
          <div className="dialog-actions">
            <button
              className="button secondary"
              disabled={importing}
              onClick={closeImport}
            >
              Cancelar
            </button>
            <button
              className="button primary"
              disabled={!file || !model?.ready}
              aria-disabled={!file || importing || !model?.ready}
              aria-busy={importing}
              onClick={() => importData(false)}
            >
              {importing ? (
                <LoaderCircle className="spin" size={17} />
              ) : (
                <Sparkles size={17} />
              )}
              {importing ? "Analisando comentários…" : "Importar e analisar"}
            </button>
          </div>
        </div>
      </dialog>
    </div>
  );
}

function Stat({
  label,
  value,
  total,
  kind,
}: {
  label: string;
  value: number;
  total: number;
  kind: Sentiment | "total";
}) {
  const Icon =
    kind === "positivo"
      ? Smile
      : kind === "negativo"
        ? Frown
        : kind === "neutro"
          ? Minus
          : MessageSquareText;
  return (
    <article className={`stat-card ${kind}`}>
      <div>
        <span>{label}</span>
        <Icon size={19} />
      </div>
      <strong>{number(value)}</strong>
      <p>
        {kind === "total"
          ? "Uma opinião de cada vez"
          : `${percent(total ? (value / total) * 100 : 0)} dos comentários`}
      </p>
    </article>
  );
}

function Methodology({
  model,
  loading,
  error,
}: {
  model: ModelInfo | null;
  loading: boolean;
  error: ApiError | null;
}) {
  if (loading && !model)
    return (
      <div className="loading-state" role="status">
        <LoaderCircle className="spin" />
        Carregando metodologia…
      </div>
    );
  if (error && !model)
    return (
      <section className="panel method-panel">
        <h2>Não foi possível carregar a metodologia.</h2>
        <p>Confira a conexão com a aplicação e tente novamente.</p>
      </section>
    );
  const report = model?.report;
  if (!report)
    return (
      <section className="panel method-panel">
        <h2>Avaliação ainda não disponível.</h2>
        <p>
          Execute o treinamento descrito no README para gerar o modelo e o
          relatório de validação.
        </p>
      </section>
    );
  const metrics = report.metrics;
  const comparison = model?.comparison;
  return (
    <div className="methodology">
      {comparison && <ComparisonResults model={model} />}
      <div className="demo-banner">
        <FlaskConical size={19} />
        <span>
          <strong>
            {comparison
              ? "Validação do modelo ativo."
              : "Avaliação preliminar."}
          </strong>{" "}
          Os números abaixo são da validação.{" "}
          {comparison
            ? "Os números de teste acima foram calculados uma vez após a seleção do modelo."
            : report.test_evaluated
              ? "O teste final já foi consultado; confira o relatório específico."
              : "O conjunto de teste final permanece reservado."}
        </span>
      </div>
      <div className="panel method-panel">
        <p className="eyebrow">MODELO ATIVO</p>
        <h2>{report.model_name}</h2>
        <p>
          {model?.active_model === "bertimbau"
            ? "BERTimbau ajustado para três classes de sentimento em português."
            : "TF-IDF de palavras e caracteres com regressão logística para três classes."}{" "}
          Os exemplos fictícios do painel não entram nas métricas.
        </p>
        <div className="method-stats">
          <div>
            <strong>{percent(metrics.f1_macro * 100)}</strong>
            <span>F1 macro</span>
            <small>Mesmo peso para cada classe</small>
          </div>
          <div>
            <strong>{percent(metrics.accuracy * 100)}</strong>
            <span>Acurácia</span>
            <small>Acertos na validação</small>
          </div>
          <div>
            <strong>{number(report.samples.train)}</strong>
            <span>Textos de treino</span>
            <small>
              {number(report.samples.validation)} textos de validação
            </small>
          </div>
        </div>
        <h3>Desempenho por classe</h3>
        <div
          className="table-wrap"
          role="region"
          aria-label="Desempenho por classe"
          tabIndex={0}
        >
          <table className="metrics-table">
            <thead>
              <tr>
                <th scope="col">Classe</th>
                <th scope="col">Precisão</th>
                <th scope="col">Recall</th>
                <th scope="col">F1</th>
                <th scope="col">Exemplos</th>
              </tr>
            </thead>
            <tbody>
              {metrics.label_order.map((key) => {
                const item = metrics.classification_report[key];
                return (
                  <tr key={key}>
                    <td>
                      <span className={`sentiment-badge ${key}`}>
                        <i />
                        {labels[key]}
                      </span>
                    </td>
                    <td>{percent(item.precision * 100)}</td>
                    <td>{percent(item.recall * 100)}</td>
                    <td>{percent(item["f1-score"] * 100)}</td>
                    <td>{item.support}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <h3>Matriz de confusão</h3>
        <p className="small-muted">
          Linhas: classe real. Colunas: classe prevista. A diagonal indica os
          acertos.
        </p>
        <div
          className="table-wrap"
          role="region"
          aria-label="Matriz de confusão"
          tabIndex={0}
        >
          <table className="confusion-table">
            <thead>
              <tr>
                <th scope="col">Real / prevista</th>
                {metrics.label_order.map((key) => (
                  <th key={key}>{labels[key]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {metrics.confusion_matrix.map((row, i) => (
                <tr key={i}>
                  <th scope="row">{labels[metrics.label_order[i]]}</th>
                  {row.map((value, j) => (
                    <td key={j} className={i === j ? "diagonal" : ""}>
                      {value}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="dataset-note">
          <BookOpen size={20} />
          <div>
            <strong>
              {report.dataset || "Dados de treinamento em português"}
            </strong>
            <p>
              Divisões oficiais preservadas, com remoção de duplicados e
              sobreposição entre treino e validação.{" "}
              {number(report.samples.test_reserved)} textos de teste
              {comparison ? " avaliados na comparação" : " reservados"}.
            </p>
            {report.source_url && (
              <a href={report.source_url} target="_blank" rel="noreferrer">
                Consultar base de treinamento (abre em nova aba){" "}
                <ArrowRight size={13} />
              </a>
            )}
          </div>
        </div>
        <h3>Limitações e próximos passos</h3>
        <ul className="limitations">
          {report.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        {report.configuration && (
          <>
            <h3>Configuração do treinamento</h3>
            <dl className="configuration-list">
              {Object.entries(report.configuration).map(([key, value]) => (
                <div key={key}>
                  <dt>{configurationNames[key] || key.replaceAll("_", " ")}</dt>
                  <dd>{String(value)}</dd>
                </div>
              ))}
              {report.best_epoch != null && (
                <div>
                  <dt>Melhor época</dt>
                  <dd>{report.best_epoch}</dd>
                </div>
              )}
              {report.training_seconds != null && (
                <div>
                  <dt>Tempo de treino</dt>
                  <dd>
                    {number(Math.round(report.training_seconds))} segundos
                  </dd>
                </div>
              )}
              {report.hardware?.gpu && (
                <div>
                  <dt>GPU</dt>
                  <dd>{report.hardware.gpu}</dd>
                </div>
              )}
            </dl>
          </>
        )}
        <p className="model-version">Modelo: {model?.version}</p>
      </div>
    </div>
  );
}

function ComparisonResults({ model }: { model: ModelInfo }) {
  const comparison = model.comparison!;
  const active = comparison.models.find(
    (item) => item.model_id === model.version,
  );
  return (
    <div className="panel method-panel">
      <p className="eyebrow">COMPARAÇÃO EM TESTES RESERVADOS</p>
      <h2>Resultados por conjunto de teste</h2>
      <p>
        Os números de teste foram calculados uma vez após a seleção do modelo.
      </p>
      <p>
        {comparison.protocol} {comparison.selection_rule}
      </p>
      <div
        className="table-wrap"
        role="region"
        aria-label="Comparação de modelos"
        tabIndex={0}
      >
        <table className="metrics-table comparison-table">
          <thead>
            <tr>
              <th scope="col">Modelo</th>
              {comparison.test_sets.map((set) => (
                <th scope="col" key={set.key}>
                  {set.name}
                  <br />
                  F1 macro / acurácia
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {comparison.models.map((item) => (
              <tr
                key={item.key}
                className={
                  item.model_id === model.version ? "active-comparison" : ""
                }
              >
                <th scope="row">
                  {item.name}
                  {item.model_id === model.version ? " · ativo" : ""}
                </th>
                {comparison.test_sets.map((set) => {
                  const metrics = comparison.results[item.key]?.[set.key];
                  return (
                    <td key={set.key}>
                      {metrics
                        ? `${percent(metrics.f1_macro * 100)} / ${percent(metrics.accuracy * 100)}`
                        : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
            <tr>
              <th scope="row">Classe majoritária (piso)</th>
              {comparison.test_sets.map((set) => {
                const metrics = comparison.dummy[set.key];
                return (
                  <td key={set.key}>
                    {metrics
                      ? `${percent(metrics.f1_macro * 100)} / ${percent(metrics.accuracy * 100)}`
                      : "—"}
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>
      {active &&
        comparison.test_sets.map((set) => {
          const metrics = comparison.results[active.key]?.[set.key];
          return (
            metrics && (
              <TestMetrics key={set.key} name={set.name} metrics={metrics} />
            )
          );
        })}
      <h3>Fontes dos dados e licenças</h3>
      <ul className="limitations">
        {comparison.data_sources.map((source) => (
          <li key={source.url}>
            <a href={source.url} target="_blank" rel="noreferrer">
              {source.name}
            </a>{" "}
            · {source.license} · {source.use}
          </li>
        ))}
      </ul>
      <h3>Limitações da comparação</h3>
      <ul className="limitations">
        {comparison.limitations.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function TestMetrics({ name, metrics }: { name: string; metrics: Metrics }) {
  return (
    <section className="test-metrics">
      <h3>{name}: desempenho do modelo ativo</h3>
      <p>
        F1 macro: {percent(metrics.f1_macro * 100)} · acurácia:{" "}
        {percent(metrics.accuracy * 100)}
      </p>
      <div
        className="table-wrap"
        role="region"
        aria-label={`Desempenho por classe: ${name}`}
        tabIndex={0}
      >
        <table className="metrics-table">
          <thead>
            <tr>
              <th scope="col">Classe</th>
              <th scope="col">Precisão</th>
              <th scope="col">Recall</th>
              <th scope="col">F1</th>
              <th scope="col">Exemplos</th>
            </tr>
          </thead>
          <tbody>
            {metrics.label_order.map((label) => {
              const item = metrics.classification_report[label];
              return (
                <tr key={label}>
                  <th scope="row">{labels[label]}</th>
                  <td>{percent(item.precision * 100)}</td>
                  <td>{percent(item.recall * 100)}</td>
                  <td>{percent(item["f1-score"] * 100)}</td>
                  <td>{item.support}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <h3>Matriz de confusão: {name}</h3>
      <p>Linhas: classe real. Colunas: classe prevista.</p>
      <div
        className="table-wrap"
        role="region"
        aria-label={`Matriz de confusão: ${name}`}
        tabIndex={0}
      >
        <table className="confusion-table">
          <thead>
            <tr>
              <th scope="col">Real / prevista</th>
              {metrics.label_order.map((label) => (
                <th scope="col" key={label}>
                  {labels[label]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metrics.confusion_matrix.map((row, i) => (
              <tr key={i}>
                <th scope="row">{labels[metrics.label_order[i]]}</th>
                {row.map((value, j) => (
                  <td key={j} className={i === j ? "diagonal" : ""}>
                    {value}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
