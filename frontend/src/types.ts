export type Sentiment = "positivo" | "negativo" | "neutro";
export type Mention = {
  id: number;
  text: string;
  published_at: string | null;
  source: string;
  sentiment: Sentiment;
  import_id: number;
  is_demo: number;
};
export type Dashboard = {
  total: number;
  total_all: number;
  counts: Record<Sentiment, number>;
  undated: number;
  demo_count: number;
  timeline: ({ date: string } & Record<Sentiment, number>)[];
  mentions: Mention[];
  sources: string[];
  imports: {
    id: number;
    filename: string;
    total: number;
    is_demo: number;
    created_at: string;
  }[];
  pagination: { page: number; pages: number; page_size: number };
};
export type ModelInfo = {
  ready: boolean;
  version: string;
  report: null | {
    model_name: string;
    dataset: string;
    source_url: string;
    model_id: string;
    evaluation_split: string;
    test_evaluated: boolean;
    samples: { train: number; validation: number; test_reserved: number };
    metrics: {
      accuracy: number;
      f1_macro: number;
      label_order: Sentiment[];
      confusion_matrix: number[][];
      classification_report: Record<
        Sentiment,
        {
          precision: number;
          recall: number;
          "f1-score": number;
          support: number;
        }
      >;
    };
    limitations: string[];
  };
};
export type ImportResult = {
  inserted: number;
  duplicates: number;
  import_id: number;
  is_demo: boolean;
};
export class ApiError extends Error {
  issues: { line: number; message: string }[];
  status: number;
  constructor(
    message: string,
    issues: { line: number; message: string }[] = [],
    status = 0,
  ) {
    super(message);
    this.issues = issues;
    this.status = status;
  }
}
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError(
      init?.body instanceof FormData
        ? "Não foi possível enviar o arquivo. Se ele foi editado, selecione-o novamente. Confira também se a aplicação está em execução."
        : "Não foi possível conectar. Confira se a aplicação está em execução.",
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    if (typeof detail === "string")
      throw new ApiError(detail, [], response.status);
    if (detail?.message)
      throw new ApiError(detail.message, detail.issues, response.status);
    throw new ApiError(
      "Não foi possível concluir. Confira os filtros ou tente novamente.",
      [],
      response.status,
    );
  }
  return response.json() as Promise<T>;
}
