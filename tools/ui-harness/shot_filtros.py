"""
Renderiza o harness dos filtros (tools/ui-harness/filtros.html) em várias larguras
usando Playwright, mede o estado de cada grupo (nº de linhas, título centralizado,
largura) e salva um screenshot por largura em tools/ui-harness/shots/.

Uso:
    python tools/ui-harness/shot_filtros.py

Não faz parte do app. Requer: pip install playwright && playwright install chromium.
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

AQUI = Path(__file__).resolve().parent
HARNESS_URL = (AQUI / "filtros.html").as_uri()
SAIDA = AQUI / "shots"

# larguras de viewport para inspecionar (foco na transição lado-a-lado -> empilhado e no mobile)
LARGURAS = [1640, 1536, 1440, 1366, 1280, 1200, 1100, 1000, 900, 820, 768, 600, 480, 414, 360]


def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    print(f"Harness: {HARNESS_URL}")
    print(f"Saída:   {SAIDA}\n")
    print(f"{'largura':>7} | {'divider':>7} | grupos (titulo: linhas, largura px, titulo-centralizado)")
    print("-" * 92)

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        for largura in LARGURAS:
            pagina = navegador.new_page(
                viewport={"width": largura, "height": 1000},
                device_scale_factor=2,
            )
            pagina.goto(HARNESS_URL, wait_until="networkidle")
            pagina.evaluate("document.fonts.ready")
            dados = pagina.evaluate("window.medirFiltros()")
            divider_visivel = pagina.evaluate(
                "getComputedStyle(document.querySelector('.filter-divider')).display !== 'none'"
            )

            resumo = "  ||  ".join(
                f"{g['titulo'][:18]}: {g['linhas']} linha(s), {g['larguraGrupo']}px, centr={g['tituloCentralizado']}"
                for g in dados
            )
            print(f"{largura:>7} | {str(divider_visivel):>7} | {resumo}")

            card = pagina.locator(".card")
            card.screenshot(path=str(SAIDA / f"filtros_{largura:04d}.png"))
            pagina.close()

        navegador.close()

    print(f"\nOK. {len(LARGURAS)} screenshots em {SAIDA}")


if __name__ == "__main__":
    main()
