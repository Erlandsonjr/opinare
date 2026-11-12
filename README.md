# Opinare

MVP acadêmico de análise de sentimentos em português brasileiro, desenvolvido para Laboratório de Inovação Social do iCEV.

**Importe comentários -> classifique -> salve -> consulte o painel.**

O classificador ativo é o **BERTimbau Base ajustado pela equipe** com tweets (UMSAB) e avaliações reais de e-commerce (B2W). Ele foi comparado com um baseline TF-IDF nos mesmos dados, em testes reservados. O painel mostra positivos, negativos e neutros, evolução por dia, comentários, busca e filtros. O botão **Testar uma frase** compara ao vivo o modelo ativo e o baseline, sem salvar nada. A área **Modelo e metodologia** traz a tabela comparativa, as métricas por classe e as matrizes de confusão. Tudo roda localmente, sem contas ou serviços pagos.

## Usar agora no Windows

Neste computador, o ambiente, o modelo e o painel já foram preparados. Na pasta do projeto:

```powershell
.\iniciar.ps1
```

Abra [http://127.0.0.1:8000](http://127.0.0.1:8000). No primeiro acesso, clique em **Explorar demonstração** ou importe um CSV próprio. A demonstração contém 30 comentários fictícios, identificados na interface; as previsões são produzidas pelo modelo real.

Se o PowerShell bloquear scripts locais, use `powershell -ExecutionPolicy Bypass -File .\iniciar.ps1` para esta execução, sem alterar a política do computador.

Mantenha o terminal aberto durante o uso. Encerre com `Ctrl+C`. Os dados ficam em `var/opinare.sqlite3` e continuam disponíveis após reiniciar. O projeto só escuta em `127.0.0.1`; esta versão foi feita para apresentação local.

## Preparar em outro computador

Pré-requisitos: [uv](https://docs.astral.sh/uv/getting-started/installation/) e Node.js LTS com npm. O uv instala sozinho o Python 3.12 fixado em `.python-version`, exigido pelo PyTorch. As versões das dependências estão fixadas em `uv.lock` e `frontend/package-lock.json`.

```powershell
.\preparar.ps1
.\iniciar.ps1
```

A preparação instala as dependências (com PyTorch para CPU, cerca de 216 MB), baixa os dados acadêmicos (UMSAB e B2W, cerca de 50 MB), treina os dois baselines TF-IDF, que levam poucos minutos, e compila a interface. Requer internet nessa etapa. Depois, a aplicação funciona sem internet. Modelos e dados brutos não são incluídos no Git.

**O BERTimbau ajustado não é treinado pela preparação.** Se a pasta `artifacts/bertimbau-sentimento/` existir e for válida, ele é usado; caso contrário, a aplicação usa o baseline TF-IDF e informa isso no topo do painel e no terminal. Treinar o Transformer é um passo manual (seção "Treinar novamente").

Para refazer os baselines: `.\preparar.ps1 -RecriarModelo`. Reinicie o servidor após trocar um modelo.

### Levar para outro computador

O modelo treinado nunca precisa ser treinado de novo em outra máquina, e não é preciso ter placa de vídeo NVIDIA: a inferência roda na CPU.

1. **Na véspera, com internet**, no outro computador: clone o repositório (branch desta versão) e instale uv e Node.js.
2. Copie deste computador para a mesma pasta do projeto no outro:
   - `artifacts/` inteira (cerca de 420 MB: BERTimbau ajustado e baselines);
   - `var/opinare.sqlite3`, se quiser levar os dados já importados na demonstração.
3. **Não copie `.venv`**: ambientes do uv não podem ser movidos entre computadores.
4. Execute `.\preparar.ps1` uma vez. Ele reaproveita os modelos copiados, sem retreinar, instala o PyTorch para CPU e mostra se o BERTimbau foi validado.
5. No dia, `.\iniciar.ps1` funciona sem internet.

Se o BERTimbau ficar lento demais no computador da apresentação, inicie com o baseline: `$env:OPINARE_MODEL = 'baseline'; .\iniciar.ps1`.

Em Linux/macOS, execute na raiz:

```sh
uv sync --frozen --extra cpu
uv run python -m experiments.train
uv run python -m experiments.train_combined
npm ci --prefix frontend
npm run build --prefix frontend
uv run uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

## Formato de importação

CSV UTF-8, com vírgula ou ponto e vírgula. Até 1 MB e 1.000 registros; cada texto pode ter até 5.000 caracteres.

| Coluna | Obrigatória | Formato |
| --- | --- | --- |
| `texto` | Sim | Comentário a analisar |
| `data` | Não | `AAAA-MM-DD`; vazio para data desconhecida |
| `fonte` | Não | Nome do canal de origem, até 100 caracteres |
| `id_origem` | Não | Identificador opcional, até 200 caracteres |

Exemplo mínimo:

```csv
texto,data,fonte,id_origem
"Gostei do atendimento!",2026-10-28,Minha fonte,1
"Qual é o horário?",,Minha fonte,2
```

Há arquivos em `data/examples/`, e a interface permite baixar um modelo CSV com o cabeçalho. Textos que contenham o separador precisam de aspas, conforme o formato CSV.

O sistema valida o arquivo inteiro antes de importar. Se uma linha estiver inválida ou o modelo falhar, o lote não é salvo. Arquivos repetidos são recusados e comentários idênticos, com os mesmos metadados, não são inseridos novamente. Sem identificador da origem, comentários iguais na mesma data/fonte são considerados duplicados; isso pode reunir ocorrências legítimas idênticas, uma simplificação do MVP.

Os filtros afetam os indicadores, o gráfico e a listagem. Datas ausentes ficam fora do gráfico e continuam na contagem geral quando não há filtro de período. A data da importação não é usada como data da publicação. A busca ignora diferenças de maiúsculas/minúsculas ASCII; a equivalência de acentos e de caixa Unicode não está garantida no SQLite padrão.

Evite nomes, contatos e outras informações pessoais desnecessárias nos textos enviados.

## Modelos e resultados

Três modelos foram treinados pela equipe e avaliados **uma única vez** nos testes reservados, depois da escolha do modelo:

| Modelo | Treino | UMSAB teste (869): F1 macro / acurácia | B2W teste (1.500): F1 macro / acurácia |
| --- | --- | --- | --- |
| Baseline v1: TF-IDF + regressão logística | UMSAB (1.839 tweets) | 0,589 / 0,588 | 0,465 / 0,483 |
| Baseline combinado: mesmo pipeline | UMSAB + B2W (7.839) | 0,611 / 0,611 | 0,708 / 0,707 |
| **BERTimbau Base ajustado (ativo)** | UMSAB + B2W (7.839) | **0,709 / 0,709** | **0,750 / 0,750** |
| Classe majoritária (piso) | — | 0,166 / 0,333 | 0,167 / 0,333 |

- **Por que o BERTimbau está ativo:** a regra foi definida antes do teste: entre os modelos treinados com os mesmos dados, vence o de maior F1 macro na validação combinada. O BERTimbau teve 0,730 e o baseline combinado, 0,669. O teste confirmou a escolha nos dois conjuntos.
- **Dados:** UMSAB (tweets sobre TV) mais B2W-Reviews01, com 2.000/300/500 avaliações por classe em treino/validação/teste e semente 42. Do B2W, só o texto e a nota são lidos; as colunas de perfil do avaliador são descartadas. Notas 1–2 viram negativo, 3 vira neutro e 4–5 vira positivo. As divisões são disjuntas por texto normalizado, inclusive entre UMSAB e B2W. Os CSVs de exemplo nunca entram no treino.
- **BERTimbau:** `neuralmind/bert-base-portuguese-cased`, revisão `94d69c9`, licença MIT. Configuração: comprimento máximo de 128 tokens, taxa de aprendizado 2e-5, 3 épocas, lote efetivo 16 (8 × 2 de acumulação), 10% de aquecimento, decaimento de pesos 0,01 e semente 42. A melhor época foi a 3. O treino levou cerca de 20 minutos numa GTX 1050 Ti (4 GB).
- **Preparação do texto:** conservadora. Mantém acentos, pontuação, negações e emojis; troca apenas links e @usuários.
- **Inferência:** na CPU, carrega em cerca de 9 s e classifica 1.000 comentários curtos em cerca de 14 s (medido neste computador, i7-8750H). Textos acima de 128 tokens são divididos em janelas, sem corte.

Limitações: a classe neutra é a mais difícil (F1 de cerca de 0,64 nos dois testes) e, no B2W, a nota 3 é um rótulo ruidoso. Ironia e opiniões mistas ainda geram erros. O domínio-alvo, comentários de pequenos negócios locais, **não foi medido**. O CSV fictício da livraria é apenas uma checagem de sanidade, com rótulos propostos que ainda precisam ser revisados pela equipe, e não uma estimativa de acurácia. Veja `docs/ANALISE_ERROS.md`.

Rastreabilidade: `reports/comparacao_modelos.json` (comparação no teste), `reports/bertimbau_validation.json`, `reports/baseline_combinado_validation.json`, `reports/baseline_validation.json` (validação), `reports/dataset_manifest_combinado.json` (hashes e contagens) e `reports/erros_teste_b2w.json` (amostra de erros).

### Treinar novamente

Comandos reproduzíveis, na ordem. Os três primeiros rodam na CPU:

```powershell
.\.venv\Scripts\python.exe -m experiments.train            # baseline v1 (UMSAB)
.\.venv\Scripts\python.exe -m experiments.data             # divisões e manifesto (baixa o B2W)
.\.venv\Scripts\python.exe -m experiments.train_combined   # baseline combinado
uv sync --frozen --extra cu118                             # PyTorch com CUDA 11.8 (2,8 GB), só para treinar
.\.venv\Scripts\python.exe -m experiments.train_transformer
.\.venv\Scripts\python.exe -m experiments.compare          # teste: executar uma única vez
.\.venv\Scripts\python.exe -m experiments.reclassify       # reclassifica a base local, com backup
```

`experiments.compare` se recusa a rodar se a comparação já existir, para impedir ajustes guiados pelo teste. O build CUDA 11.8 foi escolhido porque ainda suporta GPUs Pascal (sm_61). Sem GPU, `train_transformer --cpu --limit N` permite um treino reduzido, muito mais lento.

### Fontes e uso dos dados

- [Repositório XLM-T / UMSAB](https://github.com/cardiffnlp/xlm-t), versão `874214d64d96599eb869a033c22ec2cc57d19256`.
- Barbieri, Espinosa Anke e Camacho-Collados (2022). [XLM-T: Multilingual Language Models in Twitter for Sentiment Analysis and Beyond](https://aclanthology.org/2022.lrec-1.27/).
- Brum e Nunes (2018). [Building a Sentiment Corpus of Tweets in Brazilian Portuguese](https://aclanthology.org/L18-1658/).
- [B2W-Reviews01](https://github.com/americanas-tech/b2w-reviews01), commit `4639429ec698d7821fc99a0bc665fa213d9fcd5a`, licença CC BY-NC-SA 4.0 (uso não comercial, com atribuição). Real, Oshiro e Mafra (2019), *B2W-Reviews01: an open product reviews corpus*, STIL.
- [BERTimbau Base](https://huggingface.co/neuralmind/bert-base-portuguese-cased), revisão `94d69c95f98f7d5b2a8700c420230ae10def0baa`, licença MIT. Souza, Nogueira e Lotufo (2020), *BERTimbau: pretrained BERT models for Brazilian Portuguese*, BRACIS.

A fonte XLM-T informa que podem se aplicar restrições dos datasets originais e da plataforma. Não é feita aqui uma afirmação de licença irrestrita. Os textos brutos são baixados somente para uso acadêmico local e ficam fora do Git; verificar as condições da fonte antes de qualquer redistribuição ou uso diferente. Os CSVs fictícios de demonstração foram criados para este projeto e não contêm textos do corpus.

## Verificar e desenvolver

```powershell
.\verificar.ps1
```

Isso executa a análise estática Python, os testes de importação/API/modelo e a compilação TypeScript/React. Os testes da aplicação usam bancos temporários e não alteram os comentários do usuário. O teste de integração real exige o modelo preparado.

Para desenvolvimento com atualização automática, abra dois terminais:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

```powershell
npm.cmd run dev --prefix frontend
```

Abra `http://127.0.0.1:5173`. O Vite encaminha a API para a porta 8000. A documentação técnica da API está em `http://127.0.0.1:8000/docs`.

Estrutura:

```text
backend/       API, importação CSV, classificador e persistência SQLite
frontend/      Painel React, TypeScript e Vite
experiments/   Download reproduzível, treinamento e avaliação
data/examples/ CSVs fictícios para demonstração e importação
reports/       Estatísticas e rastreabilidade dos experimentos
tests/         Verificações das regras e integrações principais
docs/          Planejamento, progresso e roteiro de apresentação
```

## Próximas entregas

1. Medir o desempenho no domínio-alvo: rotular, com autorização, comentários reais de pequenos negócios locais.
2. Revisar uma amostra de notas 3 do B2W para estimar o ruído do rótulo neutro.
3. Conversar com potenciais usuários; não há validação de mercado realizada.
4. Consolidar metodologia, resultados e limitações no artigo (P2 de 19/11), a partir de `docs/ANALISE_ERROS.md` e dos relatórios.

Login, múltiplas empresas, APIs de redes sociais, coleta em tempo real e classificação por API de LLM ficam fora do escopo. Consulte `docs/PLANO_MVP.md`, `docs/PROGRESSO.md` e `docs/ROTEIRO_APRESENTACAO.md`.
