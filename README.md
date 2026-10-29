# Opinare

MVP acadêmico de análise de sentimentos em português brasileiro, desenvolvido para Laboratório de Inovação Social do iCEV.

**Importe comentários -> classifique -> salve -> consulte o painel.**

O classificador ativo é um Transformer já treinado para sentimentos em português. O baseline treinado pelo projeto foi preservado para comparação. O painel mostra positivos, negativos e neutros, evolução por dia, comentários, busca e filtros. A área **Modelo e metodologia** apresenta as métricas da checagem sintética e a matriz de confusão. A importação e o painel funcionam localmente, sem contas ou serviços pagos.

## Usar agora no Windows

Neste computador, o ambiente, o modelo e o painel já foram preparados. Na pasta do projeto:

```powershell
.\iniciar.ps1
```

Abra [http://127.0.0.1:8000](http://127.0.0.1:8000). No primeiro acesso, clique em **Explorar demonstração** ou importe um CSV próprio. A demonstração contém 30 comentários fictícios, identificados na interface; as previsões são produzidas pelo modelo real.

Se o PowerShell bloquear scripts locais, use `powershell -ExecutionPolicy Bypass -File .\iniciar.ps1` para esta execução, sem alterar a política do computador.

Mantenha o terminal aberto durante o uso. Encerre com `Ctrl+C`. Os dados ficam em `var/opinare.sqlite3` e continuam disponíveis após reiniciar. O projeto só escuta em `127.0.0.1`; esta versão foi feita para apresentação local.

## Preparar em outro computador

Pré-requisitos: Python 3.11 a 3.14, [uv](https://docs.astral.sh/uv/getting-started/installation/) e Node.js LTS com npm. As versões das dependências estão fixadas em `uv.lock` e `frontend/package-lock.json`.

```powershell
.\preparar.ps1
.\iniciar.ps1
```

A preparação instala as dependências, treina o baseline no recorte português do UMSAB, baixa uma versão fixada do checkpoint externo e gera a comparação funcional, além de compilar a interface. O checkpoint tem aproximadamente 540 MB. Requer internet nessa etapa. Depois, a aplicação e as fontes do painel funcionam sem internet. O modelo e os dados brutos não são incluídos no Git; a preparação os recria.

Para refazer o treinamento do baseline: `.\preparar.ps1 -RecriarModelo`. Reinicie o servidor após trocar o modelo.

Em Linux/macOS, execute na raiz:

```sh
uv sync --frozen
uv run python -m experiments.train
uv run python -m experiments.prepare_transformer
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

## Modelo ativo e comparação

O modelo ativo é `pysentimiento/bertweet-pt-sentiment`, checkpoint externo fixado na revisão `726612815d49447cbfe3f55bbfc2993c1f5fad10`. Executa localmente em CPU, com pesos safetensors e hashes verificados, sem enviar comentários a serviços externos. Não foi treinado nem ajustado com os CSVs demonstrativos ou com a amostra de controle do projeto.

Na mesma amostra funcional de **30 frases sintéticas novas com rótulos propostos pelo assistente Codex**, o baseline acertou **18/30** e o Transformer **29/30**. F1 macro: **0,5979** e **0,9666**, respectivamente. A amostra foi criada após observar falhas do baseline, sem revisão humana, e não é cega. É uma checagem funcional pequena, não uma estimativa de acurácia comercial. As frases ficam em `data/evaluation/checagem_sentimentos.json`, e o relatório completo em `reports/transformer_functional_check.json`.

A preparação usa a rotina de português do pysentimiento, fixada no código com sua licença original para uso não comercial e pesquisa científica. A normalização interna inglesa do tokenizador está desativada. A substituição legada de caracteres é desativada para preservar emojis compostos antes de sua conversão para português.

O checkpoint foi ajustado em dados relacionados ao TweetSentBR. Portanto, métricas calculadas sobre UMSAB poderiam ter sobreposição com seus dados de treinamento e não seriam uma comparação independente. Nesta atualização, não foi calculado um novo resultado no teste UMSAB. A avaliação científica independente continua pendente.

A interface mostra explicitamente que as métricas atuais são de uma checagem sintética. Textos longos são divididos em janelas de tokens; todas as partes participam da previsão por agregação. Isso evita descartar silenciosamente o final de um texto, mas ainda pode diluir opiniões curtas em textos extensos.

### Baseline inicial preservado

- **Modelo:** TF-IDF de palavras (1–2) e caracteres (3–5), seguido de regressão logística, com parâmetros fixos e semente 42.
- **Dados:** UMSAB, recorte português derivado de SentiBR/TweetSentBR, disponibilizado pelos pesquisadores do XLM-T.
- **Treino:** 1.839 textos da divisão oficial.
- **Validação:** 323 textos; removida uma sobreposição com o treino.
- **F1 macro de validação:** 0,5778.
- **Acurácia de validação:** 0,5759.
- **Teste:** 870 textos reservados, sem avaliação nesta primeira entrega.

Esses resultados são preliminares. Não representam desempenho validado para empresas. Os dados têm domínio ligado a programas de televisão, e os exemplos de negócios usados no painel são fictícios. A classe neutra teve maior dificuldade na validação. Ironia, negação, gírias e diferenças de domínio podem produzir erros.

As métricas completas, o comparador de classe majoritária, os parâmetros e a matriz de confusão estão em `reports/baseline_validation.json`. A versão da fonte e os hashes dos arquivos estão em `reports/dataset_manifest.json`. O relatório de validação contém somente estatísticas, sem republicar textos do corpus.

O conjunto de teste não é utilizado para ajustar o modelo. Quando o procedimento final estiver definido, a avaliação reservada pode ser executada uma vez com:

```powershell
.\.venv\Scripts\python.exe -m experiments.train --test
```

Esse comando avalia somente o baseline e gera `reports/baseline_test.json`; não deve ser usado durante ajustes iterativos. A comparação funcional com Transformer foi realizada. A comparação científica em dados reais independentes permanece como próximo marco.

### Atualizar resultados já importados

Trocar o modelo não muda automaticamente classificações históricas. Para recalculá-las, encerre o servidor e execute:

```powershell
.\.venv\Scripts\python.exe -m experiments.reclassify
```

O comando cria uma cópia SQLite em `var/backups/`, calcula todas as previsões antes de escrever e salva classes e versões em uma transação única. Preserva IDs, textos, datas, fontes e identidade dos arquivos. Se a base mudar durante a análise, cancela a atualização. Se houver uma falha, os resultados anteriores são preservados. Reinicie o servidor depois.

### Fontes e uso dos dados

- [Checkpoint português de sentimentos](https://huggingface.co/pysentimiento/bertweet-pt-sentiment) e [projeto pysentimiento](https://github.com/pysentimiento/pysentimiento). O modelo externo mantém as condições de uso e a atribuição de seus autores. Os pesos não são incluídos no Git.

- [Repositório XLM-T / UMSAB](https://github.com/cardiffnlp/xlm-t), versão `874214d64d96599eb869a033c22ec2cc57d19256`.
- Barbieri, Espinosa Anke e Camacho-Collados (2022). [XLM-T: Multilingual Language Models in Twitter for Sentiment Analysis and Beyond](https://aclanthology.org/2022.lrec-1.27/).
- Brum e Nunes (2018). [Building a Sentiment Corpus of Tweets in Brazilian Portuguese](https://aclanthology.org/L18-1658/).

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

1. Alinhar o recorte com o professor e discutir a contribuição para pequenos negócios locais.
2. Complementar a comparação funcional com avaliação científica em dados reais independentes.
3. Analisar erros e conversar com potenciais usuários; não há validação de mercado realizada.
4. Consolidar metodologia, resultados e limitações no artigo.
5. Estabilizar para a apresentação de 12/11 e a P2 de 19/11, conforme o cronograma fornecido.

Login, múltiplas empresas, APIs de redes sociais e atualização em tempo real ficam fora desta primeira versão. Consulte `docs/PLANO_MVP.md` e `docs/ROTEIRO_MONITORIA.md` para o contexto acadêmico.
