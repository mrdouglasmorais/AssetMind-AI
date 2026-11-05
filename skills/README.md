# Skills de execução

Uma skill é uma competência. O orquestrador é código: classifica o ativo, chama o especialista da classe e não gasta token para rotear. O modelo só narra um resultado que o motor já validou.

São oito skills, nesta ordem de dependência:

1. `evidence-review` e o contrato em `contracts/report.schema.json`.
2. `orchestration` e `token-balance`.
3. `equity-analysis`, `crypto-analysis` e `real-estate-analysis`.
4. `scenario-analysis`.
5. `market-news`.

## O que o motor faz hoje

- Retorno composto, volatilidade, drawdown, percentis e buy-and-hold dentro da amostra recebida.
- Ação: fechamento, faixa de 52 semanas e estatísticas atuais (P/L, P/VP, LPA, dividend yield) quando o provedor as envia.
- Cripto: preço, valor de mercado e volume no CoinGecko. A volatilidade anual usa 365 períodos.
- FII: preço da cota e, quando existem, fatos rotulados. Vacância só em fundo de tijolo. O informe mensal da CVM ao vivo não é lido.
- Cenário: preço de referência vezes `1 + choque`. O padrão é −15%, 0% e +15%, com rótulo `illustrative_assumption`. Não há probabilidade.
- Notícia: até 3 manchetes do Google News nos últimos 7 dias. Título, fonte, data e link, em cards. A imagem entra só quando o item do feed a declara. O texto da matéria não entra.
- Saldo: tokens estimados e tokens reais em campos separados. Notícia é chamada de provedor. Embedding da sessão, quando o Groq está ligado, é uma linha `embedding`.

## Lentes de leitura

A skill pode usar o nome de um analista como pergunta sobre um campo que já existe. O nome não vira número, alvo ou recomendação.

| Lente | Onde entra | O que a ficha permite |
| --- | --- | --- |
| Luiz Barsi Filho | Ação e FII | Dividend yield ou distribuição realizada, com o período. A amostra de cerca de 3 meses não é o horizonte longo dele. |
| Décio Bazin | Ação | Olhar o yield realizado. Sem corte configurado, o yield não é nota de barato ou caro. |
| Warren Buffett e Benjamin Graham | Ação | Drawdown da amostra e múltiplos atuais. Valor intrínseco e margem de segurança não são calculados. |
| Ficha de FII (Baroni e a pesquisa de fundos) | FII | DY e P/VP quando existem; vacância só no tijolo. Os três juntos não são regra de compra. |
| Lyn Alden | Cripto | Série de preço, retorno, volatilidade em 365, drawdown, valor de mercado e volume. A manchete não é fator. |
| Andreas M. Antonopoulos | Cripto | Explicar a série e não instruir operação. Custódia fica fora da ferramenta. |

Willy Woo, Coin Metrics, stock-to-flow e preço-teto ficam citados só como métodos que esta ferramenta não executa.

## O que a skill não pode completar

DCF, GARCH, Monte Carlo, modelo multifatorial, backtest walk-forward, métrica on-chain, derivativo e alvo de preço não são calculados. A narrativa não inventa o número que falta. Qualidade do dado e chance de acerto de uma projeção são coisas diferentes; a segunda não é emitida.

O relatório publicado obedece a `contracts/report.schema.json`.
