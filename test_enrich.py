import pytest

from src.enrich import enrich, parse_weight, parse_diameter


def e(name, **kw):
    return enrich(name, **kw)


def test_silk_color_brand_weight():
    r = e("Bambu Lab PLA Silk 1 kg Baby Blue")
    assert (r.brand, r.material, r.finish, r.color, r.weight_kg) == ("Bambu Lab", "PLA", "Silk", "Blå", 1.0)


def test_norwegian_compound_matt_black():
    r = e("Addnorth Textura-filament for 3D-skriver 1,75 mm Mattsvart")
    assert (r.brand, r.finish, r.color, r.diameter_mm) == ("Addnorth", "Matt", "Svart", 1.75)


def test_glow_in_the_dark():
    r = e("Addnorth E-PLA-filament for 3D-skriver 1,75 mm Dark Green selvlysende")
    assert (r.finish, r.color, r.material) == ("Selvlysende", "Grønn", "PLA")


def test_glitter_and_marble():
    assert e("Addnorth E-PLA 1,75 mm Glitz Sapphire").finish == "Glitter"
    assert e("Addnorth E-PLA 1,75 mm Marble").finish == "Marmor"


def test_grams_with_thousand_separator():
    assert parse_weight("Addnorth E-PLA filament 1,75 mm – 1 000 g Gul") == 1.0
    assert parse_weight("Primaselect PETG 1.75mm 750 g") == 0.75
    assert parse_weight("PLA 3D-filament, 1,75 mm, 0,6 kg") == 0.6
    assert parse_diameter("PLA 1,75 mm") == 1.75
    assert parse_diameter("PLA Tough 2.85mm") == 2.85


def test_materials():
    assert e("Copymaster3D PETG 1KG").material == "PETG"
    assert e("Polymaker PolyFlex TPU-95A").material == "TPU"
    assert e("Bambu Lab ABS 1 kg").material == "ABS"
    assert e("ABS 3D-filament Universal 1,75 mm 1 kg").ui_material == "ABS"
    assert e("Primaselect Nylonpower Glass Fibre 1,75mm 500g").ui_material == "PA"
    assert e("Creality CR-PLA Carbon 1,75 mm 1 kg").ui_material == "PLA"


def test_color_hint_wins_over_name():
    r = e("Bambu Lab PLA Basic 1 kg", color_hint="Rød")
    assert r.color == "Rød"


def test_short_norwegian_color_words():
    assert e("Addnorth E-PLA 1,75 mm Lysegrå").color == "Grå"
    assert e("Addnorth E-PLA 1,75 mm 1000 g Rød").color == "Rød"
    assert e("Addnorth E-PLA 1,75 mm Gul").color == "Gul"
    assert e("Addnorth PLA Premium Silk 1,75 mm Gull").color == "Gull"


def test_multicolor():
    assert e("Azurefilm PLA Silk Rainbow Amber").color == "Flerfarget"
    assert e("Bambu Lab PLA Silk Multi 1kg Aurora Purple").color == "Flerfarget"


@pytest.mark.parametrize("name", [
    "Filamentholder til 3D-skriver",
    "FlashForge Adventurer 3, 3D-skriver",
    "3Doodler 2.0, 3D-penn",
])
def test_rejects_non_filament(name):
    assert e(name).is_filament is False


@pytest.mark.parametrize("name", [
    "PLA 3D-filament, 1,75 mm, 0,6 kg",
    "Elegoo TPU 95A 1 kg",
    "Azurefilm PLA Silk Silk Lila",
    "Polyalkemi PLA-HS Paper White",
])
def test_accepts_filament(name):
    assert e(name).is_filament is True


def test_same_product_in_two_stores_gets_same_key():
    a = e("Bambu Lab PLA Silk 1 kg Baby Blue")
    b = e("Bambu Lab PLA Silk 1kg - Baby Blue 1.75 mm")
    assert a.key == b.key


def test_different_color_or_weight_gives_different_key():
    base = e("Bambu Lab PLA Basic 1 kg Bambu Green")
    assert base.key != e("Bambu Lab PLA Basic 1 kg Black").key
    assert base.key != e("Bambu Lab PLA Basic 0,5 kg Bambu Green").key


def test_olive_beige_transparent():
    assert e("Bambu Lab ABS 1kg - Olive").color == "Grønn"
    assert e("Bambu Lab PETG Basic - Dark Beige").color == "Beige"
    assert e("Bambu Lab PC - Transparent").color == "Gjennomsiktig"


def test_new_finishes_and_colors():
    assert e("eSUN ePLA Metal - 1.75mm- 1kg Antique Brass").finish == "Metall"
    assert e("eSUN ePLA Metal - 1.75mm- 1kg Antique Brass").color == "Gull"
    assert e("eSUN PLA Rock 1kg - Granite").finish == "Stein"
    assert e("Bambu Lab PLA Wood 1kg - Rosewood").finish == "Tre"
    assert e("Bambu Lab PLA Translucent 1kg - Lavender").finish == "Gjennomsiktig"
    assert e("Bambu Lab PLA Translucent 1kg - Lavender").color == "Lilla"
    assert e("eSUN PLA-Chameleon 1.75mm 1kg - Polaris").finish == "Fargeskift"
    assert e("Bambu Lab PLA Galaxy 1kg - Nebulae").finish == "Glitter"
    assert e("Elegoo PLA Refill 1kg - Cyan").color == "Turkis"
    assert e("eSUN PLA+ 4kg - CMYK").color == "Flerfarget"
    assert e("Bambu Lab PLA Matte REFILL 1kg - Dark Chocolate").color == "Brun"


def test_material_variants_and_packs():
    assert e("eSUN ePLA Metal - 1.75mm- 1kg Gold").ui_material == "PLA"
    assert e("eSUN ePLA-CF 1.75mm - 1kg - Black").ui_material == "PLA"
    assert e("colorFabb Varioshore TPU (700g)").weight_kg == 0.7
    assert e("EasyPrint PLA Value Pack 1.75mm 4x500g 4-farger").weight_kg == 2.0
    assert e("Bambu Lab Support for PLA/PETG").ui_material == "Support"


def test_more_color_words():
    assert e("Azurefilm PETG Original Skin Cappuccino").color in ("Brun", "Beige")
    assert e("Azurefilm PLA Matte HS Bordeaux").color == "Rød"
    assert e("Azurefilm PLA Silk Silk Rose").color == "Rosa"
    assert e("Bambu Lab PLA Wood 1kg - Rosewood").color == "Brun"
    assert e("Fiberlogy ABS Onyx").color == "Svart"
    assert e("FilamentPM PLA+ WoodJet Natur").color == "Naturell"
    assert e("Azurefilm Super Pack HS PETG (10 ruller) MIX").color == "Flerfarget"


def test_expanded_materials():
    cases = {
        "Intam ASA 1,75mm 1kg": "ASA",
        "Prusament ASA": "ASA",
        "Bambu Lab ABS 1 kg": "ABS",
        "FormFast industrial PCTG": "PCTG",
        "Esun PTCG 1.75mm 1kg": "PCTG",
        "addnorth Adura Nylon 1kg Black": "PA",
        "Prusament PA11 Carbon Fiber Black 800g": "PA",
        "Bambu Lab PAHT-CF Carbon Fiber Nylon 500g": "PAHT",
        "FORMFAST LUVOCOM 3F PEEK 9581 NT 500gr": "PEEK",
        "INTAM PEI 1010 1,75mm 1kg": "PEI",
        "INTAM PPS BLACK 1,75mm 1kg": "PPS",
        "INTAM PPA-CF 1,75mm 1kg": "PPA",
        "Polymaker Polymax Tough PC": "PC",
        "Polymaker Fiberon PET-CF17 500g": "PET",
        "INTAM HIPS 1,75mm 1kg": "HIPS",
        "PRIMASELECT BVOH 750g 1,75mm": "BVOH",
        "Esun PVA 1.75mm 500g": "PVA",
        "Polymaker PolyFlex TPU-95A": "TPU",
        "Esun PP 1.75mm 500g": "PP",
        "Bambu Lab PETG HF 1kg": "PETG",
        "Bambu Lab Support for PA/PET 500g": "Support",
    }
    for name, mat in cases.items():
        assert e(name).ui_material == mat, (name, e(name).ui_material)


def test_additives():
    assert e("addnorth PETG Flame Retardant V0 1kg").additive == "Flammehemmende"
    assert e("addnorth ESD PETG Black 750g").additive == "ESD"
    assert e("Bambu Lab PAHT-CF 500g").additive == "Karbon"
    assert e("Polymaker HT-PLA GF").additive == "Glassfiber"
    assert e("Bambu Lab PLA Basic 1 kg").additive is None


def test_material_list():
    cases = {
        "Spectrum PA6 Low Warp CF15S (1000g) Black": "PA6",
        "Nordic Filament PA12-CF20 Black": "PA12",
        "Polymaker Fiberon PA612-CF15 (1kg)": "PA612",
        "Polymaker PolyMide CoPA Black (750g)": "CoPA",
        "Fiberlogy CPE HT Black": "CPE",
        "addnorth HT-PLA Pro Matte 1kg": "HT-PLA",
        "eSUN PLA+ 1kg": "PLA+",
        "eSUN PLA Basic 1kg": "PLA",
        "Fiberlogy ASA+ Black": "ASA+",
        "Esun ABS+ 1kg": "ABS+",
        "Eastar PC-ABS 1kg": "PC-ABS",
        "Polymaker PETG+ 1kg": "PETG+",
        "Esun TPE 1kg": "TPE",
        "Sunlu TPR 1kg": "TPR",
        "Esun PMMA 500g": "PMMA",
        "Esun PCL 500g": "PCL",
        "Colorfabb PIPG 750g": "PIPG",
        "Mabs 1kg": "MABS",
    }
    for name, mat in cases.items():
        assert e(name).ui_material == mat, (name, e(name).ui_material)


def test_weight_after_number():
    assert parse_weight("Polymaker Fiberon PA6-CF20 500g Polymaker Industrial") == 0.5
    assert parse_weight("Addnorth E-PLA 1 000 g") == 1.0
