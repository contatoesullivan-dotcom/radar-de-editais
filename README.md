# Radar de Editais

Aplicativo web instalável (PWA) para acompanhar oportunidades de serviços de comunicação, seleções profissionais e mestrados em Comunicação.

**Acesse:** https://contatoesullivan-dotcom.github.io/radar-de-editais/

## Fontes

Em 16/11/2026 foram cadastradas **16 fontes oficiais**; **13 com coleta programada ou experimental** e 3 referências com integração pendente.

| Eixo | Fontes |
| --- | --- |
| Ceará: serviços, pesquisa e cultura | Agropolos, FUNCAP, Mapa Cultural do Ceará, TCE Ceará (licitações municipais) |
| Ceará: seleções | IFCE |
| Comunicação: mestrados | PPGCOM/UFC, UFJF, UFMA, UFPE, UFMG, Póscom/UFBA e PPGEM/UFRN |
| API de contratações | PNCP — consulta experimental de pregões, concorrências e dispensas no Ceará |
| Em preparação | Compras.gov.br, licitações da Prefeitura de Fortaleza e UFC/PROGEP |

As fontes em preparação são exibidas no aplicativo para consulta manual, mas **não** são lidas pelo coletor. As fontes ativas podem retornar `falhou` ou `atenção` se houver bloqueio, página dinâmica ou mudança de layout. **Estar cadastrada não é garantia de extração funcional.**

### Como o coletor funciona

- `scripts/monitor.py` analisa links e títulos em HTML das fontes cadastradas.
- `scripts/pncp.py` consulta a API oficial de propostas do PNCP, limitada a três modalidades e às primeiras páginas de resultados do Ceará; **não é uma busca nacional exaustiva**.
- `scripts/test_monitor.py` testa a lógica de extração com exemplos controlados; **esses testes não comprovam acesso real às instituições**.
- `data/opportunities.json` reúne as oportunidades, com identificação pela URL oficial.
- `data/monitor_status.json` distingue fontes verificadas, fontes sem links reconhecidos e fontes com falha de acesso.

**Importante:** fora da API PNCP, o coletor encontra títulos e links. Ele **não lê automaticamente o inteiro teor de todos os PDFs** e não confirma remuneração, requisitos ou prazo. O sistema não deve chamar um edital de aberto quando essa condição não estiver comprovada.

## Atualização automática

O fluxo [Atualizar Radar de Editais](https://github.com/contatoesullivan-dotcom/radar-de-editais/actions/workflows/monitorar.yml) está configurado para executar às **8h e 19h, horário de Fortaleza** (11h e 22h UTC), e também ao atualizar os scripts e a lista de fontes. O GitHub pode atrasar execuções agendadas, que não são instantâneas.

Após a coleta, o bot salva o JSON no repositório. O aplicativo tenta buscar esses JSONs do `raw.githubusercontent.com` a cada abertura, com fallback para arquivos servidos pelo GitHub Pages. Isso é importante porque commits feitos com `GITHUB_TOKEN` não provocam automaticamente nova publicação do GitHub Pages.

**Primeiro teste:** abra o fluxo no link acima e selecione `Run workflow` (Executar fluxo). Confira os passos de testes, consulta e gravação dos dados; depois visite a aba **Fontes monitoradas** no aplicativo.

Para testar a extração sem consultar sites:

```bash
python -m unittest discover -s scripts -p 'test_*.py' -v
```

Para executar uma coleta local (requer internet):

```bash
python scripts/monitor.py
```

## Instalação no iPhone

Abra o link do aplicativo no Safari, toque em **Compartilhar** e escolha **Adicionar à Tela de Início**. No computador, quando o navegador permitir, use a opção **Instalar**.

## Notificações

**Ainda não implementadas.** A tela de alertas armazena apenas preferências locais e não envia e-mails ou push. Não cadastre senhas e tokens no repositório público. A próxima etapa é conectar um provedor de e-mail ou push e testar entregas.

## Limitações e transparência

- Dados de referência iniciais não são inscrições abertas verificadas.
- Publicações antigas podem aparecer na primeira varredura; confira datas no documento oficial.
- O status de cada fonte é observado somente depois de uma coleta real.
- Os favoritos ficam salvos apenas no dispositivo.
- A busca do PNCP cobre o Ceará no primeiro recorte experimental; uma consulta exaustiva nacional exige paginação e filtros adicionais.
- O aplicativo está em desenvolvimento; use os links oficiais antes de tomar decisões de inscrição.
