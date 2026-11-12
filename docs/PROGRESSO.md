# Progresso do MVP

Atualização: 12/11/2026. Versão para a apresentação final, branch `feat/modelo-final`.

## Implementado

- Backend Python/FastAPI e painel React/TypeScript/Vite, servidos juntos na versão compilada.
- Importação de CSV UTF-8 com validação completa antes de salvar, lote atômico, bloqueio de arquivos repetidos e deduplicação.
- Persistência SQLite com lote, versão do modelo e metadados originais.
- Painel com totais, evolução por dia, listagem paginada, busca e filtros (sentimento, fonte, período e importação).
- **Classificador BERTimbau Base ajustado pela equipe** (UMSAB + B2W), carregado de `artifacts/bertimbau-sentimento/` depois de conferir o SHA-256 de cada arquivo e o mapeamento das classes. Se o modelo faltar, estiver corrompido ou o PyTorch não estiver instalado, a aplicação **usa o baseline TF-IDF** e mostra o motivo.
- **Testar uma frase**: `POST /api/analyze` classifica um texto sem salvar e devolve o rótulo e as pontuações por classe do modelo ativo e do baseline. A interface mostra os dois lado a lado, com estados de carregamento, texto vazio, texto longo demais e erro.
- Metodologia com a tabela comparativa nos testes, destaque do modelo ativo, métricas por classe, matrizes de confusão, fontes e licenças, configuração do treino e limitações.
- Reclassificação da base existente (`python -m experiments.reclassify`): backup verificado, todas as previsões calculadas antes de gravar, transação única. A base local foi reclassificada: 54 comentários, 19 rótulos alterados, com backup em `var/backups/`.
- Portabilidade: `preparar.ps1` instala o PyTorch para CPU (216 MB) e reaproveita os modelos existentes, sem retreinar. `iniciar.ps1` funciona sem internet. O README tem a seção "Levar para outro computador".

## Evidência dos classificadores

Teste consultado uma única vez, depois da seleção pela validação (`reports/comparacao_modelos.json`):

| Modelo | UMSAB teste (869): F1 macro / acurácia | B2W teste (1.500): F1 macro / acurácia |
| --- | --- | --- |
| Baseline v1 (UMSAB) | 0,5887 / 0,5880 | 0,4647 / 0,4827 |
| Baseline combinado (UMSAB + B2W) | 0,6109 / 0,6110 | 0,7082 / 0,7073 |
| BERTimbau ajustado (ativo) | 0,7091 / 0,7089 | 0,7499 / 0,7500 |
| Classe majoritária | 0,1664 / 0,3326 | 0,1667 / 0,3333 |

F1 macro na validação combinada (1.223 textos), critério de seleção: baseline combinado 0,6686; BERTimbau 0,7303 (época 3 de 3). O baseline v1 continua documentado em `reports/baseline_validation.json` (0,5778 na validação UMSAB).

Checagem de sanidade, que não é métrica, no CSV fictício da livraria (24 frases, com rótulos propostos que ainda precisam ser revisados pela equipe): baseline v1 coincide em 13, baseline combinado em 19 e BERTimbau em 23.

Desempenho de inferência neste computador (i7-8750H, GTX 1050 Ti):

| Dispositivo | Carga do modelo | 1.000 comentários curtos | 1 frase |
| --- | --- | --- | --- |
| CPU | 9,4 s | 14,4 s | 39 ms |
| GPU | 10,7 s | 6,4 s | 10 ms |

## Verificações executadas

- **56 testes automatizados aprovados** (eram 36). Os novos cobrem a seleção e o fallback do classificador (pasta ausente, PyTorch ausente, hash divergente, relatório incompleto, `OPINARE_MODEL=baseline`), as pontuações, `/api/analyze` (sucesso, vazio, longo demais, campo ausente, 503, nada persistido, origem externa), a reclassificação (backup, falha sem alteração, base vazia) e o preparo do B2W (colunas, notas, duplicados conflitantes, hash).
- Ruff sem apontamentos; build TypeScript/Vite aprovado.
- Verificação em Chromium (Playwright) contra a aplicação real com o BERTimbau ativo e uma base separada: demonstração, importação da livraria (24 comentários), teste de frase (vazio e mais de 5.000 caracteres bloqueados, duas frases analisadas), fechamento por Esc com o foco devolvido ao botão, tabela comparativa e larguras de 1440, 390 e 320 px sem rolagem horizontal da página nem do diálogo, sem erros no console.
- Auditoria estrutural da interface por inspeção de código. Foram corrigidos: os botões do cabeçalho no celular, o botão desativado sem modelo, o anúncio do resultado para leitores de tela, o erro limpo ao editar, a possibilidade de fechar durante a análise e os rótulos acessíveis das barras e dos links.

Limites: não houve teste com leitor de tela nem em Safari ou Firefox. O desempenho no computador da apresentação não foi medido.

## Pendências acadêmicas

1. Revisar os rótulos propostos da livraria e a classificação qualitativa de `docs/ANALISE_ERROS.md`.
2. Medir o desempenho em comentários reais de pequenos negócios locais (domínio-alvo ainda não medido).
3. Obter uma primeira devolutiva de potenciais usuários.
4. Escrever o artigo para a P2 (19/11) com os relatórios e a análise de erros.
