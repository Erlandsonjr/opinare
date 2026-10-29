# Opinare: estudo inicial e plano de MVP

Data: 28/10/2026. Planejamento para a conversa com o professor em 29/10/2026.

## Recomendação

Construir uma aplicação web local que importe um CSV de comentários em português brasileiro, classifique cada texto como positivo, negativo ou neutro, salve os resultados e apresente um painel com resumo, evolução temporal e consulta às mensagens.

O primeiro avanço demonstrável deve ser esse fluxo completo com um classificador simples. A comparação com um Transformer continua no plano científico da entrega final. A programação da aplicação ainda não foi iniciada nesta etapa: este arquivo registra a análise e as decisões propostas.

## 1. Leitura dos cinco documentos

### Fundamentação Opinare

O arquivo reúne nove referências candidatas sobre análise de sentimentos, português brasileiro, BERT, avaliação e dashboard. Dá suporte à metodologia, mas não representa uma revisão bibliográfica já escrita nem experimentos realizados. TweetSentBR e BERTimbau aparecem como candidatos; não são escolhas fechadas. Na próxima etapa, ler os trabalhos efetivamente utilizados e conferir seus metadados antes de montar as referências do artigo.

### Requisitos e escopo

O núcleo está bem delimitado: entrada de dados, preparação, classificação em três classes, armazenamento e dashboard. RF01 a RF08 são P0; filtros e contexto monitorado são P1. A importação de dados equivalentes já é permitida. A evolução temporal depende da disponibilidade de datas, e uma meta numérica de desempenho só deve ser definida depois do baseline.

Isso permite entregar um MVP útil sem integrar redes sociais. A avaliação com dados rotulados e o registro das limitações fazem parte da entrega, não são complementos opcionais.

### Proposta técnica

Prevê TF-IDF com classificador linear como baseline, comparação com Transformer e escolha do modelo integrado pelas métricas e pelo custo. Propõe Python, scikit-learn, FastAPI, PostgreSQL e React/Vite. Aceita ajustes justificados na tecnologia e trata importação como caminho garantido.

A proposta final espera baseline e Transformer avaliados em condições comparáveis. Portanto, começar apenas pelo baseline é uma estratégia de implementação; eliminar a comparação da entrega final exigiria um alinhamento com o professor.

### Cronograma

O documento previa componentes principais integrados até 28/10. Como o repositório está vazio, essa etapa está atrasada em relação ao planejamento original. A resposta recomendada é reduzir dependências e replanejar por entregas demonstráveis.

Marcos registrados: 29/10, orientação para artigos; 12/11, apresentação final; 19/11, entrega da P2. O usuário descreveu o encontro de amanhã como monitoria: confirmar com o professor a dinâmica atual, mantendo essas datas como referência documental.

### Pitch

Explica a proposta e o público empresarial, mas enfatiza tempo real e usa afirmações amplas sobre mercado e limitações das ferramentas existentes. Os documentos posteriores tornam o compromisso mais viável: importação, processamento em lote e avaliação mensurável.

Para a monitoria, apresentar o recorte atualizado. As afirmações de mercado devem ser tratadas como hipóteses enquanto não houver pesquisa ou conversas com usuários que as sustentem. O pitch prevê essas conversas como próximo passo; não há evidência, nos arquivos, de que já tenham ocorrido.

## 2. Escopo fechado proposto

### Essencial para a aplicação

1. Importar CSV em UTF-8, com coluna `texto` obrigatória; `data`, `fonte` e `id_origem` opcionais. Escolher um único formato inicialmente.
2. Validar arquivo, cabeçalhos e textos vazios. Explicar erros por linha e o resultado da importação.
3. Preparar textos de forma conservadora, preservando negações, acentos, pontuação e emojis quando relevantes à abordagem.
4. Classificar com um modelo treinado nas três classes. Não transformar falha de processamento em sentimento neutro.
5. Persistir texto, metadados disponíveis, classe, identificação do modelo e lote de importação.
6. Mostrar total analisado, quantidade e porcentagem por classe, além de mensagens com seus rótulos.
7. Mostrar evolução por data original quando existir. Informar registros sem data; não usar a data de importação como data da publicação.
8. Manter resultados após reiniciar a aplicação.

### Essencial para a entrega acadêmica

- Dataset com origem, condições de uso e rótulos documentados.
- Baseline reproduzível e comparação com um Transformer, conforme a proposta técnica.
- Acurácia, precisão, recall e F1 por classe, F1 macro e matriz de confusão.
- Divisões de treino, validação e teste registradas; teste reservado à avaliação final.
- Pequena análise de erros e limitações, incluindo diferenças entre o domínio do dataset e comentários empresariais.
- README com execução, metodologia e resultados que possam ser conferidos.

### Somente depois do núcleo

Filtros por sentimento, período e fonte, conforme disponibilidade dos metadados. Um campo de contexto do lote pode identificar a empresa ou produto sem criar um módulo de cadastro.

### Fora desta entrega proposta

Login, perfis, múltiplas empresas com ambientes separados, pagamentos, integrações de redes sociais, scraping, alertas automáticos, atualização contínua, respostas a clientes, geração de recomendações por IA, imagens, áudio e vídeo. Hospedagem pública não é pré-requisito para a primeira demonstração.

## 3. Arquitetura e tecnologias

Fluxo: CSV -> validação/preparação -> classificador -> banco local -> API -> painel.

| Parte | Escolha proposta | Motivo |
| --- | --- | --- |
| Modelo inicial | TF-IDF + regressão logística, com scikit-learn | Concretiza uma das opções já previstas e fornece uma referência simples |
| Backend | Python + FastAPI | Mantém a direção da proposta e usa o mesmo ecossistema do classificador |
| Persistência inicial | SQLite | Reduz a configuração para demonstração local e mantém persistência real |
| Interface | React + Vite, com uma única página principal | Mantém a proposta sem criar fluxos adicionais |
| Experimento posterior | Um Transformer para classificação em três classes | Cumpre a comparação científica sem obrigar a aplicação a depender dele |

A substituição inicial de PostgreSQL por SQLite é uma recomendação deste estudo, não uma decisão já aprovada pelo professor. Registrar a justificativa; manter PostgreSQL se houver exigência acadêmica ou infraestrutura pronta que torne seu uso mais simples para o grupo.

BERTimbau Base é um modelo pré-treinado de linguagem, não um classificador de sentimentos pronto. Seu uso nesta tarefa requer adaptação supervisionada ou um checkpoint apropriado já ajustado, com origem e rótulos verificados. Não é uma dependência da primeira demonstração.

Manter o classificador em um módulo separado no mesmo backend. Não criar microserviço, fila de processamento ou arquitetura distribuída para esse volume inicial.

Organização sugerida para a implementação: `backend/`, `frontend/`, `experiments/`, `data/examples/` e `docs/`. Definir detalhes de tabelas e rotas quando a implementação começar.

## 4. Dados e avaliação

### Primeiro bloqueio a resolver

Verificar um dataset com texto completo acessível, português brasileiro, três classes e condições de uso claras. TweetSentBR é candidato coerente com as referências, mas este estudo não confirmou o download nem as condições da base completa. Não planejar a noite supondo que seu acesso esteja garantido.

O artigo original descreve textos sobre programas de televisão. Mesmo se a base for escolhida, registrar que desempenho nesse domínio não comprova o mesmo desempenho em avaliações de empresas.

Limitar a investigação inicial a aproximadamente uma hora. Se o candidato não estiver disponível, buscar outra base de três classes com procedência verificável. Uma base binária não resolve o requisito de neutro. Se não houver base adequada a tempo, declarar a pendência e mostrar somente o progresso de software que realmente existir.

### Separação dos dados

- Treinamento e avaliação: dados rotulados, com partições estáveis. Usar divisão oficial quando apropriada; caso contrário, documentar a divisão e a semente.
- Demonstração da interface: pequeno CSV de aproximadamente 30 a 50 comentários, com dados fictícios claramente identificados ou textos cujo uso seja permitido. Esse tamanho é uma sugestão para a demonstração, não um tamanho suficiente para validar cientificamente o modelo.
- Validação do problema: comentários e observações de potenciais usuários, obtidos e usados de modo apropriado. Não confundir essa validação com métricas do classificador.

Remover duplicatas ou agrupá-las antes das divisões, evitando que textos equivalentes apareçam no treino e no teste. Ajustar o TF-IDF somente no treino. Guardar exemplos do teste para avaliação, sem selecionar hiperparâmetros por seus resultados.

Para a monitoria, métricas preliminares de validação podem demonstrar avanço, desde que identificadas como preliminares. Os resultados finais devem usar o teste reservado. Dados sintéticos e exemplos escolhidos para parecerem fáceis não devem sustentar afirmações de acurácia.

O pipeline de treinamento, avaliação e inferência deve compartilhar a preparação de texto e registrar a versão do modelo. Não mostrar porcentagem de confiança como probabilidade garantida de acerto.

## 5. Plano até a monitoria de 29/10

Estimativa de trabalho focado: aproximadamente 6 a 9 horas, sujeita ao acesso ao dataset e ao ambiente. É uma referência de planejamento, não uma garantia de conclusão.

| Ordem | Atividade | Evidência de avanço |
| --- | --- | --- |
| 1 | Fechar CSV, classes e limite do MVP; verificar dataset | Fonte, colunas e limitações documentadas |
| 2 | Preparar dados, treinar baseline e registrar avaliação preliminar | Modelo salvo, comando reproduzível e relatório real |
| 3 | Implementar importação, inferência e armazenamento | Um arquivo percorre o fluxo e os resultados persistem |
| 4 | Montar painel único conectado à API | Contagens e mensagens correspondem ao arquivo importado |
| 5 | Conferir fluxo completo e preparar demonstração | Execução repetível e roteiro curto |

Concentrar primeiro o esforço no fluxo real com poucos registros. Refinar o visual quando os números do painel já vierem do classificador e do banco.

Se faltar tempo, reduzir o acabamento visual e adiar filtros. Manter classificação, persistência e transparência sobre os resultados. Se o modelo ainda não estiver disponível, qualquer dado pré-classificado usado na interface precisa ser identificado como demonstração de interface; não apresentar essa versão como MVP completo.

### O que levar amanhã

- Este recorte de escopo e as decisões técnicas propostas.
- Uma demonstração de 3 a 5 minutos do que estiver efetivamente implementado: importar, analisar, consultar e mostrar persistência.
- Uma evidência do baseline, quando disponível, com dados e limitações explícitos.
- O cronograma ajustado até 12/11 e 19/11.
- Pontos para alinhar: importação como fonte do MVP, SQLite para versão local, comparação com Transformer na etapa seguinte e recorte de contribuição social.

## 6. Plano até a entrega final

| Período | Prioridade | Critério para encerrar |
| --- | --- | --- |
| 28 a 29/10 | Primeira versão demonstrável e conversa com o professor | Fluxo real inicial e decisões pendentes registradas |
| 30/10 a 04/11 | Completar RF01 a RF08; avaliar um Transformer; escrever metodologia | Aplicação integrada e comparação reproduzível |
| 05 a 08/11 | Corrigir erros, analisar previsões, validar utilidade e consolidar resultados | Limitações e resultados prontos para discussão |
| 09 a 11/11 | Estabilizar sistema, preparar material e ensaiar | Demonstração local repetível sem novas funcionalidades |
| 12/11 | Apresentação final, conforme cronograma fornecido | Demonstração e explicação das decisões |
| 13 a 18/11 | Ajustes finais, revisão do artigo e organização do repositório | Código, instruções e artigo coerentes entre si |
| 19/11 | Entrega da P2, conforme cronograma fornecido | Repositório, documentação e artigo completos |

Se o Transformer trouxer pouco ganho ou custo elevado, o baseline pode continuar integrado. A comparação deve explicar a escolha. Se a comparação não couber no prazo, negociar explicitamente a alteração da proposta com o professor.

## 7. Divisão de trabalho e automação

Para os quatro integrantes, sugerir frentes de dados/modelo, backend/importação, painel e integração/documentação/validação. O grupo pode distribuir pessoas conforme familiaridade; este estudo não atribui nomes nem presume competências.

A automação pode preparar a estrutura do projeto, componentes, importação, banco local, treinamento, relatórios de métricas, verificações essenciais e instruções de execução. Comandos reproduzíveis devem substituir etapas manuais repetidas.

O grupo continua responsável por conferir a procedência e os rótulos dos dados, entender o que o classificador faz, interpretar métricas, validar utilidade com pessoas e explicar o trabalho ao professor. Não apresentar conteúdo gerado como evidência de experimento não realizado.

## 8. Contribuição social e critérios de conclusão

Como a disciplina é Laboratório de Inovação Social, explicitar um beneficiário concreto: por exemplo, pequenos negócios locais que precisam organizar comentários sem uma equipe dedicada. É uma hipótese de recorte, a validar com o professor e com potenciais usuários; não é uma validação já realizada.

Uma conversa curta com um ou dois potenciais usuários pode verificar se o painel ajuda a entender comentários e identificar problemas recorrentes. Registrar observações com as limitações dessa amostra, sem alegar validação ampla de mercado.

O MVP estará pronto quando importar um arquivo válido, classificar com modelo real, salvar e recuperar resultados, mostrar contagens consistentes e permitir consultar textos; apresentar evolução somente com datas disponíveis; explicar estados vazios e erros; e acompanhar tudo com avaliação reproduzível e limitações documentadas.

As verificações essenciais devem cobrir arquivo inválido, texto vazio, ausência de data, falha do classificador, persistência após reinício e consistência entre listagem e totais. Não exigir que qualquer lote produza necessariamente todas as classes: o modelo deve suportar as três, mas a distribuição depende dos textos.

## Fontes e limites deste estudo

Foram lidos os cinco arquivos indicados pelo usuário, incluindo as sete páginas de requisitos, as três de cronograma, as oito da proposta técnica e os seis slides do pitch, com notas. As tabelas relevantes dos PDFs foram também conferidas visualmente. O repositório contém apenas a estrutura Git, sem commits ou implementação anterior.

Documentos locais originais, na pasta `G:/My Drive/Junior/Education/College/iCev/2026.2/Lab_Inovacao/Opinare P1/Opinare P1/`:

- `Fundamentação Opinare.txt`.
- `Opinare - Requisitos e Escopo.pdf`.
- `Opinare Cronograma.pdf`.
- `Opinare Proposta Tecnica.pdf`.
- `Opinare_Pitch.pptx`.

Referências externas consultadas para conferir os pontos técnicos:

- [Artigo original do TweetSentBR](https://aclanthology.org/L18-1658.pdf): domínio e três classes do corpus; não comprova disponibilidade atual dos arquivos completos.
- [Ficha oficial do BERTimbau Base](https://huggingface.co/neuralmind/bert-base-portuguese-cased): natureza do modelo pré-treinado.
- [Extração de características no scikit-learn](https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction) e [regressão logística](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html): componentes do baseline proposto.
- [Pipeline do scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html): encadeamento de preparação e classificador.
- [Bancos relacionais com FastAPI](https://fastapi.tiangolo.com/tutorial/sql-databases/): uso de SQLite e possibilidade de PostgreSQL.

Não foram treinados modelos, baixados datasets, medidos desempenhos, entrevistados usuários ou implementadas funcionalidades nesta etapa. Os documentos são fontes de contexto; decisões e tarefas neles descritas não foram tratadas como autorização para implementar ou publicar o sistema.
