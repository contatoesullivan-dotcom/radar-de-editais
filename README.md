# Radar de Editais

Aplicativo web instalável (PWA) para encontrar publicações do Instituto Agropolos e PPGCOM/UFC, acompanhar oportunidades de comunicação, processos seletivos e mestrados.

## Publicação no GitHub Pages

1. Abra [Settings → Pages](https://github.com/contatoesullivan-dotcom/radar-de-editais/settings/pages).
2. Em **Build and deployment**, selecione **Deploy from a branch**.
3. Em **Branch**, selecione **main** e **/(root)**; clique em **Save**.
4. Aguarde o GitHub indicar **Your site is live at...**. O endereço previsto, **somente depois de a publicação ser concluída**, é https://contatoesullivan-dotcom.github.io/radar-de-editais/.
5. No Safari do iPhone, abra o endereço e use **Compartilhar → Adicionar à Tela de Início**.

## Coleta de editais

O fluxo [Atualizar Radar de Editais](https://github.com/contatoesullivan-dotcom/radar-de-editais/actions) executa verificações às 8h e 19h, horário de Fortaleza (11h e 22h UTC). É possível iniciá-lo manualmente em **Actions → Atualizar Radar de Editais → Run workflow**.

**Importante:** a coleta não foi validada com as páginas oficiais em produção. Ela identifica links e títulos, **não confirma** inscrição aberta, remuneração, documentos, requisitos nem datas. Erros de acesso ou mudanças do layout são registrados como **falha** na aba Fontes. Dados iniciais são referências, não disponibilidade confirmada.

Não há envio de e-mail ou push configurado nesta versão. Favoritos e preferências ficam somente no dispositivo e não sincronizam entre aparelhos. Não armazene segredos ou dados pessoais no repositório público.

## Estrutura

- `index.html`: interface com busca, filtros, favoritos e detalhes
- `manifest.webmanifest`, `service-worker.js`, `assets/icon.svg`: instalação PWA e cache
- `config/sources.json`: fontes públicas monitoradas
- `scripts/monitor.py`: verificação conservadora das fontes
- `data/`: registros iniciais e situação da coleta
- `.github/workflows/monitorar.yml`: agendamento automático

### Limitações

O aplicativo é uma **primeira versão em implantação**. A coleta deve ser auditada depois de rodar no GitHub. Não consulte a interface para decidir sobre inscrições sem abrir a página oficial.
