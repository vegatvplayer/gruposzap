# Coletor de links de grupos de WhatsApp

Coleta automaticamente links de convite de grupos públicos de WhatsApp a partir
de sites de divulgação, remove repetidos e gera um painel HTML com botão de
copiar tudo já formatado.

## Para que serve

Em vez de ficar caçando link de grupo um por um no Google, você roda o programa
e recebe uma lista pronta, separada por categoria, com botão de copiar.

## Como usar

1. Instale o [Python](https://www.python.org/downloads/) marcando a caixa
   **"Add Python to PATH"**.
2. Baixe este repositório (botão verde **Code → Download ZIP**) e descompacte.
3. Clique duas vezes em `EXECUTAR.bat`.
4. O `painel.html` abre sozinho no navegador quando terminar.

No Linux ou macOS:

```bash
pip install requests
python coletor_grupos.py
```

## O painel

- filtro por categoria e busca por nome
- caixinha de seleção em cada grupo
- **Copiar selecionados** / **Copiar todos da tela**
- botão **"já entrei"** em cada grupo, para não repetir depois

O texto copiado sai assim:

```
1 - Nome do grupo: STICKERS 2026
link: https://chat.whatsapp.com/XXXXXXXXXXXXXXXXXXXXXX

2 - Nome do grupo: Papo e Amizade
link: https://chat.whatsapp.com/YYYYYYYYYYYYYYYYYYYYYY
```

## Configuração

Abra `coletor_grupos.py` num editor de texto. Tudo que dá para mexer está no
topo do arquivo, no bloco `CONFIGURACAO`:

| Opção | O que faz |
|---|---|
| `LIMITE_POR_CATEGORIA` | quantos grupos buscar por categoria em cada site (padrão 120) |
| `DIAS_MAXIMOS` | só aceita grupo publicado nos últimos X dias (padrão 150) |
| `CATEGORIAS_ATIVAS` | ligue/desligue categorias com `True` / `False` |
| `PARALELO` | velocidade. Se der erro de conexão, baixe para 3 |
| `CHECAR_LINKS` | conferir se a página do convite responde antes de salvar |
| `FONTES` | sites e IDs de categoria de onde buscar |

### Adicionar uma categoria nova

Os sites usados rodam WordPress, então dá para descobrir o ID de qualquer
categoria abrindo no navegador:

```
https://linkdegrupo.com.br/wp-json/wp/v2/categories?per_page=100&_fields=id,slug,count
```

Pegue o `id` da categoria que quiser e acrescente em `FONTES`.

## Arquivos que o programa cria

| Arquivo | O que é |
|---|---|
| `painel.html` | o painel com os botões de copiar |
| `grupos.csv` | a mesma lista em planilha, abre no Excel |
| `historico.json` | memória dos links já coletados — na próxima rodada os mesmos grupos não se repetem. Apague para começar do zero |

Esses três estão no `.gitignore` e não vão para o repositório.

## Limitações conhecidas

- **Não dá para saber se o convite ainda está válido.** O WhatsApp parou de
  informar isso fora do aplicativo: a página de convite responde igual para
  grupo ativo e para link já revogado. O programa compensa pegando só grupos
  publicados recentemente e descartando o que já vem quebrado no HTTP, mas link
  morto ainda aparece de vez em quando.
- Alguns sites de divulgação escondem o link atrás de verificação anti-robô
  (Cloudflare Turnstile). Esses ficaram de fora de propósito.
- Se um dos sites mudar de estrutura, a coleta daquele site para de funcionar
  até os IDs em `FONTES` serem atualizados.

## Fontes usadas

- [linkdegrupo.com.br](https://linkdegrupo.com.br/)
- [grupodewhats.app](https://grupodewhats.app/)

Ambos publicam os links abertamente e permitem acesso automatizado no
`robots.txt`. O programa só lê páginas públicas — não faz login, não posta nada
e não entra em grupo nenhum por você.

## Licença

MIT — veja [LICENSE](LICENSE).
