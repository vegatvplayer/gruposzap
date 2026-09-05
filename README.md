# gruposzap

Um site que se atualiza sozinho todo dia com links de grupos públicos de
WhatsApp, separados por categoria e com botão de copiar tudo já formatado.

**O site:** https://vegatvplayer.github.io/gruposzap/

Abre no celular também. Não precisa instalar nada para usar.

## Como funciona

Todo dia de manhã o GitHub roda o coletor sozinho: ele varre sites de
divulgação de grupos, pega os links de convite, tira os repetidos e regrava a
página. Você só abre o site e copia.

Se quiser rodar na hora, sem esperar o horário: aba **Actions** → **Coletar
links** → botão **Run workflow**. Em uns 2 minutos a página está nova.

## Ligando o site (só na primeira vez)

1. **Settings → Actions → General**, lá embaixo em *Workflow permissions*,
   marque **Read and write permissions** e salve.
2. **Settings → Pages**, em *Source* escolha **Deploy from a branch**, e logo
   abaixo escolha a branch `main` e a pasta **`/docs`**. Salve.
3. **Actions → Coletar links → Run workflow** para gerar a primeira lista.

## No site

- filtro por categoria e busca por nome
- caixinha de seleção em cada grupo
- **Copiar selecionados** / **Copiar todos da tela**
- botão **"já entrei"**, que apaga o grupo da sua vista e fica salvo naquele
  aparelho — assim você não repete grupo de um número para outro

O texto copiado sai assim:

```
1 - Nome do grupo: STICKERS 2026
link: https://chat.whatsapp.com/XXXXXXXXXXXXXXXXXXXXXX

2 - Nome do grupo: Papo e Amizade
link: https://chat.whatsapp.com/YYYYYYYYYYYYYYYYYYYYYY
```

Tem também o `grupos.csv` na pasta `docs`, com a mesma lista para abrir no Excel.

## Rodando no seu PC (opcional)

Dá para usar sem depender do site:

1. Instale o [Python](https://www.python.org/downloads/) marcando a caixa
   **"Add Python to PATH"**.
2. Baixe o repositório (**Code → Download ZIP**) e descompacte.
3. Clique duas vezes em `EXECUTAR.bat`.

Aí ele gera um `painel.html` na sua pasta e abre sozinho. Nessa forma ele guarda
um `historico.json` e, nas próximas vezes, só traz grupo que você ainda não viu.

## Configuração

Abra `coletor_grupos.py` num editor de texto. Tudo que dá para mexer está no
topo, no bloco `CONFIGURACAO`:

| Opção | O que faz |
|---|---|
| `LIMITE_POR_CATEGORIA` | quantos grupos buscar por categoria em cada site (padrão 120) |
| `DIAS_MAXIMOS` | só aceita grupo publicado nos últimos X dias (padrão 150) |
| `CATEGORIAS_ATIVAS` | ligue/desligue categorias com `True` / `False` |
| `PARALELO` | velocidade. Se der erro de conexão, baixe para 3 |
| `CHECAR_LINKS` | conferir se a página do convite responde antes de salvar |
| `FONTES` | sites e IDs de categoria de onde buscar |

Depois de editar e dar `commit`, o site já sai com a mudança na próxima coleta.

### Adicionar uma categoria nova

Os sites usados rodam WordPress, então dá para descobrir o ID de qualquer
categoria abrindo isto no navegador:

```
https://linkdegrupo.com.br/wp-json/wp/v2/categories?per_page=100&_fields=id,slug,count
```

Pegue o `id` da categoria e acrescente em `FONTES`.

### Mudar o horário da coleta

Em `.github/workflows/coletar.yml`, na linha do `cron`. O horário é em UTC —
Brasília é 3 horas a menos. `0 9 * * *` = 06:00 da manhã aqui.

## Limitações conhecidas

- **Não dá para saber se o convite ainda está válido.** O WhatsApp parou de
  informar isso fora do aplicativo: a página de convite responde igual para
  grupo ativo e para link já revogado. O programa compensa pegando só grupos
  publicados recentemente e descartando o que já vem quebrado no HTTP, mas link
  morto ainda aparece de vez em quando.
- Alguns sites de divulgação escondem o link atrás de verificação anti-robô
  (Cloudflare Turnstile). Esses ficaram de fora de propósito.
- Se um dos sites mudar de estrutura, a coleta dele para até os IDs em `FONTES`
  serem atualizados.

## Fontes usadas

- [linkdegrupo.com.br](https://linkdegrupo.com.br/)
- [grupodewhats.app](https://grupodewhats.app/)

Ambos publicam os links abertamente e liberam acesso automatizado no
`robots.txt`. O programa só lê páginas públicas — não faz login, não posta nada
e não entra em grupo nenhum por você.

## Licença

MIT — veja [LICENSE](LICENSE).
