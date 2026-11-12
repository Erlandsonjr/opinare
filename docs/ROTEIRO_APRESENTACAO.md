# Roteiro da apresentação final (12/11/2026)

Duração alvo: 8 a 9 minutos, mais perguntas. Todos os números citados vêm de `reports/comparacao_modelos.json` e `reports/bertimbau_validation.json`.

## Antes de começar (5 minutos antes)

Use uma base vazia só para a apresentação, assim a importação da livraria acontece ao vivo, sem mexer na base principal:

```powershell
$env:OPINARE_DB = "$PWD\var\apresentacao.sqlite3"
.\iniciar.ps1
```

- Se você já ensaiou com essa base, apague `var\apresentacao.sqlite3` antes (com o servidor parado). Senão, a importação da livraria será recusada como repetida.
- Espere a mensagem do servidor (cerca de 10 s, porque o BERTimbau é verificado ao iniciar). Abra `http://127.0.0.1:8000` e confira no topo: **"Modelo ativo: BERTimbau Base ajustado (UMSAB + B2W)"**.
- Deixe aberto no Explorador de Arquivos: `data\examples\teste_livraria_horizonte.csv`.
- Deixe as frases da seção 4 num bloco de notas para copiar e colar.
- Plano B: se o BERTimbau não carregar, o painel mostra o motivo e usa o baseline. Siga a demonstração e explique o fallback, que também é uma funcionalidade. Se a base de apresentação der problema, rode `.\iniciar.ps1` sem a variável: a base principal já tem a demonstração e a livraria, reclassificadas.

## 1. O problema (1 min)

- Pequenos negócios locais (cafés, livrarias, lojas de bairro) recebem comentários em vários canais e não têm equipe para lê-los e organizá-los.
- O Opinare importa esses comentários, classifica cada um como **positivo, negativo ou neutro** e mostra um painel: o que está bom, o que incomoda e como isso muda no tempo.
- Público beneficiado: o dono ou atendente do pequeno negócio. É uma hipótese de recorte social; ainda não fizemos validação com usuários.

## 2. Arquitetura em uma linha (20 s)

**CSV → validação e preparação do texto → classificador (BERTimbau ajustado) → SQLite → API FastAPI → painel React.** Tudo roda localmente, sem internet nem contas.

## 3. Demonstração ao vivo (4 min)

1. **Dados de demonstração:** clique em *Explorar demonstração*. São 30 comentários fictícios de um café, todos classificados agora pelo modelo. Mostre os totais, o gráfico por dia e a lista.
2. **Filtros:** filtre por *Negativo* e, depois, faça uma busca, por exemplo "atendimento". Comente que os indicadores e a lista obedecem ao mesmo filtro.
3. **Importação:** *Importar CSV* → `teste_livraria_horizonte.csv` → *Importar e analisar*. São 24 comentários de uma livraria fictícia, analisados e salvos de uma vez; se uma linha estiver inválida, nada é salvo. Filtre pela importação da livraria.
4. **Testar uma frase**, botão no topo. Cole uma frase de cada vez e mostre os dois cartões: o modelo ativo à esquerda e o baseline TF-IDF, treinado com os mesmos dados, à direita.

   | Frase | Baseline TF-IDF | BERTimbau | O que mostra |
   | --- | --- | --- | --- |
   | Não tenho do que reclamar, tudo certo com o pedido. | negativo | **positivo** | negação: "reclamar" sozinho engana o baseline |
   | O garçom foi um amor com a gente. | neutro | **positivo** | linguagem informal |
   | A loja fica no centro. | negativo | **neutro** | frase informativa, sem opinião |
   | Atendimento nota zero. | neutro | **negativo** | expressão idiomática; pontuação do BERTimbau baixa (≈0,41) |
   | **Falha honesta:** Que maravilha, esperei duas horas pela pizza fria. | positivo | positivo ✗ | sarcasmo: os dois erram |

   Diga sempre: "as barras são **pontuações do modelo**, não probabilidade garantida de acerto". As frases foram escolhidas para ilustrar; não são métrica. A métrica é a tabela a seguir.

## 4. Comparação e o que os números significam (1 min 30 s)

Abra **Modelo e metodologia**.

| Modelo | UMSAB teste (869 tweets) F1 macro | B2W teste (1.500 avaliações) F1 macro |
| --- | --- | --- |
| Baseline v1 (só tweets) | 0,589 | 0,465 |
| Baseline TF-IDF (tweets + B2W) | 0,611 | 0,708 |
| **BERTimbau ajustado (ativo)** | **0,709** | **0,750** |
| Classe majoritária (piso) | 0,166 | 0,167 |

- Dois ganhos separados. **Dados do domínio certo**: o baseline sai de 0,465 para 0,708 no B2W só por treinar com avaliações. **Modelo melhor**: o BERTimbau ganha do baseline nos mesmos dados, por cerca de 4 pontos no B2W e 10 no UMSAB.
- Acurácia de 75% no B2W, com três classes equilibradas (o acaso daria cerca de 33%).
- Na matriz de confusão, quase todos os erros envolvem o **neutro**: no B2W, 363 de 375. Elogio e reclamação quase nunca são trocados (12 casos).

## 5. Limitações e próximos passos (1 min)

- A classe neutra é a mais difícil (F1 de cerca de 0,64). No B2W, "nota 3 = neutro" é um rótulo ruidoso: há nota 3 com texto claramente positivo.
- Ironia, sarcasmo e opiniões mistas ("produto bom, entrega péssima") ainda erram.
- **Ainda não medimos o desempenho em comentários reais de pequenos negócios locais.** O B2W são avaliações de produtos, e o UMSAB são tweets sobre TV.
- Próximos passos: rotular comentários reais de negócios locais (com autorização), conversar com potenciais usuários e estudar análise por aspecto (produto × atendimento × entrega).

## 6. Perguntas prováveis

**Por que BERTimbau?** É um BERT pré-treinado em português brasileiro, aberto (MIT), com tamanho Base que cabe numa GPU de 4 GB para ajuste e roda na CPU para inferência. Era o candidato da proposta técnica. Nós mesmos fizemos o ajuste para três classes; não usamos um classificador pronto de terceiros.

**Por que não usar uma API de LLM?** Estava fora do escopo definido. Os textos dos clientes sairiam do computador (privacidade), haveria custo por comentário e dependência de internet, e as previsões não seriam reprodutíveis nem auditáveis com versão fixa. Um modelo local pequeno atende à tarefa e pode ser avaliado com rigor.

**Por que SQLite e não PostgreSQL?** É um MVP local para um usuário, sem servidor para instalar. O SQLite tem transações reais (a importação é atômica) e persiste entre reinícios. A camada de dados é pequena; migrar para PostgreSQL seria simples se houver vários usuários.

**Como vocês protegeram o conjunto de teste?** As divisões são disjuntas por texto normalizado, inclusive entre as duas bases. Hiperparâmetros fixos, sem busca. A época e o modelo foram escolhidos só pela validação, com a regra definida antes do teste. O teste foi rodado **uma vez**, e o script se recusa a rodar de novo. Os CSVs de demonstração nunca entram no treino nem nas métricas.

**Por que nota 3 = neutro?** O B2W não tem rótulo de sentimento, só a nota de 1 a 5. A nota 3 é a aproximação mais direta de "nem satisfeito nem insatisfeito", e as classes extremas (1–2 e 4–5) são bem separadas. Sabemos que é ruidosa e mostramos exemplos disso na análise de erros. Rotular uma amostra manualmente é o próximo passo.

**Quanto tempo leva?** Treinar o BERTimbau levou cerca de 20 min numa GTX 1050 Ti. Para usar, não precisa de GPU: na CPU, 1.000 comentários curtos levam cerca de 14 s, e uma frase leva milissegundos.

**Os dados pessoais dos avaliadores?** Do B2W, lemos só o texto e a nota; gênero, idade e estado são descartados ao carregar. Dados brutos e pesos do modelo não vão para o Git.
