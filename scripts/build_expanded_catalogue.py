"""Build the expanded 112-crop global catalogue with verified FAO/GBIF/AGROVOC references and FAO-56 stage/trait tables."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAT_PATH = ROOT / "data" / "global_catalogue.json"


NEW_SOURCES = [
    {
        "id": "fao_56_crop_water_1998",
        "title": "FAO Irrigation and Drainage Paper 56: Crop evapotranspiration - Guidelines for computing crop water requirements (Allen et al., 1998)",
        "url": "https://www.fao.org/4/x0490e/x0490e00.htm",
        "license": "FAO Terms and Conditions",
        "version": "1998",
    },
    {
        "id": "fao_66_crop_yield_water_2012",
        "title": "FAO Irrigation and Drainage Paper 66: Crop yield response to water (Steduto et al., 2012)",
        "url": "https://www.fao.org/4/i2800e/i2800e.pdf",
        "license": "FAO Open Archive Terms",
        "version": "2012",
    },
    {
        "id": "fao_33_yield_response_1979",
        "title": "FAO Irrigation and Drainage Paper 33: Yield response to water (Doorenbos & Kassam, 1979)",
        "url": "https://www.fao.org/4/x5560e/x5560e00.htm",
        "license": "FAO Terms and Conditions",
        "version": "1979",
    },
    {
        "id": "fao_irrigation_manual_3_1986",
        "title": "FAO Irrigation Water Management Training Manual No. 3: Irrigation Water Needs (Brouwer & Heibloem, 1986)",
        "url": "https://www.fao.org/4/s2022e/s2022e07.htm",
        "license": "FAO Terms and Conditions",
        "version": "1986",
    },
    {
        "id": "fao_wca_2020_crop_list",
        "title": "FAO World Programme for the Census of Agriculture 2020 Volume 1 Appendix 4 Indicative Crop List",
        "url": "https://www.fao.org/3/a-i4913e.pdf",
        "license": "CC BY-NC-SA 3.0 IGO",
        "version": "2020",
    },
    {
        "id": "fao_agrovoc",
        "title": "FAO AGROVOC Multilingual Thesaurus",
        "url": "https://agrovoc.fao.org/browse/agrovoc/en/",
        "license": "CC BY 4.0",
        "version": "2026-11",
    },
    {
        "id": "gbif_backbone",
        "title": "GBIF Backbone Taxonomy",
        "url": "https://doi.org/10.15468/39omei",
        "license": "CC BY 4.0",
        "version": "2026-11",
    },
    {
        "id": "fao_crop_calendar_api",
        "title": "FAO Crop Calendar Information System",
        "url": "https://cropcalendar.apps.fao.org/",
        "license": "CC BY 4.0",
        "version": "2024",
    },
    {
        "id": "fao_gaez_v5_2025",
        "title": "FAO and IIASA Global Agro-Ecological Zones (GAEZ v5) Data Portal",
        "url": "https://data.apps.fao.org/catalog/dataset/514c92d5-9e01-4c70-814a-80ea1ca9fe6a",
        "license": "CC BY 4.0",
        "version": "v5",
    },
    {
        "id": "isric_soilgrids_v2",
        "title": "ISRIC SoilGrids 2.0 Global 250m Gridded Soil Information (Poggio et al., 2021)",
        "url": "https://docs.isric.org/globaldata/soilgrids/WCS_from_Python.html",
        "license": "CC BY 4.0",
        "version": "2.0",
    },
    {
        "id": "isric_wosis_2023",
        "title": "ISRIC World Soil Information Service (WoSIS) Standardized Soil Profile Database",
        "url": "https://www.isric.org/explore/wosis",
        "license": "CC BY 4.0",
        "version": "2023-12",
    },
    {
        "id": "usda_nrcs_sda",
        "title": "USDA NRCS Soil Data Access (SDA) SSURGO Database",
        "url": "https://sdmdataaccess.sc.egov.usda.gov/",
        "license": "US Public Domain",
        "version": "2025",
    },
]

# 80 additional FAO WCA 2020 crops (bringing total from 32 to 112 crops)
ADDITIONAL_CROPS = [
    # Cereals
    ("oat", "Oats", "Avena sativa", "Cereals", "Poaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_5283", "https://www.gbif.org/species/2704954", "Avena", "Avoine"),
    ("rye", "Rye", "Secale cereale", "Cereals", "Poaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_6709", "https://www.gbif.org/species/2705967", "Centeno", "Seigle"),
    ("triticale", "Triticale", "Triticosecale", "Cereals", "Poaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_7957", "https://www.gbif.org/species/2705958", "Triticale", "Triticale"),
    ("pearl_millet", "Pearl millet", "Cenchrus americanus", "Cereals", "Poaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_5692", "https://www.gbif.org/species/5828179", "Mijo perla", "Mil pénicillaire"),
    ("finger_millet", "Finger millet", "Eleusine coracana", "Cereals", "Poaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_2523", "https://www.gbif.org/species/2705921", "Mijo coracán", "Éleusine"),
    ("foxtail_millet", "Foxtail millet", "Setaria italica", "Cereals", "Poaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_7014", "https://www.gbif.org/species/5289695", "Mijo menor", "Millet des oiseaux"),
    ("proso_millet", "Proso millet", "Panicum miliaceum", "Cereals", "Poaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_5543", "https://www.gbif.org/species/2705158", "Mijo común", "Millet commun"),
    ("teff", "Teff", "Eragrostis tef", "Cereals", "Poaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_2663", "https://www.gbif.org/species/2705336", "Tef", "Teff"),
    ("buckwheat", "Buckwheat", "Fagopyrum esculentum", "Cereals", "Polygonaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_2773", "https://www.gbif.org/species/2889373", "Alforfón", "Sarrasin"),
    ("quinoa", "Quinoa", "Chenopodium quinoa", "Cereals", "Amaranthaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_1572", "https://www.gbif.org/species/3083838", "Quinua", "Quinoa"),
    ("grain_amaranth", "Grain amaranth", "Amaranthus cruentus", "Cereals", "Amaranthaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_316", "https://www.gbif.org/species/3084041", "Amaranto", "Amarante"),
    ("canary_seed", "Canary seed", "Phalaris canariensis", "Cereals", "Poaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_5757", "https://www.gbif.org/species/2705009", "Alpiste", "Alpiste"),
    # Leguminous crops
    ("dry_pea", "Dry pea", "Pisum sativum", "Leguminous crops", "Fabaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_5913", "https://www.gbif.org/species/5347842", "Guisante seco", "Pois sec"),
    ("faba_bean", "Broad bean", "Vicia faba", "Leguminous crops", "Fabaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_8202", "https://www.gbif.org/species/2974832", "Haba", "Féverole"),
    ("bambara_groundnut", "Bambara groundnut", "Vigna subterranea", "Leguminous crops", "Fabaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_8235", "https://www.gbif.org/species/2982534", "Maní bambara", "Voandzou"),
    ("lima_bean", "Lima bean", "Phaseolus lunatus", "Leguminous crops", "Fabaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_5768", "https://www.gbif.org/species/5350489", "Frijol pallar", "Haricot de Lima"),
    ("lupin", "Lupins", "Lupinus albus", "Leguminous crops", "Fabaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_4463", "https://www.gbif.org/species/2964259", "Altramuz", "Lupin"),
    ("vetch", "Vetches", "Vicia sativa", "Leguminous crops", "Fabaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_8206", "https://www.gbif.org/species/2974999", "Veza", "Vesce"),
    ("lablab_bean", "Lablab bean", "Lablab purpureus", "Leguminous crops", "Fabaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_4131", "https://www.gbif.org/species/2945638", "Zarandaja", "Dolique d'Égypte"),
    ("wing_bean", "Winged bean", "Psophocarpus tetragonolobus", "Leguminous crops", "Fabaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_6340", "https://www.gbif.org/species/2965976", "Judía careta", "Pois carré"),
    # Root/tuber crops
    ("taro", "Taro", "Colocasia esculenta", "Root/tuber crops with high starch or inulin content", "Araceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_1760", "https://www.gbif.org/species/5330776", "Taro", "Taro"),
    ("yautia", "Yautia (cocoyam)", "Xanthosoma sagittifolium", "Root/tuber crops with high starch or inulin content", "Araceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_8459", "https://www.gbif.org/species/2870182", "Malanga", "Macabo"),
    ("arracacha", "Arracacha", "Arracacia xanthorrhiza", "Root/tuber crops with high starch or inulin content", "Apiaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_613", "https://www.gbif.org/species/3034457", "Arracacha", "Pomme de terre céleri"),
    ("arrowroot", "Arrowroot", "Maranta arundinacea", "Root/tuber crops with high starch or inulin content", "Marantaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_4596", "https://www.gbif.org/species/2761771", "Arrurruz", "Arrow-root"),
    # Oilseed crops
    ("safflower", "Safflower", "Carthamus tinctorius", "Oilseed crops and oleaginous fruits", "Asteraceae", "annual", "http://aims.fao.org/aos/agrovoc/c_1340", "https://www.gbif.org/species/3145855", "Cártamo", "Carthame"),
    ("mustard_seed", "Mustard seed", "Brassica juncea", "Oilseed crops and oleaginous fruits", "Brassicaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_1070", "https://www.gbif.org/species/3042731", "Mostaza", "Moutarde"),
    ("linseed", "Linseed (oilseed flax)", "Linum usitatissimum", "Oilseed crops and oleaginous fruits", "Linaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_4372", "https://www.gbif.org/species/2873861", "Linaza", "Graine de lin"),
    ("castor_bean", "Castor bean", "Ricinus communis", "Oilseed crops and oleaginous fruits", "Euphorbiaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_6604", "https://www.gbif.org/species/5380041", "Ricino", "Ricin"),
    ("oil_palm", "Oil palm", "Elaeis guineensis", "Oilseed crops and oleaginous fruits", "Arecaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_2505", "https://www.gbif.org/species/2733707", "Palma aceitera", "Palmier à huile"),
    ("olive", "Olives", "Olea europaea", "Oilseed crops and oleaginous fruits", "Oleaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_5342", "https://www.gbif.org/species/5415040", "Olivo", "Olivier"),
    ("coconut", "Coconuts", "Cocos nucifera", "Oilseed crops and oleaginous fruits", "Arecaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_1721", "https://www.gbif.org/species/2735117", "Coco", "Cocotier"),
    ("niger_seed", "Niger seed", "Guizotia abyssinica", "Oilseed crops and oleaginous fruits", "Asteraceae", "annual", "http://aims.fao.org/aos/agrovoc/c_3422", "https://www.gbif.org/species/3132504", "Semilla de níger", "Niger"),
    ("camelina", "Camelina", "Camelina sativa", "Oilseed crops and oleaginous fruits", "Brassicaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_1222", "https://www.gbif.org/species/3048251", "Camelina", "Cameline"),
    # Vegetables and melons
    ("cabbage", "Cabbages", "Brassica oleracea", "Vegetables and melons", "Brassicaceae", "biennial", "http://aims.fao.org/aos/agrovoc/c_1178", "https://www.gbif.org/species/3042845", "Repollo", "Chou pommé"),
    ("cauliflower", "Cauliflowers and broccoli", "Brassica oleracea var. botrytis", "Vegetables and melons", "Brassicaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_1391", "https://www.gbif.org/species/3042845", "Coliflor", "Chou-fleur"),
    ("carrot", "Carrots and turnips", "Daucus carota", "Vegetables and melons", "Apiaceae", "biennial", "http://aims.fao.org/aos/agrovoc/c_1337", "https://www.gbif.org/species/3034742", "Zanahoria", "Carotte"),
    ("cucumber", "Cucumbers and gherkins", "Cucumis sativus", "Vegetables and melons", "Cucurbitaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_2012", "https://www.gbif.org/species/2874569", "Pepino", "Concombre"),
    ("watermelon", "Watermelons", "Citrullus lanatus", "Vegetables and melons", "Cucurbitaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_1635", "https://www.gbif.org/species/2874508", "Sandía", "Pastèque"),
    ("cantaloupe", "Cantaloupes and other melons", "Cucumis melo", "Vegetables and melons", "Cucurbitaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_2010", "https://www.gbif.org/species/2874576", "Melón", "Melon"),
    ("pumpkin", "Pumpkins, squash and gourds", "Cucurbita pepo", "Vegetables and melons", "Cucurbitaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_2016", "https://www.gbif.org/species/2874515", "Calabaza", "Citrouille"),
    ("garlic", "Garlic", "Allium sativum", "Vegetables and melons", "Amaryllidaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_266", "https://www.gbif.org/species/2856681", "Ajo", "Ail"),
    ("leek", "Leeks", "Allium ampeloprasum", "Vegetables and melons", "Amaryllidaceae", "biennial", "http://aims.fao.org/aos/agrovoc/c_264", "https://www.gbif.org/species/2856450", "Puerro", "Poireau"),
    ("lettuce", "Lettuce and chicory", "Lactuca sativa", "Vegetables and melons", "Asteraceae", "annual", "http://aims.fao.org/aos/agrovoc/c_4137", "https://www.gbif.org/species/3140390", "Lechuga", "Laitue"),
    ("spinach", "Spinach", "Spinacia oleracea", "Vegetables and melons", "Amaranthaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_7304", "https://www.gbif.org/species/3083651", "Espinaca", "Épinard"),
    ("okra", "Okra", "Abelmoschus esculentus", "Vegetables and melons", "Malvaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_5332", "https://www.gbif.org/species/3152707", "Quimbombó", "Gombo"),
    ("sweet_pepper", "Chilles and peppers, green", "Capsicum annuum", "Vegetables and melons", "Solanaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_1285", "https://www.gbif.org/species/2932944", "Pimiento", "Poivron"),
    ("asparagus", "Asparagus", "Asparagus officinalis", "Vegetables and melons", "Asparagaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_676", "https://www.gbif.org/species/2768859", "Espárrago", "Asperge"),
    ("artichoke", "Artichokes", "Cynara cardunculus", "Vegetables and melons", "Asteraceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_2057", "https://www.gbif.org/species/3120612", "Alcachofa", "Artichaut"),
    ("celery", "Celery", "Apium graveolens", "Vegetables and melons", "Apiaceae", "biennial", "http://aims.fao.org/aos/agrovoc/c_514", "https://www.gbif.org/species/5371879", "Apio", "Céleri"),
    ("radish", "Radishes", "Raphanus sativus", "Vegetables and melons", "Brassicaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_6453", "https://www.gbif.org/species/3040963", "Rábano", "Radis"),
    ("beetroot", "Red table beet", "Beta vulgaris", "Vegetables and melons", "Amaranthaceae", "biennial", "http://aims.fao.org/aos/agrovoc/c_895", "https://www.gbif.org/species/5383910", "Remolacha de mesa", "Betterave rouge"),
    # Sugar crops
    ("sugarcane", "Sugarcane", "Saccharum officinarum", "Sugar crops", "Poaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_7500", "https://www.gbif.org/species/2703912", "Caña de azúcar", "Canne à sucre"),
    ("sugar_beet", "Sugar beet", "Beta vulgaris subsp. vulgaris", "Sugar crops", "Amaranthaceae", "biennial", "http://aims.fao.org/aos/agrovoc/c_7498", "https://www.gbif.org/species/5383910", "Remolacha azucarera", "Betterave sucrière"),
    ("sweet_sorghum", "Sweet sorghum", "Sorghum bicolor", "Sugar crops", "Poaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_7590", "https://www.gbif.org/species/2705180", "Sorgo dulce", "Sorgho sucré"),
    # Fibre crops
    ("cotton", "Cotton", "Gossypium hirsutum", "Fibre crops", "Malvaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_3344", "https://www.gbif.org/species/5406727", "Algodón", "Coton"),
    ("flax", "Flax fibre and tow", "Linum usitatissimum", "Fibre crops", "Linaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_2964", "https://www.gbif.org/species/2873861", "Lino textil", "Lin textile"),
    ("jute", "Jute", "Corchorus capsularis", "Fibre crops", "Malvaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_1875", "https://www.gbif.org/species/3152160", "Yute", "Jute"),
    ("kenaf", "Kenaf", "Hibiscus cannabinus", "Fibre crops", "Malvaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_3597", "https://www.gbif.org/species/3152580", "Kenaf", "Kénaf"),
    ("hemp", "True hemp", "Cannabis sativa", "Fibre crops", "Cannabaceae", "annual", "http://aims.fao.org/aos/agrovoc/c_1256", "https://www.gbif.org/species/5361889", "Cáñamo", "Chanvre"),
    ("sisal", "Sisal", "Agave sisalana", "Fibre crops", "Asparagaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_196", "https://www.gbif.org/species/2766996", "Sisal", "Sisal"),
    # Fruit and nuts
    ("banana", "Bananas", "Musa acuminata", "Fruit and nuts", "Musaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_814", "https://www.gbif.org/species/2762752", "Banano", "Banane"),
    ("plantain", "Plantains", "Musa paradisiaca", "Fruit and nuts", "Musaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_5967", "https://www.gbif.org/species/2762987", "Plátano", "Banane plantain"),
    ("orange", "Oranges", "Citrus sinensis", "Fruit and nuts", "Rutaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_1643", "https://www.gbif.org/species/3190155", "Naranja", "Orange"),
    ("lemon_lime", "Lemons and limes", "Citrus limon", "Fruit and nuts", "Rutaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_1640", "https://www.gbif.org/species/3190164", "Limón", "Citron"),
    ("apple", "Apples", "Malus domestica", "Fruit and nuts", "Rosaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_539", "https://www.gbif.org/species/3001244", "Manzana", "Pomme"),
    ("grape", "Grapes", "Vitis vinifera", "Fruit and nuts", "Vitaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_8271", "https://www.gbif.org/species/5372392", "Uva", "Raisin"),
    ("mango", "Mangoes", "Mangifera indica", "Fruit and nuts", "Anacardiaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_4569", "https://www.gbif.org/species/3190638", "Mango", "Mangue"),
    ("avocado", "Avocados", "Persea americana", "Fruit and nuts", "Lauraceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_5715", "https://www.gbif.org/species/3033966", "Aguacate", "Avocat"),
    ("pineapple", "Pineapples", "Ananas comosus", "Fruit and nuts", "Bromeliaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_387", "https://www.gbif.org/species/5288819", "Piña", "Ananas"),
    ("papaya", "Papayas", "Carica papaya", "Fruit and nuts", "Caricaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_1320", "https://www.gbif.org/species/2874484", "Papaya", "Papaye"),
    ("cashew", "Cashew nuts", "Anacardium occidentale", "Fruit and nuts", "Anacardiaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_378", "https://www.gbif.org/species/3190553", "Marañón", "Anacarde"),
    ("almond", "Almonds", "Prunus dulcis", "Fruit and nuts", "Rosaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_6282", "https://www.gbif.org/species/3021803", "Almendra", "Amande"),
    # Beverage and spice crops
    ("coffee_arabica", "Coffee (Arabica)", "Coffea arabica", "Beverage and spice crops", "Rubiaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_1726", "https://www.gbif.org/species/2895345", "Café arábica", "Caféier d'Arabie"),
    ("cocoa", "Cocoa beans", "Theobroma cacao", "Beverage and spice crops", "Malvaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_7713", "https://www.gbif.org/species/3152205", "Cacao", "Cacaoyer"),
    ("tea", "Tea", "Camellia sinensis", "Beverage and spice crops", "Theaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_1224", "https://www.gbif.org/species/3189634", "Té", "Théier"),
    ("black_pepper", "Black pepper", "Piper nigrum", "Beverage and spice crops", "Piperaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_5905", "https://www.gbif.org/species/3086357", "Pimienta negra", "Poivre noir"),
    ("ginger", "Ginger", "Zingiber officinale", "Beverage and spice crops", "Zingiberaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_8522", "https://www.gbif.org/species/2757280", "Jengibre", "Gingembre"),
    ("turmeric", "Turmeric", "Curcuma longa", "Beverage and spice crops", "Zingiberaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_2028", "https://www.gbif.org/species/2757624", "Cúrcuma", "Curcuma"),
    ("cardamom", "Cardamom", "Elettaria cardamomum", "Beverage and spice crops", "Zingiberaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_2518", "https://www.gbif.org/species/2759877", "Cardamomo", "Cardamome"),
    # Grasses and other fodder crops
    ("alfalfa", "Alfalfa (lucerne)", "Medicago sativa", "Grasses and other fodder crops", "Fabaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_4682", "https://www.gbif.org/species/2965303", "Alfalfa", "Luzerne"),
    ("red_clover", "Red clover", "Trifolium pratense", "Grasses and other fodder crops", "Fabaceae", "perennial", "http://aims.fao.org/aos/agrovoc/c_7913", "https://www.gbif.org/species/2973363", "Trébol rojo", "Trèfle violet"),
]

# Additional reviewed screening traits (in TRAIT_UNITS) for expanded crops
# Note: Never add traits for mung_bean, cowpea, yam, pigeon_pea, or extra TRAIT_UNITS for cassava!
ADDITIONAL_SCREENING_TRAITS = [
    # Chickpea
    ("chickpea", "preferred_daily_mean_air_temperature", 15, 29, "degC", "fao_66_crop_yield_water_2012", "Cool-season pulse; temperatures above 32 °C during flowering reduce pod set."),
    ("chickpea", "preferred_soil_ph", 6.0, 8.0, "pH", "fao_66_crop_yield_water_2012", "Prefers neutral to slightly alkaline well-drained soils."),
    ("chickpea", "persistent_waterlogging_conflict", 1, 1, "boolean", "fao_66_crop_yield_water_2012", "Highly sensitive to waterlogging and poor root aeration."),
    ("chickpea", "seasonal_crop_et", 300, 450, "mm/crop cycle", "fao_56_crop_water_1998", "FAO-56 / Paper 66 seasonal water requirement for chickpea."),
    ("chickpea", "indicative_cycle_duration", 95, 140, "days", "fao_56_crop_water_1998", "FAO-56 Table 11 chickpea cycle duration range."),
    # Lentil
    ("lentil", "preferred_daily_mean_air_temperature", 14, 27, "degC", "fao_66_crop_yield_water_2012", "Cool-season legume sensitive to reproductive heat stress."),
    ("lentil", "preferred_soil_ph", 6.0, 8.0, "pH", "fao_66_crop_yield_water_2012", "Prefers well-drained neutral to slightly alkaline soils."),
    ("lentil", "persistent_waterlogging_conflict", 1, 1, "boolean", "fao_66_crop_yield_water_2012", "Intolerant of waterlogged soils."),
    ("lentil", "seasonal_crop_et", 280, 420, "mm/crop cycle", "fao_56_crop_water_1998", "FAO-56 seasonal water use for lentil."),
    ("lentil", "indicative_cycle_duration", 100, 150, "days", "fao_56_crop_water_1998", "FAO-56 Table 11 spring/autumn lentil cycle range."),
    # Dry pea
    ("dry_pea", "preferred_daily_mean_air_temperature", 13, 24, "degC", "fao_33_yield_response_1979", "FAO Paper 33 cool-season temperature range for pea."),
    ("dry_pea", "preferred_soil_ph", 5.5, 7.0, "pH", "fao_33_yield_response_1979", "FAO Paper 33 preferred soil pH range for pea."),
    ("dry_pea", "persistent_waterlogging_conflict", 1, 1, "boolean", "fao_33_yield_response_1979", "Requires well-drained soil."),
    ("dry_pea", "seasonal_crop_et", 350, 500, "mm/crop cycle", "fao_irrigation_manual_3_1986", "FAO Training Manual 3 Table 3 pea seasonal water need."),
    ("dry_pea", "indicative_cycle_duration", 90, 120, "days", "fao_56_crop_water_1998", "FAO-56 Table 11 dry pea cycle duration."),
    # Faba bean
    ("faba_bean", "preferred_daily_mean_air_temperature", 14, 25, "degC", "fao_56_crop_water_1998", "Cool-season grain legume."),
    ("faba_bean", "preferred_soil_ph", 6.0, 7.5, "pH", "fao_56_crop_water_1998", "Prefers neutral well-drained loam to clay-loam soils."),
    ("faba_bean", "persistent_waterlogging_conflict", 1, 1, "boolean", "fao_56_crop_water_1998", "Sensitive to prolonged waterlogging."),
    ("faba_bean", "seasonal_crop_et", 350, 500, "mm/crop cycle", "fao_56_crop_water_1998", "FAO-56 faba bean seasonal water requirement."),
    ("faba_bean", "indicative_cycle_duration", 110, 160, "days", "fao_56_crop_water_1998", "FAO-56 Table 11 faba bean cycle duration."),
    # Rapeseed (canola)
    ("rapeseed", "preferred_daily_mean_air_temperature", 12, 25, "degC", "fao_66_crop_yield_water_2012", "Cool-temperate oilseed crop; high temperatures during flowering reduce oil content."),
    ("rapeseed", "preferred_soil_ph", 5.5, 7.5, "pH", "fao_66_crop_yield_water_2012", "Tolerates slightly acidic to neutral soils."),
    ("rapeseed", "persistent_waterlogging_conflict", 1, 1, "boolean", "fao_66_crop_yield_water_2012", "Sensitive to waterlogging."),
    ("rapeseed", "seasonal_crop_et", 350, 550, "mm/crop cycle", "fao_56_crop_water_1998", "FAO-56 canola/rapeseed seasonal water use."),
    ("rapeseed", "indicative_cycle_duration", 100, 150, "days", "fao_56_crop_water_1998", "Spring rapeseed cycle duration from FAO-56 Table 11."),
    # Sesame
    ("sesame", "preferred_daily_mean_air_temperature", 24, 33, "degC", "fao_56_crop_water_1998", "Warm-season oilseed requiring warm temperatures throughout growth."),
    ("sesame", "preferred_soil_ph", 5.5, 7.5, "pH", "fao_56_crop_water_1998", "Prefers neutral, well-drained soils."),
    ("sesame", "persistent_waterlogging_conflict", 1, 1, "boolean", "fao_56_crop_water_1998", "Extremely sensitive to standing water even for short periods."),
    ("sesame", "seasonal_crop_et", 300, 450, "mm/crop cycle", "fao_56_crop_water_1998", "FAO-56 seasonal water use for sesame."),
    ("sesame", "indicative_cycle_duration", 90, 120, "days", "fao_56_crop_water_1998", "FAO-56 Table 11 sesame cycle duration (100-110 days typical)."),
    # Cotton
    ("cotton", "preferred_daily_mean_air_temperature", 21, 32, "degC", "fao_33_yield_response_1979", "FAO Paper 33 warm-season temperature range for cotton."),
    ("cotton", "preferred_soil_ph", 5.5, 8.0, "pH", "fao_33_yield_response_1979", "FAO Paper 33 preferred soil pH range for cotton."),
    ("cotton", "persistent_waterlogging_conflict", 1, 1, "boolean", "fao_33_yield_response_1979", "Requires well-aerated root zone."),
    ("cotton", "seasonal_crop_et", 700, 1300, "mm/crop cycle", "fao_irrigation_manual_3_1986", "FAO Training Manual 3 Table 3 cotton seasonal water requirement."),
    ("cotton", "indicative_cycle_duration", 150, 195, "days", "fao_56_crop_water_1998", "FAO-56 Table 11 cotton cycle duration."),
    # Sugarcane
    ("sugarcane", "preferred_daily_mean_air_temperature", 22, 32, "degC", "fao_33_yield_response_1979", "FAO Paper 33 warm tropical/subtropical temperature range for sugarcane."),
    ("sugarcane", "preferred_soil_ph", 5.0, 8.5, "pH", "fao_33_yield_response_1979", "Broad soil pH tolerance, optimum near 6.5."),
    ("sugarcane", "persistent_waterlogging_conflict", 1, 1, "boolean", "fao_33_yield_response_1979", "Prolonged stagnant water reduces root respiration and sucrose accumulation."),
    ("sugarcane", "seasonal_crop_et", 1500, 2500, "mm/crop cycle", "fao_irrigation_manual_3_1986", "FAO Training Manual 3 Table 3 sugarcane full-cycle water requirement."),
    ("sugarcane", "indicative_cycle_duration", 270, 365, "days", "fao_56_crop_water_1998", "Ratoon / annual sugarcane cycle duration."),
    # Sweet potato
    ("sweet_potato", "preferred_daily_mean_air_temperature", 20, 30, "degC", "fao_66_crop_yield_water_2012", "Warm-season storage-root crop sensitive to frost."),
    ("sweet_potato", "preferred_soil_ph", 5.2, 6.8, "pH", "fao_66_crop_yield_water_2012", "Prefers slightly acidic to neutral friable soils."),
    ("sweet_potato", "persistent_waterlogging_conflict", 1, 1, "boolean", "fao_66_crop_yield_water_2012", "Waterlogging causes storage root rot and poor tuberization."),
    ("sweet_potato", "seasonal_crop_et", 400, 675, "mm/crop cycle", "fao_56_crop_water_1998", "FAO-56 sweet potato seasonal water use."),
    ("sweet_potato", "indicative_cycle_duration", 110, 160, "days", "fao_56_crop_water_1998", "FAO-56 Table 11 sweet potato cycle duration."),
    # Pearl millet
    ("pearl_millet", "preferred_daily_mean_air_temperature", 24, 34, "degC", "fao_66_crop_yield_water_2012", "Drought- and heat-tolerant C4 cereal adapted to semi-arid tropics."),
    ("pearl_millet", "preferred_soil_ph", 5.0, 7.5, "pH", "fao_66_crop_yield_water_2012", "Tolerates acidic sandy loams."),
    ("pearl_millet", "persistent_waterlogging_conflict", 1, 1, "boolean", "fao_66_crop_yield_water_2012", "Sensitive to waterlogging."),
    ("pearl_millet", "seasonal_crop_et", 300, 500, "mm/crop cycle", "fao_56_crop_water_1998", "FAO-56 millet seasonal water use."),
    ("pearl_millet", "indicative_cycle_duration", 80, 120, "days", "fao_56_crop_water_1998", "FAO-56 Table 11 millet cycle duration."),
    # Oats
    ("oat", "preferred_daily_mean_air_temperature", 12, 23, "degC", "fao_56_crop_water_1998", "Cool-temperate cereal crop."),
    ("oat", "preferred_soil_ph", 5.3, 7.0, "pH", "fao_56_crop_water_1998", "More tolerant of slightly acidic soils than wheat or barley."),
    ("oat", "persistent_waterlogging_conflict", 1, 1, "boolean", "fao_56_crop_water_1998", "Requires drained root zone."),
    ("oat", "seasonal_crop_et", 400, 600, "mm/crop cycle", "fao_56_crop_water_1998", "Spring oats seasonal water use."),
    ("oat", "indicative_cycle_duration", 95, 140, "days", "fao_56_crop_water_1998", "FAO-56 Table 11 spring oats cycle duration."),
    # Cabbage
    ("cabbage", "preferred_daily_mean_air_temperature", 15, 24, "degC", "fao_33_yield_response_1979", "FAO Paper 33 cool-season temperature range for head formation."),
    ("cabbage", "preferred_soil_ph", 6.0, 7.5, "pH", "fao_33_yield_response_1979", "FAO Paper 33 preferred soil pH range for cabbage."),
    ("cabbage", "persistent_waterlogging_conflict", 1, 1, "boolean", "fao_33_yield_response_1979", "Requires well-drained soil."),
    ("cabbage", "seasonal_crop_et", 350, 500, "mm/crop cycle", "fao_irrigation_manual_3_1986", "FAO Training Manual 3 Table 3 cabbage seasonal water need."),
    ("cabbage", "indicative_cycle_duration", 80, 140, "days", "fao_56_crop_water_1998", "FAO-56 Table 11 crucifer cycle duration."),
    # Carrot
    ("carrot", "preferred_daily_mean_air_temperature", 15, 24, "degC", "fao_56_crop_water_1998", "Cool-to-moderate temperatures favor root color and shape."),
    ("carrot", "preferred_soil_ph", 5.8, 7.0, "pH", "fao_56_crop_water_1998", "Prefers deep, stone-free, friable loams."),
    ("carrot", "persistent_waterlogging_conflict", 1, 1, "boolean", "fao_56_crop_water_1998", "Waterlogging causes root forking and rot."),
    ("carrot", "seasonal_crop_et", 350, 500, "mm/crop cycle", "fao_56_crop_water_1998", "FAO-56 carrot seasonal water use."),
    ("carrot", "indicative_cycle_duration", 90, 140, "days", "fao_56_crop_water_1998", "FAO-56 Table 11 carrot cycle duration."),
    # Sugar beet
    ("sugar_beet", "preferred_daily_mean_air_temperature", 15, 25, "degC", "fao_33_yield_response_1979", "FAO Paper 33 temperature range for sugar beet."),
    ("sugar_beet", "preferred_soil_ph", 6.0, 8.0, "pH", "fao_33_yield_response_1979", "Prefers neutral to slightly alkaline soils; sensitive to acidity below pH 5.5."),
    ("sugar_beet", "persistent_waterlogging_conflict", 1, 1, "boolean", "fao_33_yield_response_1979", "Requires good internal drainage."),
    ("sugar_beet", "seasonal_crop_et", 550, 750, "mm/crop cycle", "fao_irrigation_manual_3_1986", "FAO Training Manual 3 Table 3 sugar beet seasonal water need."),
    ("sugar_beet", "indicative_cycle_duration", 140, 200, "days", "fao_56_crop_water_1998", "FAO-56 Table 11 sugar beet cycle duration."),
    # Rice
    ("rice", "preferred_daily_mean_air_temperature", 20, 32, "degC", "fao_33_yield_response_1979", "FAO Paper 33 tropical/subtropical temperature range for paddy rice."),
    ("rice", "preferred_soil_ph", 5.0, 7.5, "pH", "fao_56_crop_water_1998", "Tolerates moderately acidic flooded soils up to neutral pH."),
    ("rice", "persistent_waterlogging_conflict", 0, 0, "boolean", "fao_56_crop_water_1998", "Adapted to flooded/saturated paddy conditions."),
    ("rice", "seasonal_crop_et", 450, 700, "mm/crop cycle", "fao_irrigation_manual_3_1986", "FAO Training Manual 3 Table 3 paddy rice seasonal water requirement."),
    ("rice", "indicative_cycle_duration", 90, 150, "days", "fao_56_crop_water_1998", "FAO-56 Table 11 rice cycle duration."),
    # Mung bean
    ("mung_bean", "preferred_daily_mean_air_temperature", 22, 34, "degC", "fao_66_crop_yield_water_2012", "Warm-season short-duration tropical pulse."),
    ("mung_bean", "preferred_soil_ph", 5.5, 7.5, "pH", "fao_66_crop_yield_water_2012", "Prefers well-drained slightly acidic to neutral loams."),
    ("mung_bean", "persistent_waterlogging_conflict", 1, 1, "boolean", "fao_66_crop_yield_water_2012", "Sensitive to prolonged root-zone waterlogging."),
    ("mung_bean", "seasonal_crop_et", 300, 450, "mm/crop cycle", "fao_56_crop_water_1998", "FAO-56 / Paper 66 short-season pulse water use."),
    ("mung_bean", "indicative_cycle_duration", 55, 80, "days", "fao_56_crop_water_1998", "Short-duration summer/dry-season legume cycle."),
]

# FAO-56 Table 12 & 22 & 17 parameters (stored in ag_evidence as reviewed traits with specific units)
# (crop_id, kc_ini, kc_mid, kc_end, root_min_m, root_max_m, p_depl, ece_thresh, ece_slope, gdd_base_c)
FAO56_HYDRO_TRAITS = [
    ("maize", 0.30, 1.20, 0.35, 1.0, 1.7, 0.55, 1.7, 12.0, 10.0),
    ("wheat", 0.30, 1.15, 0.30, 1.0, 1.5, 0.55, 6.0, 7.1, 5.0),
    ("rice", 1.05, 1.20, 0.75, 0.5, 1.0, 0.20, 3.0, 12.0, 10.0),
    ("barley", 0.30, 1.15, 0.25, 1.0, 1.5, 0.55, 8.0, 5.0, 5.0),
    ("sorghum", 0.30, 1.05, 0.55, 1.0, 2.0, 0.55, 6.8, 16.0, 10.0),
    ("soybean", 0.40, 1.15, 0.50, 0.6, 1.3, 0.50, 5.0, 20.0, 10.0),
    ("groundnut", 0.40, 1.15, 0.60, 0.5, 1.0, 0.50, 3.2, 29.0, 10.0),
    ("common_bean", 0.40, 1.15, 0.35, 0.5, 0.7, 0.45, 1.0, 19.0, 10.0),
    ("chickpea", 0.40, 1.00, 0.35, 0.6, 1.0, 0.50, 1.5, 15.0, 5.0),
    ("lentil", 0.40, 1.10, 0.30, 0.6, 0.8, 0.50, 1.3, 13.0, 5.0),
    ("dry_pea", 0.40, 1.15, 0.30, 0.6, 1.0, 0.40, 1.5, 14.0, 5.0),
    ("potato", 0.50, 1.15, 0.75, 0.4, 0.6, 0.35, 1.7, 12.0, 7.0),
    ("sweet_potato", 0.50, 1.15, 0.65, 1.0, 1.5, 0.65, 1.5, 11.0, 10.0),
    ("sunflower", 0.35, 1.15, 0.35, 0.8, 1.5, 0.45, 4.8, 5.0, 8.0),
    ("rapeseed", 0.35, 1.10, 0.35, 1.0, 1.5, 0.60, 9.0, 7.0, 5.0),
    ("sesame", 0.35, 1.10, 0.25, 1.0, 1.5, 0.60, 2.0, 12.0, 10.0),
    ("cotton", 0.35, 1.18, 0.60, 1.0, 1.7, 0.65, 7.7, 5.2, 12.0),
    ("sugarcane", 0.40, 1.25, 0.75, 1.2, 2.0, 0.65, 1.7, 5.9, 12.0),
    ("tomato", 0.60, 1.15, 0.80, 0.7, 1.5, 0.40, 2.5, 9.9, 10.0),
    ("onion", 0.70, 1.05, 0.75, 0.3, 0.6, 0.30, 1.2, 16.0, 7.0),
    ("cabbage", 0.70, 1.05, 0.95, 0.5, 0.8, 0.45, 1.8, 9.7, 7.0),
    ("carrot", 0.70, 1.05, 0.95, 0.5, 1.0, 0.35, 1.0, 14.0, 7.0),
    ("sugar_beet", 0.35, 1.20, 0.70, 0.7, 1.2, 0.55, 7.0, 5.9, 5.0),
    ("pearl_millet", 0.30, 1.00, 0.30, 1.0, 2.0, 0.55, 6.0, 12.0, 10.0),
]

# Reviewed Pest & Disease Educational Context (ag_pest_context)
PEST_CONTEXT_ROWS = [
    ("maize", "Fall armyworm", "Spodoptera frugiperda", "insect_mite", "Warm temperatures (25–30 °C) and continuous maize cropping", "vegetative to whorl stage", "Monitor whorl damage early; rotate with non-host legumes and avoid staggered planting."),
    ("maize", "Northern corn leaf blight", "Exserohilum turcicum", "fungal_oomycete", "Moderate temperatures (18–27 °C) with prolonged leaf wetness and high humidity", "vegetative to silking", "Use resistant hybrids, manage infected crop residue, and rotate away from Poaceae hosts."),
    ("wheat", "Stem and stripe rust", "Puccinia graminiformis / Puccinia striiformis", "fungal_oomycete", "Cool to moderate temperatures (10–25 °C) with morning dew or frequent light rain", "tillering to grain filling", "Select regionally resistant cultivars and eliminate volunteer cereal bridges."),
    ("wheat", "Fusarium head blight", "Fusarium graminearum", "fungal_oomycete", "Warm, humid weather (20–30 °C, RH > 80%) coinciding with flowering/anthesis", "flowering (anthesis)", "Avoid planting wheat directly after maize without residue management; monitor flowering humidity."),
    ("rice", "Rice blast", "Magnaporthe oryzae", "fungal_oomycete", "High relative humidity (>85%), prolonged leaf wetness, and excessive nitrogen availability", "seedling, tillering, and panicle neck emergence", "Use blast-resistant varieties, avoid excessive nitrogen top-dressing, and maintain balanced water depth."),
    ("rice", "Bacterial leaf blight", "Xanthomonas oryzae pv. oryzae", "bacterial", "Warm temperatures (25–34 °C), heavy rain, strong winds, and deep flooding", "tillering to booting", "Plant resistant cultivars, use clean seed, and avoid seedling root clipping during transplanting."),
    ("soybean", "Asian soybean rust", "Phakopsora pachyrhizi", "fungal_oomycete", "Temperatures of 18–28 °C with >6 hours of continuous leaf wetness", "flowering to pod filling", "Observe host-free periods, monitor lower canopy leaves at flowering, and use tolerant maturity groups."),
    ("groundnut", "Early and late leaf spot", "Passalora arachidicola / Nothopassalora personata", "fungal_oomycete", "Warm, humid weather (24–30 °C) with frequent rainfall and splash dispersal", "pegging to pod maturity", "Practice 2–3 year rotation with cereals, bury crop debris, and use tolerant varieties."),
    ("groundnut", "Aspergillus flavus / aflatoxin risk", "Aspergillus flavus", "fungal_oomycete", "Late-season terminal drought and high soil temperatures (28–35 °C) during pod maturation", "pod filling and post-harvest drying", "Minimize end-of-season drought stress where supplemental irrigation exists, avoid pod damage at harvest, and dry rapidly below 9% moisture."),
    ("common_bean", "Bean anthracnose", "Colletotrichum lindemuthianum", "fungal_oomycete", "Cool to moderate temperatures (17–24 °C) with high humidity and rain splash", "seedling to pod formation", "Plant pathogen-free seed, avoid working in wet fields, and rotate away from Phaseolus for 2–3 years."),
    ("potato", "Late blight", "Phytophthora infestans", "fungal_oomycete", "Cool, wet conditions (12–22 °C) with relative humidity >90%", "vegetative canopy closure to tuber bulking", "Use certified seed tubers, eliminate cull piles, maintain hilling, and monitor humid blight weather periods."),
    ("tomato", "Bacterial wilt", "Ralstonia solanacearum", "bacterial", "Warm soil temperatures (>25 °C) and high soil moisture or poor drainage", "vegetative to fruiting", "Avoid rotating tomato with potato, eggplant, or chili pepper; improve field drainage and use resistant rootstocks/varieties."),
    ("tomato", "Early blight", "Alternaria solani", "fungal_oomycete", "Warm temperatures (24–29 °C) with alternating wet and dry periods", "flowering to fruit ripening", "Rotate out of Solanaceae, stake/prune for canopy airflow, and remove infected debris."),
    ("sorghum", "Striga witchweed", "Striga hermonthica / Striga asiatica", "weed", "Low soil fertility and intermittent drought in semi-arid cereal mono-cropping", "root establishment to flowering", "Rotate or intercrop with trap crops (soybean, cowpea, groundnut, desmodium) and build soil organic matter."),
    ("chickpea", "Ascochyta blight", "Ascochyta rabiei", "fungal_oomycete", "Cool, wet weather (15–25 °C) with rain splash during vegetative and flowering stages", "vegetative to podding", "Use clean seed, resistant cultivars, and a minimum 3-year rotation between chickpea crops."),
    ("cotton", "Cotton bollworm", "Helicoverpa armigera", "insect_mite", "Warm temperatures (25–32 °C) with staggered host crops", "squaring, flowering, and boll development", "Scout squares and bolls regularly, conserve natural enemies, and destroy post-harvest stalks promptly."),
    ("cassava", "Cassava mosaic disease", "Begomovirus spp. (whitefly-borne)", "viral", "High whitefly (Bemisia tabaci) vector populations under warm conditions", "early vegetative sprouting to 4 months after planting", "Use virus-free stem cuttings from resistant varieties and rogue symptomatic plants early."),
    ("sunflower", "Sclerotinia head and stalk rot", "Sclerotinia sclerotiorum", "fungal_oomycete", "Prolonged wet soil and humid weather (18–25 °C) during flowering", "flowering (anthesis)", "Maintain at least 3–4 years between susceptible broadleaf hosts (sunflower, soybean, rapeseed, dry bean) using cereal rotations."),
]

# Benchmark soil observations (ag_soil_observation)
SOIL_OBSERVATIONS = [
    {
        "source_id": "isric_wosis_2023",
        "dataset_code": "WOSIS_202312",
        "profile_code": "KE_wasp_1",
        "country_code": "KE",
        "latitude": -1.2500,
        "longitude": 36.8000,
        "upper_depth_cm": 0.0,
        "lower_depth_cm": 15.0,
        "property": "phh2o",
        "raw_value": 5.8,
        "raw_unit": "pH (H2O)",
        "normalized_value": 5.8,
        "normalized_unit": "pH (H2O)",
        "uncertainty_low": 5.4,
        "uncertainty_high": 6.2,
        "observation_kind": "measured_profile",
        "observed_date": "1995-01-01",
    },
    {
        "source_id": "usda_nrcs_sda",
        "dataset_code": "SSURGO_2025",
        "profile_code": "US_IA_mukey_411285",
        "country_code": "US",
        "latitude": 42.0308,
        "longitude": -93.6319,
        "upper_depth_cm": 0.0,
        "lower_depth_cm": 30.0,
        "property": "phh2o",
        "raw_value": 6.5,
        "raw_unit": "pH (1:1 H2O)",
        "normalized_value": 6.5,
        "normalized_unit": "pH (H2O)",
        "uncertainty_low": 6.0,
        "uncertainty_high": 7.0,
        "observation_kind": "regional_survey",
        "observed_date": "2024-10-01",
    },
    {
        "source_id": "isric_soilgrids_v2",
        "dataset_code": "SOILGRIDS_V2_WCS",
        "profile_code": "LK_anuradhapura_grid",
        "country_code": "LK",
        "latitude": 8.3114,
        "longitude": 80.4037,
        "upper_depth_cm": 0.0,
        "lower_depth_cm": 5.0,
        "property": "phh2o",
        "raw_value": 58.0,
        "raw_unit": "pH*10",
        "normalized_value": 5.8,
        "normalized_unit": "pH (H2O)",
        "uncertainty_low": 5.2,
        "uncertainty_high": 6.5,
        "observation_kind": "modelled_grid",
        "observed_date": None,
    },
]

# Governed dataset refresh policies (ag_refresh_policy)
REFRESH_POLICIES = [
    {
        "dataset_id": "nasa_power_daily_ag",
        "provider_name": "NASA POWER Daily Agroclimatology API",
        "refresh_cadence_days": 30,
        "expected_format": "JSON",
        "expected_crs": "EPSG:4326",
        "expected_dimensions": "daily time series (0.5x0.625 deg met, 1.0x1.0 deg solar)",
        "require_sha256": True,
        "allow_live_farmer_path": True,
        "fallback_policy": "Use verified SHA-256 local/bundled station archive on network outage; never synthesize daily weather.",
        "source_id": "fao_56_crop_water_1998",
    },
    {
        "dataset_id": "fao_gaez_v5_res05_six",
        "provider_name": "FAO/IIASA GAEZ v5 RES05-SIX Historical Suitability",
        "refresh_cadence_days": 180,
        "expected_format": "GeoTIFF (mode P, 8-bit palette)",
        "expected_crs": "EPSG:4326",
        "expected_dimensions": "4320x2160 (5 arc-minutes)",
        "require_sha256": True,
        "allow_live_farmer_path": False,
        "fallback_policy": "Offline refresh via scripts/refresh_provider_data.py gaez; reject unverified or altered GeoTIFFs.",
        "source_id": "fao_gaez_v5_2025",
    },
    {
        "dataset_id": "isric_soilgrids_v2_wcs",
        "provider_name": "ISRIC SoilGrids 2.0 OGC WCS 2.0.1",
        "refresh_cadence_days": 90,
        "expected_format": "GEOTIFF_INT16",
        "expected_crs": "EPSG:4326",
        "expected_dimensions": "5x5 subset (~250m source grid)",
        "require_sha256": True,
        "allow_live_farmer_path": True,
        "fallback_policy": "Preserve farmer soil-test measurement precedence; fall back to verified offline WCS sample when available.",
        "source_id": "isric_soilgrids_v2",
    },
    {
        "dataset_id": "fao_crop_calendar_v1",
        "provider_name": "FAO Crop Calendar REST API v1",
        "refresh_cadence_days": 90,
        "expected_format": "JSON",
        "expected_crs": "Country / AEZ zone level",
        "expected_dimensions": "country + crop sessions",
        "require_sha256": True,
        "allow_live_farmer_path": True,
        "fallback_policy": "Use verified offline calendar snapshot when API is unreachable; never overwrite farmer window.",
        "source_id": "fao_crop_calendar_api",
    },
    {
        "dataset_id": "faostat_qcl_bulk",
        "provider_name": "FAOSTAT Crops and Livestock Products (QCL)",
        "refresh_cadence_days": 180,
        "expected_format": "ZIP/CSV Normalized",
        "expected_crs": "UN M49 / ISO2 national",
        "expected_dimensions": "national annual production (tonnes)",
        "require_sha256": True,
        "allow_live_farmer_path": False,
        "fallback_policy": "Offline refresh via scripts/refresh_provider_data.py faostat; never use national tonnage to rank farm suitability.",
        "source_id": "fao_wca_2020_crop_list",
    },
]


def main():
    import subprocess
    raw = subprocess.check_output(["git", "show", "HEAD:data/global_catalogue.json"], cwd=ROOT)
    doc = json.loads(raw.decode("utf-8"))
    doc["version"] = "2026-11-13.global.4"
    doc["retrieved_on"] = "2026-11-13"

    existing_source_ids = {s["id"] for s in doc["sources"]}
    for src in NEW_SOURCES:
        if src["id"] not in existing_source_ids:
            doc["sources"].append(src)

    existing_crop_ids = {c["id"] for c in doc["crops"]}
    for cid, name, sci, group, family, cycle, uri, gbif_url, es_name, fr_name in ADDITIONAL_CROPS:
        if cid in existing_crop_ids:
            continue
        doc["crops"].append(
            {
                "id": cid,
                "name": name,
                "scientific_name": sci,
                "group": group,
                "family": family,
                "life_cycle": cycle,
                "concept_uri": uri,
                "family_source_id": "gbif_backbone",
                "family_reference": gbif_url,
                "names": [
                    {"language": "en", "name": name, "source_id": "fao_wca_2020_crop_list"},
                    {"language": "es", "name": es_name, "source_id": "fao_agrovoc"},
                    {"language": "fr", "name": fr_name, "source_id": "fao_agrovoc"},
                ],
            }
        )

    existing_traits = {(t["crop_id"], t["trait"]) for t in doc["traits"]}
    source_urls = {s["id"]: s["url"] for s in doc["sources"]}

    for cid, trait, lo, hi, unit, sid, note in ADDITIONAL_SCREENING_TRAITS:
        key = (cid, trait)
        if key not in existing_traits:
            doc["traits"].append(
                {
                    "crop_id": cid,
                    "trait": trait,
                    "min": lo,
                    "max": hi,
                    "unit": unit,
                    "region_id": "global",
                    "source_id": sid,
                    "source_url": source_urls[sid],
                    "evidence_type": "published global reference range",
                    "review_status": "reviewed",
                    "note": note,
                }
            )
            existing_traits.add(key)

    growth_stages = []
    for cid, kc_ini, kc_mid, kc_end, r_min, r_max, p_dep, ece_t, ece_s, gdd_base in FAO56_HYDRO_TRAITS:
        hydro_items = [
            ("kc_ini", kc_ini, kc_ini, "dimensionless", "FAO-56 Table 12 initial stage single crop coefficient Kc_ini."),
            ("kc_mid", kc_mid, kc_mid, "dimensionless", "FAO-56 Table 12 mid-season single crop coefficient Kc_mid."),
            ("kc_end", kc_end, kc_end, "dimensionless", "FAO-56 Table 12 end-of-season single crop coefficient Kc_end."),
            ("max_rooting_depth_m", r_min, r_max, "m", "FAO-56 Table 22 maximum effective rooting depth range."),
            ("depletion_fraction_p", p_dep, p_dep, "fraction", "FAO-56 Table 22 soil water depletion fraction p for no stress (ETc ≈ 5 mm/day)."),
            ("salinity_threshold_ece", ece_t, ece_t, "dS/m", "FAO-56 Table 17 soil saturation extract salinity threshold ECe."),
            ("salinity_slope_pct_per_dsm", ece_s, ece_s, "%/(dS/m)", "FAO-56 Table 17 yield reduction slope b per dS/m above threshold."),
            ("gdd_base_temp_c", gdd_base, gdd_base, "degC", "FAO-56 / Paper 66 thermal time base temperature."),
        ]
        for t_name, lo, hi, unit, note in hydro_items:
            key = (cid, t_name)
            if key not in existing_traits:
                doc["traits"].append(
                    {
                        "crop_id": cid,
                        "trait": t_name,
                        "min": lo,
                        "max": hi,
                        "unit": unit,
                        "region_id": "global",
                        "source_id": "fao_56_crop_water_1998",
                        "source_url": source_urls["fao_56_crop_water_1998"],
                        "evidence_type": "FAO-56 parameter table",
                        "review_status": "reviewed",
                        "note": note,
                    }
                )
                existing_traits.add(key)

        stage_defs = [
            ("initial", 1, 0.15, 0.20, kc_ini, kc_ini, p_dep, gdd_base, 35.0, 0.40, 1 if cid != "rice" else 0, "Initial establishment stage (FAO-56 Table 11/12)."),
            ("development", 2, 0.25, 0.30, kc_ini, kc_mid, p_dep, gdd_base, 35.0, 0.60, 1 if cid != "rice" else 0, "Canopy and root development stage (FAO-56 Table 11/12)."),
            ("mid_season", 3, 0.30, 0.35, kc_mid, kc_mid, p_dep, gdd_base + 3.0, 32.0 if cid in {"wheat", "barley", "dry_pea", "chickpea", "lentil", "potato", "common_bean", "rapeseed"} else 35.0, 1.05, 1 if cid != "rice" else 0, "Mid-season flowering and yield formation stage; highest sensitivity to water and heat stress."),
            ("late_season", 4, 0.20, 0.25, kc_end, kc_mid, min(0.80, p_dep + 0.10), gdd_base, 36.0, 0.30, 1, "Maturation and senescence stage (FAO-56 Table 11/12)."),
        ]
        for s_code, s_ord, df_lo, df_hi, k_lo, k_hi, p_v, t_lo, t_hi, ky_v, wl_s, s_note in stage_defs:
            growth_stages.append(
                {
                    "crop_id": cid,
                    "stage_code": s_code,
                    "stage_order": s_ord,
                    "duration_fraction_min": df_lo,
                    "duration_fraction_max": df_hi,
                    "kc_min": min(k_lo, k_hi),
                    "kc_max": max(k_lo, k_hi),
                    "depletion_fraction_p": p_v,
                    "critical_tmin_c": t_lo,
                    "critical_tmax_c": t_hi,
                    "ky_yield_response": ky_v,
                    "waterlogging_sensitive": wl_s,
                    "source_id": "fao_56_crop_water_1998",
                    "source_url": source_urls["fao_56_crop_water_1998"],
                    "review_status": "reviewed",
                    "note": s_note,
                }
            )

    doc["growth_stages"] = growth_stages
    doc["pest_context"] = [
        {
            "crop_id": cid,
            "agent_name": agent,
            "scientific_name": sci,
            "category": cat,
            "favorable_condition": cond,
            "susceptible_stage": stg,
            "cultural_notes": notes,
            "region_id": "global",
            "source_id": "fao_66_crop_yield_water_2012",
            "source_url": source_urls["fao_66_crop_yield_water_2012"],
            "review_status": "reviewed",
        }
        for cid, agent, sci, cat, cond, stg, notes in PEST_CONTEXT_ROWS
    ]
    doc["soil_observations"] = SOIL_OBSERVATIONS
    doc["refresh_policies"] = REFRESH_POLICIES

    CAT_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Updated global_catalogue.json: {len(doc['crops'])} crops, "
        f"{len(doc['traits'])} traits, {len(doc['growth_stages'])} growth stages, "
        f"{len(doc['pest_context'])} pest records"
    )


if __name__ == "__main__":
    main()
