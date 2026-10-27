import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools import polyalkemi_feed as m  # noqa: E402

CARD = ('<div class="x"><div class="AddProductImage"><a href="/add-north/anep14arg/e-pla-army-green" id="d4img_1">'
        '<img src="https://img/a.w240.png" class="d4"/></a></div><span class="InfoOverlay"><a href="/add-north/anep14arg/e-pla-army-green">'
        '<span class="AddHeader1">add:north E-PLA (1kg)</span><span class="AddHeader2">Army Green</span></a>'
        '<span class="product-desc-prod-num"><span>ANEP14ARG</span></span><div class="AddStockContainer"> '
        '<div class="DynamicStockTooltipContainer"> <span class="InStock">{stock}</span><span> på lager</span> </div> </div></div>')


def test_parse_list_og_lager():
    page = CARD.format(stock="20+") + CARD.replace("ANEP14ARG", "B2").replace("<span class=\"InStock\">{stock}</span><span> på lager</span>", "Ikke på lager")
    items = m.parse_list(page)
    assert [i["Varenummer"] for i in items] == ["ANEP14ARG", "B2"]
    assert items[0]["Lager"] == "20+" and items[0]["Farge/type"] == "Army Green"
    assert items[0]["Lenke"] == "https://polyalkemi.no/add-north/anep14arg/e-pla-army-green"
    assert items[1]["Lager"] == "Utsolgt"


def test_stock_text():
    assert m.stock_text("7 på lager") == "7"
    assert m.stock_text("Forventet til lager 13.11.2026") == "Snart 13.11.2026"
    assert m.stock_text("Ikke på lager") == "Utsolgt"


def test_parse_price():
    assert m.parse_price('<span class="PriceLabel" data-priceincvat="1 090,-" data-priceexvat="872,-">') == "1 090,-"
    assert m.parse_price("<html></html>") == ""


def test_pris_faller_tilbake_til_gammel():
    items = [{"Varenummer": "A", "Lenke": "u1"}, {"Varenummer": "B", "Lenke": "u2"}]

    def fake(url, retries=2, timeout=60):
        if url == "u1":
            return '<b data-priceincvat="209,-">'
        raise OSError("feil")

    stats = m.add_prices(items, {"B": "99,-"}, fetch_fn=fake, delay=0, budget_min=1)
    assert [i["pris"] for i in items] == ["209,-", "99,-"]
    assert stats["ny"] == 1 and stats["gammel"] == 1


def test_collect_bruker_hovedsiden_og_faller_tilbake():
    card = test_parse_list_og_lager.__globals__["CARD"]
    many = "".join(card.format(stock="5").replace("ANEP14ARG", f"V{i}") for i in range(m.MIN_ALL))
    calls = []

    def ok(url, **kw):
        calls.append(url)
        return many

    assert len(m.collect(ok)) == m.MIN_ALL and calls == [m.ALL_URL]
    calls.clear()

    def partial(url, **kw):
        calls.append(url)
        if url == m.ALL_URL:
            raise OSError("for stor")
        return card.format(stock="5").replace("ANEP14ARG", "X" + str(len(calls)))

    assert len(m.collect(partial)) == len(m.CATEGORIES) and len(calls) == 1 + len(m.CATEGORIES)


def test_minifisert_html_og_relativt_bilde():
    page = ('<div class=AddProductImage><a href=/a/b/c id=d4img_1><img class="d4"alt="x"src=/Media/Cache/Images/x.webp border=0></a></div>'
            '<span class=AddHeader1>Navn A</span><span class=AddHeader2>Rød</span>'
            '<span class=product-desc-prod-num><span>V1</span></span><div class=AddStockContainer><div class=DynamicStockTooltipContainer>'
            '<span class=InStock>6</span><span> på lager</span></div></div>')
    it = m.parse_list(page)[0]
    assert (it["Navn"], it["Farge/type"], it["Varenummer"], it["Lager"]) == ("Navn A", "Rød", "V1", "6")
    assert it["Bilde"] == "https://polyalkemi.no/Media/Cache/Images/x.webp" and it["Lenke"].endswith("/a/b/c")
