# Progresso do MVP

Atualização: 28/10/2026. Primeira versão funcional para a monitoria de 29/10.

## Implementado

- Backend Python/FastAPI e painel React/TypeScript/Vite, servidos juntos na versão compilada.
- Importação CSV UTF-8 com vírgula ou ponto e vírgula; validação completa antes de salvar.
- Modelo real TF-IDF + regressão logística, com três classes e preparação conservadora dos textos.
- Persistência SQLite com lote, data de importação, versão do modelo e metadados originais.
- Importação atômica, bloqueio de arquivos repetidos e deduplicação de comentários idênticos com os mesmos metadados.
- Resumo por sentimento, proporções, evolução por dia e listagem paginada.
- Busca e filtros de sentimento, fonte, período e importação, compartilhados pelos indicadores e pela tabela.
- Estados de carregamento, base vazia, busca sem resultados, falhas de importação e modelo indisponível.
- Visualização específica para celular, com o sentimento junto ao comentário.
- Área de metodologia com métricas reais por classe, matriz de confusão, origem dos dados e limitações.
- Demonstração com 30 comentários fictícios, explicitamente identificados; modelo CSV vazio para preenchimento.
- Fontes locais; aplicação utilizável sem internet após a preparação.
- Comandos de preparação, início e verificação no Windows, além de instruções para Linux/macOS.

## Evidência do classificador

| Item | Resultado |
| --- | --- |
| Dataset | UMSAB, recorte português derivado de SentiBR/TweetSentBR |
| Fonte fixada | XLM-T, commit `874214d64d96599eb869a033c22ec2cc57d19256` |
| Treinamento | 1.839 textos |
| Validação | 323 textos; removida uma sobreposição com o treino |
| F1 macro | 0,577755 |
| Acurácia | 0,575851 |
| Teste | 870 textos reservados, sem métricas consultadas nesta implementação |
| Modelo local | `tfidf-logreg-umsab-pt-7c73a5308862` |

O identificador do modelo incorpora um hash do código de treinamento e preparação, a versão da fonte e a versão do scikit-learn. O relatório servido pela aplicação fica dentro do mesmo artefato do modelo. Os hashes dos arquivos de dados são verificados antes do treinamento.

Os textos brutos e o modelo local ficam fora do Git. Não há alegação de licença irrestrita dos dados. A preparação baixa a fonte acadêmica; conferir suas condições antes de redistribuir dados ou mudar a finalidade do uso.

## Verificações executadas

- **36 testes automatizados aprovados**, cobrindo CSV válido/inválido, codificação, datas, limites, duplicados, falha do modelo, rollback do lote, consultas e importações concorrentes, filtros, paginação, reinício da aplicação, limites locais de acesso e dados de treinamento.
- Análise estática Python aprovada.
- Compilação TypeScript e build Vite aprovados.
- Instalação reprodutível pelo comando `preparar.ps1` executada com sucesso. O npm informou zero vulnerabilidades conhecidas nessa execução.
- Verificação real em Chromium: importação válida, inválida e duplicada; persistência após recarregar; foco no erro, limpeza do arquivo, retorno do foco ao cancelar e foco no título após sucesso; navegação da paginação; filtro de sentimento; busca sem resultados, intervalo de datas inválido e recuperação de falha de conexão simulada. As importações válidas/inválidas/duplicadas foram testadas contra a API real; cenários adicionais de foco após sucesso e falha de conexão usaram respostas simuladas no navegador.
- Layout conferido em larguras de **320, 390, 768, 1440, 1550 e 1920 px**, sem rolagem horizontal da página nos cenários verificados. Também conferidos o diálogo de importação em 320 px e a metodologia em 390 px.
- Capturas do painel, comentários e metodologia inspecionadas visualmente.

As verificações de navegador usaram uma base local separada, `var/browser-check.sqlite3`. A base de demonstração principal fica em `var/opinare.sqlite3` e não recebeu os registros adicionais dos testes de importação.

Limites: verificação em Chromium, sem teste em leitor de tela, Safari ou Firefox. As proteções são adequadas à execução local demonstrada; não foi feita implantação pública nem criada autenticação. Os testes emitiram um aviso de descontinuação da biblioteca de cliente HTTP do ambiente de testes, sem falhas funcionais.

## Pendências acadêmicas

1. Comparar um Transformer com o baseline, em condições documentadas e comparáveis.
2. Analisar qualitativamente erros, inclusive a diferença entre o domínio de televisão do corpus e comentários empresariais.
3. Confirmar o recorte de contribuição social com o professor e obter uma primeira devolutiva de potenciais usuários.
4. Escrever o artigo e consolidar os resultados finais.
5. Consultar o teste reservado somente quando o procedimento final estiver definido.

O resultado atual é uma demonstração funcional com baseline avaliado. Não é uma validação comercial nem uma medição de desempenho em comentários de empresas.
