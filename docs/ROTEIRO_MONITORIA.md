# Roteiro para a monitoria de 29/10/2026

Duração sugerida: 3 a 5 minutos. Apresentar o que foi implementado e distinguir das próximas etapas.

## 1. Recorte do problema

O Opinare organiza comentários em português brasileiro para ajudar a entender a percepção expressa nos textos. O público proposto são pequenos negócios que não têm uma equipe dedicada a acompanhar opiniões. Essa utilidade ainda será verificada com potenciais usuários.

O primeiro MVP usa importação CSV, permitida pelos requisitos. A atualização em tempo real do pitch inicial foi adiada para preservar o prazo da disciplina.

## 2. Demonstração

1. Execute `iniciar.ps1` e abra `http://127.0.0.1:8000`.
2. Se a base estiver vazia, use **Explorar demonstração**. Se já houver dados, explique que eles foram salvos localmente.
3. Mostre os totais e o aviso de que os comentários de exemplo são fictícios. As classificações são calculadas pelo modelo.
4. Mostre a evolução temporal. Dois exemplos não têm data e são contabilizados separadamente do gráfico.
5. Filtre um sentimento e confira que cartões, gráfico e tabela mudam juntos.
6. Limpe os filtros e busque uma palavra presente nos comentários.
7. Abra **Importar CSV**, apresente as colunas e baixe o modelo CSV vazio para preenchimento. O sistema identifica arquivos e comentários duplicados.
8. Abra **Modelo e metodologia**, mostre F1 macro, acurácia, resultados por classe e matriz de confusão.

Para demonstrar uma nova importação, crie um CSV próprio com duas ou três frases diferentes dos exemplos. Não use dados pessoais. A classificação pode errar: discutir o erro faz parte da apresentação das limitações.

## 3. Evidência disponível

- Treinamento real com 1.839 textos do recorte português UMSAB.
- Validação em 323 textos, preservando a divisão oficial e removendo uma sobreposição.
- Baseline: F1 macro 57,8% e acurácia 57,6% na validação UMSAB.
- Modelo ativo: Transformer externo para português. Em uma amostra separada de 30 frases sintéticas novas, o baseline acertou 18 e o Transformer 29. É uma checagem funcional, sem promessa de acurácia em dados reais.
- A área de metodologia mostra essa distinção. O checkpoint pode ter visto dados relacionados ao UMSAB; uma comparação científica independente ainda precisa ser planejada.
- Os 870 textos do teste UMSAB não foram avaliados pelo projeto; sua independência para o checkpoint externo não está garantida.
- Comandos reproduzíveis, dependências fixadas, fonte versionada e hashes registrados.
- Os 30 comentários fictícios do painel não foram usados para treinar nem medir o classificador.

## 4. Pontos para alinhar com o professor

- Manter importação de CSV como entrada suficiente para o MVP.
- Confirmar SQLite na demonstração local, simplificando a proposta inicial de PostgreSQL.
- Confirmar o uso do Transformer externo e definir uma avaliação científica independente para a comparação final.
- Confirmar o recorte social e a forma de obter uma primeira devolutiva de usuários.
- Confirmar os marcos do documento: apresentação em 12/11 e P2 em 19/11. O documento descreve 29/10 como orientação para artigos.

## 5. Situação e próximos passos

O núcleo do software está implementado. A comparação funcional com Transformer foi implementada. A avaliação científica independente, a análise qualitativa de erros, as conversas com usuários e o artigo completo continuam pendentes. Não apresentar essas etapas como concluídas.

O registro detalhado de verificações desta implementação está em `docs/PROGRESSO.md`.
