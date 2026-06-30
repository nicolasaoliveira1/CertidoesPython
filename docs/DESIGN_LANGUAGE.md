# Design Language — Zelo (guia operacional)

> Regras práticas a seguir **sempre que mexer em UI/UX** deste sistema.
> O *porquê* (brief, conceito, faseamento do rebrand) vive em [`IDENTIDADE_ZELO.md`](IDENTIDADE_ZELO.md).
> A **fonte de verdade dos valores** é o bloco `:root` de [`app/static/css/style.css`](../app/static/css/style.css);
> este doc resume as decisões e diz como aplicá-las.

## Princípio

**"A única cor é o status."** Todo o chrome é grafite sobre papel (monocromático). A única
cromaticidade da tela é o indicador de validade da certidão (válida / a vencer / vencida / pendente /
sem data). Não introduza cor decorativa — cor carrega significado de status, nada mais.

## Regra de ouro das cores

- **Nunca** hardcode hex em template/CSS novo. Use os tokens `--zelo-*` ou as variáveis Bootstrap
  já mapeadas (`--bs-primary`, `--bs-primary-rgb`, `--bs-secondary-color`, `--bs-tertiary-bg`, etc.).
- Tudo tem valor para **light e dark**; ao criar um componente, garanta que ele lê de tokens (assim
  acompanha o tema sozinho). Revise nos dois temas antes de fechar.

### Tokens de chrome (monocromático)
`--zelo-ink` (texto forte/ação) · `--zelo-graphite` (primário) · `--zelo-slate` (muted) ·
`--zelo-line` (bordas) · `--zelo-mist` (superfícies) · `--zelo-paper` (fundo).
`--bs-primary` está mapeado para grafite — **botões/links não são azuis**.

### Tokens de status (a única cor)
`--zelo-ok` (válida) · `--zelo-warn` (a vencer) · `--zelo-danger` (vencida) · `--zelo-pend`
(pendente — tom tijolo próprio, provável débito) · `--zelo-muted` (sem data). Cada um tem a variante
`*-soft` (banda de fundo suave). Use-os só para comunicar validade.

## Tipografia — superfamília IBM Plex (3 papéis)

| Papel | Token | Onde |
|---|---|---|
| Display (serif) | `--zelo-font-display` | wordmark, títulos de página, cabeçalhos |
| Corpo/UI (sans) | `--zelo-font-body` | labels, botões, navegação, texto geral |
| Dados (mono) | `--zelo-font-mono` | CNPJ, datas, números, contadores |

Não use Inter/Roboto/Arial soltos. Pesos: Serif 500/600 · Sans 400/500/600 · Mono 400/500.

## Botões — hierarquia (primário / secundário / terciário)

Em **rodapés de modal/diálogo** e blocos de ação, siga esta escala. A leitura é
**sólido > tint > transparente**: cada nível abaixa um degrau de preenchimento.

| Nível | Quando usar | Classe |
|---|---|---|
| **Primário** | a ação principal/recomendada | `btn btn-primary` (ou `btn-success`/`btn-danger` quando a semântica exige) |
| **Secundário** | ação alternativa positiva | `btn btn-soft-primary` |
| **Terciário** | dispensar / cancelar / "não" | `btn btn-ghost` |

- O CTA primário fica **à direita** no rodapé (último na ordem do DOM).
- `btn-soft-primary` e `btn-ghost` são classes próprias (em `style.css`, perto de `.batch-modal-footer`)
  com `:hover`/`:focus-visible`/`:active`. **Prefira-as a `btn-outline-*`** em rodapés: o outline fica
  "vazio" e só ganha cor no hover, o que lê como desabilitado.
- **Ações destrutivas** (remover, marcar pendente) ficam **fora da escala**: use a cor `danger`
  (`btn-danger` / `btn-outline-danger`) — vermelho carrega significado.

### Exceções (não force o ghost)
- **Nav solta de página** (Voltar/Limpar sozinhos no topo, sem primário ao lado): mantenha
  `btn-outline-secondary`. Solto numa página clara, o ghost (transparente) parece texto e perde a
  afordância de "clicável". O ghost brilha em **rodapé de modal**, não solto.
- **Botões de ícone em linha de tabela** (`btn-sm btn-outline-* border-0`) e **controles de overlay**
  (Pausar/Retomar/Parar sobre fundo escuro): contextos próprios, deixe como estão.

## Modais

- Sempre `×` (`btn-close`) no header — é o dispensar universal.
- **Modal de decisão** (2+ ações positivas): inclua o terciário "Cancelar" (`btn-ghost`). Com
  `data-bs-backdrop="static"`, sem ele a única saída é o `×` minúsculo. Ordem:
  `Cancelar (ghost) · ação secundária (soft) · ação primária (sólido)`.
- **Modal de confirmação** com negativa nomeada ("Não, manter como está" / "Sim, ..."): o botão da
  esquerda já é o "não" → terciário (ghost); o da direita carrega a semântica (success/danger).
- **Modal de puro aviso/resumo**: só `OK`/`Entendi` (primário). **Não** adicione Cancelar.

## Forma

- **Raio:** cards/modais ~`0.5–0.85rem`; chips/badges/pílulas `999px`. (Ainda não tokenizado;
  siga os valores vizinhos do componente.)
- **Sombra:** sutil e fria (ex. `0 1px 2px rgba(16,18,28,.06)` / `0 10px 24px rgba(0,0,0,.09)`).
  Nada de sombra pesada.
- **Foco:** sempre visível — anel `box-shadow: 0 0 0 .25rem rgba(var(--bs-primary-rgb), .3)`
  (ou `--bs-secondary-rgb` para terciário). Não remova outline sem repor um foco equivalente.

## Copy (voz)

- O sistema se chama **Zelo** (nunca "Controle de Certidões Fiscais" em texto novo).
- Botões em **voz ativa de ação**: "Emitir" → toast "Emitida". Curto e direto.

## Não faça

- ❌ Hex hardcoded / cores fora dos tokens · ❌ cor decorativa (cor ≠ status) · ❌ `btn-outline-*`
  como secundário em rodapé de modal · ❌ remover Cancelar de modal de decisão · ❌ Cancelar em modal
  de aviso · ❌ fontes default (Inter/Roboto/Arial) · ❌ sombra pesada · ❌ remover foco visível ·
  ❌ entregar mudança testada só num tema.
