# Análise de erros do modelo selecionado

Atualização: 12/11/2026. Modelo: BERTimbau Base ajustado (UMSAB + B2W), `bertimbau-b2w-umsab-cbd682b00250`.

Fonte dos números: `reports/comparacao_modelos.json` (avaliação única nos testes reservados). Fonte dos exemplos B2W: `reports/erros_teste_b2w.json`, uma amostra aleatória de 80 erros, sorteada com semente 42. Os textos do B2W-Reviews01 são reproduzidos com atribuição, sob a licença CC BY-NC-SA 4.0. Os tweets do UMSAB não são republicados aqui: os casos são apenas descritos.

A divisão por causa é **qualitativa**. Foi feita sobre a amostra e não mede a proporção de cada causa no teste. A equipe deve revisar a classificação antes de usá-la no artigo.

## Visão geral

| Conjunto de teste | Textos | Erros | Erros que envolvem a classe neutra | Inversões positivo ↔ negativo |
| --- | --- | --- | --- | --- |
| B2W (avaliações de e-commerce) | 1.500 | 375 | 363 | 12 |
| UMSAB (tweets sobre TV) | 869 | 253 | 211 | 42 |

Leitura: o modelo quase nunca confunde elogio com reclamação em avaliações de produtos. A dificuldade está na fronteira com o **neutro**. No B2W, 105 avaliações positivas foram previstas como neutras, e 106 neutras foram previstas como positivas. O F1 da classe neutra é 0,637 no B2W e 0,638 no UMSAB, contra 0,74 a 0,84 nas classes polares.

## 1. Ruído de rótulo: nota 3 não significa texto neutro

No B2W, o rótulo vem da nota dada pelo cliente: 1–2 é negativo, 3 é neutro e 4–5 é positivo. A nota resume a experiência inteira, não o texto. Muitos "erros" são o modelo lendo corretamente um texto cujo rótulo é discutível.

- *"Os livros são ótimos e vieram bem embalados. As histórias são ótimas!! Adorei!!"*: rótulo **neutro** (nota 3), previsto **positivo**.
- *"Gostei muito, superou as expectativas, recomendo! O produto chegou antes da data prevista, estou satisfeito."*: rótulo **neutro**, previsto **positivo**.
- *"Das muitas compras no site, esta foi a pior delas, empresa não cumpre prazo de entrega."*: rótulo **neutro**, previsto **negativo**.
- *"Não gostei do tempo de entrega, demora muito, […] já passou da data de entrega e nada."*: rótulo **neutro**, previsto **negativo**.
- *"Fraco, produto bem mais ou menos e deixou a desejar"*: rótulo **negativo** (nota 1–2), previsto **neutro**. É um caso limítrofe.

Implicação: parte do teto de desempenho vem do mapeamento nota → classe, não do modelo. Rotular manualmente uma amostra seria o próximo passo para medir esse ruído.

## 2. Opinião mista: elogio e crítica no mesmo texto

O texto tem polaridades opostas, e o rótulo depende de qual parte o cliente valorizou mais.

- *"É uma cortina bonita, mas o tecido é muito fino e ela deixa passar muita luz."*: rótulo **negativo**, previsto **neutro**.
- *"Um bom aparelho, mas com uma bateria muito ruim, dura no máximo 36 horas"*: rótulo **negativo**, previsto **neutro**.
- *"Atendeu minhas expectativas, porém o material é frágil."*: rótulo **negativo**, previsto **neutro**.
- *"O produto em si é bom, mas a empresa não é nada boa, […] o produto chegou dia 22/02/2018"*: rótulo **neutro**, previsto **negativo**.
- *"Tive um atraso enorme na entrega […] porém o produto atinge a expectativa"*: rótulo **positivo**, previsto **negativo**. É uma das raras inversões de polaridade.

Implicação: para pequenos negócios, separar aspectos ("produto" vs. "entrega/atendimento") seria mais útil do que um único rótulo por comentário. Fica como trabalho futuro.

## 3. Negação e construções indiretas

- *"Não achei aparelho com o mesmo nível de hardware nessa faixa de preço. Até o momento funciona perfeitamente"*: rótulo **positivo**, previsto **neutro**. O baseline combinado previu **negativo**: o "não" é um elogio indireto.
- *"[…] Não Recomendo utilizar muito molhado, é bom esperar uns 5 minutos que o resultado é bem melhor"*: rótulo **positivo**, previsto **neutro**. O "não recomendo" faz parte de uma dica de uso, não é uma crítica.
- *"Funciona perfeitamente para o fim que se destina."*: rótulo **positivo**, previsto **neutro**. É um elogio contido, sem palavras fortes.

Observação: nas frases de demonstração, o BERTimbau acertou negações simples em que o baseline falha, como "Não tenho do que reclamar". Isso é ilustração, não métrica. Negações longas ou indiretas continuam difíceis.

## 4. Ironia, humor e exagero

- *"Chave top, solta e aperta parafusos, abre cofre de banco, abre a casa branca, abre a porta da área 51, abre as portas do céu."*: rótulo **positivo**, previsto **neutro**. O exagero humorístico é um elogio, mas o vocabulário é descritivo.
- No UMSAB, há tweets em que o autor reclama da chuva derrubando o sinal da TV com emojis de raiva; o rótulo é negativo e a previsão, neutra. Há também tweets em que gíria afetuosa do tipo "esse participante me mata" é lida como negativa, quando o rótulo é neutro.
- Caso fora do teste, usado na apresentação: *"Que maravilha, esperei duas horas pela pizza fria."* Os dois modelos preveem positivo. O sarcasmo continua sendo uma falha conhecida.

## 5. Perguntas e textos sem opinião explícita

Perguntas recebem nota como qualquer avaliação, mas o texto não expressa sentimento.

- *"Produto é original? Tem nota fiscal? Preciso saber?"*: rótulo **negativo**, previsto **neutro**.
- *"Gostaria de saber se esse produto tem bluetooth? ……"*: rótulo **positivo**, previsto **neutro**.
- *"O preço do frete está errado? Por gentileza deem uma olhada no preço do frete cobrado pra esse produto..."*: rótulo **negativo**, previsto **neutro**.

Para o painel, prever "neutro" em perguntas é o comportamento desejado. Esses erros pesam contra o modelo na métrica, mas não na utilidade.

## 6. Linguagem informal, pontuação repetida e emoji

- *"Muito bom, bonito, rápido, um pouco grande mas gostei bastante :D"*: rótulo **positivo**, previsto **neutro**. A pequena ressalva pesou mais do que o emoticon.
- *"otimo, fiquei muito satisfeito, recomendo !!!!!!!!…"*: rótulo **neutro**, previsto **positivo**. Aqui o ruído de rótulo provavelmente se soma à informalidade.
- No UMSAB, muitos erros são tweets formados quase só por hashtags de programas, anúncios de horário ("começou o programa", "vou assistir pela primeira vez") ou gírias. O rótulo humano depende de contexto que o texto não traz: por exemplo, um "cheguei a tempo de ver" rotulado como positivo e previsto como neutro.

## Mudança de domínio

O teste UMSAB (tweets sobre TV) tem F1 macro de 0,709, menor que o do B2W (0,750). Os tweets usam hashtags, nomes de participantes e humor de fandom, e o B2W tem só 2.000 exemplos de treino por classe. Comentários de pequenos negócios locais (atendimento, ambiente, cardápio) são um terceiro domínio, **não medido** por nenhum dos dois testes. O CSV fictício da livraria é só uma checagem de sanidade: 23 de 24 previsões do BERTimbau coincidem com rótulos propostos, que ainda precisam ser revisados pela equipe, e isso não é estimativa de acurácia.

## Próximos passos sugeridos

1. Rotular manualmente cerca de 200 comentários reais de negócios locais, com autorização, para medir o desempenho no domínio-alvo.
2. Revisar uma amostra de notas 3 do B2W para estimar o ruído do rótulo neutro.
3. Avaliar análise por aspecto (produto, entrega, atendimento) para opiniões mistas.
