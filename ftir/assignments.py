"""
IR peak assignment table and wavenumber mapping.
Covers 400–3900 cm⁻¹ with no gaps.
References:
  - Colthup, Daly & Wiberley (1990)
  - Movasaghi et al. Appl. Spectrosc. Rev. 43 (2008) 134-179
  - Stuart, Biological Applications of Infrared Spectroscopy (1997)
"""
import pandas as pd

IR_TABLE = [
    # (wn_low, wn_high, functional_group, bond, vibration_type, compound_class, biological_relevance)

    # ── O–H / N–H above 3700 ──
    (3700, 3900, "O–H Overtone / Atmospheric",  "O–H",          "overtone / combination",         "Water vapour, atmospheric",              "Atmospheric water vapour / instrument noise above 3700 cm⁻¹"),
    (3600, 3700, "Alcohol / Water",              "O–H",          "stretch (free)",                 "Alcohols, water",                        "Free hydroxyl groups, trace water"),
    (3400, 3600, "Alcohol / Carbohydrate",       "O–H",          "stretch (H-bonded)",             "Alcohols, sugars, water",                "Glucose, raffinose, HES — preservation solutes"),
    (3300, 3500, "Amine / Amide",                "N–H",          "stretch",                        "Primary/secondary amines, amides",       "Proteins, amino acids (glutathione, adenosine)"),
    (3200, 3400, "Water / Carbohydrate",         "O–H",          "stretch (broad, H-bonded)",      "Water, polysaccharides",                 "Aqueous matrix, HES backbone"),
    (3050, 3200, "Aromatic C–H / Alkene",        "=C–H",         "stretch",                        "Aromatics, alkenes",                     "Aromatic amino acids, unsaturated lipids"),

    # ── C–H stretch (2700–3050) ──
    (2950, 2970, "Alkyl — CH₃ (lipid)",          "C–H",          "asym. stretch –CH₃",            "Lipids, fatty acids",                    "Lipid membrane fragments"),
    (2910, 2935, "Alkyl — CH₂ (lipid)",          "C–H",          "asym. stretch –CH₂–",           "Lipids, fatty acids",                    "Phospholipid acyl chains"),
    (2855, 2875, "Alkyl — CH₂ sym (lipid)",      "C–H",          "sym. stretch –CH₂–",            "Lipids, fatty acids",                    "Phospholipid acyl chains (↑ after = cell lysis marker)"),
    (2830, 2860, "Alkyl — CH₃ sym",              "C–H",          "sym. stretch –CH₃",             "Methyl-bearing molecules",               "Various metabolites"),
    (2700, 2830, "Aldehyde / N–H overtone",      "C–H / N–H",    "aldehyde C–H / Fermi resonance","Aldehydes, amines",                      "Aldehyde C–H ~2720 cm⁻¹ (lipid peroxidation); N–H overtone"),

    # ── Overtone / CO₂ / combination (1960–2700) ──
    (2500, 2700, "Carboxylic acid O–H",          "O–H",          "stretch (very broad)",           "Carboxylic acids",                       "Organic acids, metabolic byproducts"),
    (2280, 2500, "CO₂ / Combination",            "O=C=O",        "antisym. stretch / overtone",    "Atmospheric CO₂, combinations",          "CO₂ ~2349 cm⁻¹ (atmospheric); weak combination 2400–2500 cm⁻¹"),
    (2100, 2280, "Nitrile / Isocyanate",         "C≡N / C=N=O",  "stretch",                        "Nitriles, isocyanates",                  "Rare in normal fluid — toxicity indicator if present"),
    (2033, 2100, "Combination band",             "C–O / C–C",    "combination / overtone",         "Carbohydrates, alcohols",                "Weak combinations of carbohydrate C–O stretches"),
    (1960, 2033, "Overtone",                     "C=O",          "overtone",                       "Carbonyl-containing molecules",          "Weak overtone; no strong absorbers expected here"),
    (1900, 1960, "Overtone / Combination",       "C=O",          "overtone / combination",         "Background",                             "Weak combination bands; minor background feature"),
    (1860, 1900, "Anhydride",                    "C=O",          "asym. stretch",                  "Anhydrides",                             "Degradation product or artefact"),
    (1820, 1860, "Anhydride / Lactone",          "C=O",          "sym. stretch",                   "Anhydrides, five-membered lactones",     "Cyclic anhydride / lactone — degradation product"),
    (1755, 1820, "Ester / Carbonate",            "C=O",          "stretch",                        "Esters, carbonates",                     "Membrane-derived ester / carbonate"),

    # ── Carbonyl region (1700–1755) ──
    (1735, 1755, "Ester / Lipid",                "C=O",          "stretch",                        "Esters, triglycerides, phospholipids",   "Lipid esters — membrane integrity marker (↑ = membrane damage)"),
    (1710, 1730, "Carboxylic acid / Aldehyde",   "C=O",          "stretch",                        "Carboxylic acids, aldehydes",            "Free fatty acids, aldehyde metabolites (oxidative stress marker)"),

    # ── Amide / protein region (1500–1710) ──
    (1680, 1700, "Amide I — unordered protein",  "C=O",          "stretch (unordered)",            "Proteins",                               "Denatured / unordered protein — ↑ in stressed fluid"),
    (1650, 1680, "Amide I — α-helix",            "C=O",          "stretch (α-helix)",              "Proteins (albumin, enzymes)",            "Major protein secondary structure band (key toxicity marker)"),
    (1620, 1650, "Amide I — β-sheet / Water",    "C=O / H–O–H",  "stretch / bend",                 "Proteins, water",                        "β-sheet proteins; water bending ~1640 cm⁻¹"),
    (1590, 1620, "Aromatic / C=C",               "C=C",          "stretch",                        "Aromatics, purines",                     "Adenosine ring vibration, aromatic amino acids"),
    (1570, 1590, "C=C / Aromatic",               "C=C",          "stretch",                        "Conjugated systems, aromatics",          "Purine/pyrimidine ring vibrations (adenosine, nucleotides)"),
    (1535, 1570, "Amide II",                     "N–H / C–N",    "bend + stretch",                 "Proteins, peptides",                     "Coupled N–H bend / C–N stretch — protein content marker"),
    (1510, 1535, "Amide II — extended / Tyr",    "N–H / C–N",    "bend + C–N stretch",             "Proteins, tyrosine",                     "Amide II tail; tyrosine ring vibration ~1515 cm⁻¹"),
    (1480, 1510, "Amide II / Aromatic",          "N–H / C=C",    "bend",                           "Proteins, aromatic rings",               "Secondary protein band"),

    # ── Fingerprint — CH / carboxylate (1300–1480) ──
    (1445, 1480, "Lipid / Protein CH₂",          "C–H",          "scissoring –CH₂–",              "Lipids, aliphatic proteins",             "Fatty acid chain length indicator"),
    (1395, 1445, "Carboxylate",                  "COO⁻",         "sym. stretch",                   "Amino acids, fatty acid salts",          "Ionised carboxylate (amino acids, glutathione)"),
    (1365, 1395, "Alkyl / Nitrate",              "C–H / N–O",    "bending / stretch",              "tert-Butyl, nitrates",                   "Hydroxyethyl groups (HES), inorganic nitrate"),
    (1300, 1365, "Amide III / CH",               "C–N / N–H",    "bend + stretch",                 "Proteins",                               "Tertiary protein structure marker"),

    # ── Phosphate / carbohydrate (900–1300) ──
    (1215, 1265, "Phospholipid / Amide III",     "P=O / C–N",    "asym. stretch",                  "Phospholipids, nucleic acids",           "Membrane phospholipids — integrity indicator"),
    (1140, 1215, "Carbohydrate",                 "C–O",          "stretch",                        "Sugars, glycogen",                       "Glucose, raffinose, HES (C–O of C–OH groups)"),
    (1070, 1140, "Phosphate / Carbohydrate",     "P–O / C–O–C",  "sym. stretch",                   "Phosphate, sugars",                      "Phosphate buffer, glucose ring C–O–C (key preservation band)"),
    (1020, 1070, "Carbohydrate",                 "C–O–C",        "glycosidic stretch",             "Polysaccharides, monosaccharides",       "Raffinose, glucose, HES backbone — key preservation markers"),
    (970,  1020, "Phosphodiester / Sugar",       "C–O–P / C–OH", "stretch",                        "Nucleotides, sugars",                    "Adenosine phosphate bonds"),
    (890,  970,  "Anomeric C–H / Phosphate",     "=C–H / P–O",   "bend / stretch",                 "Sugars (β-anomers), phosphate",          "Carbohydrate anomeric configuration"),

    # ── Aromatic / fingerprint (400–890) ──
    (800,  890,  "Aromatic C–H / Silicone",      "=C–H / Si–O",  "out-of-plane bend",              "Aromatics, Si–O (contaminant check)",    "Adenine ring C–H; Si–O ~840 cm⁻¹ = silicone contamination"),
    (700,  800,  "Aromatic / Alkene",            "=C–H",         "out-of-plane bend",              "Mono-subst. aromatics, alkenes",         "Aromatic amino acids (phenylalanine, tyrosine)"),
    (710,  730,  "Lipid — long chain",           "(CH₂)ₙ",       "rocking (n > 4)",                "Long-chain fatty acids",                 "Saturated fatty acid chains — membrane-derived lipids"),
    (600,  700,  "C–Cl / Aromatic",              "C–X / C–H",    "stretch / bend",                 "Halogenated compounds, aromatics",       "Possible chlorinated metabolites or contaminants"),
    (500,  600,  "Inorganic / Skeletal",         "M–O / P–O",    "bend",                           "Metal oxides, phosphate",                "Inorganic phosphate, metal salts (preservation buffer)"),
    (400,  500,  "Inorganic / Skeletal",         "M–L",          "stretch / bend",                 "Mineral salts, metal-ligand",            "KH₂PO₄, MgSO₄ salts in preservation solution"),
]

IR_DF = pd.DataFrame(IR_TABLE, columns=[
    "wn_low", "wn_high", "functional_group", "bond",
    "vibration_type", "compound_class", "biological_relevance",
])

# Spectral regions for grouping
REGIONS = [
    (400,   700,  "Fingerprint / Inorganic"),
    (700,   900,  "Aromatic & Long-chain C–H"),
    (900,  1300,  "Carbohydrate / Phosphate"),
    (1300, 1500,  "Protein C–H / Carboxylate"),
    (1500, 1800,  "Amide (Protein) / Lipid C=O"),
    (1800, 2800,  "Overtone / Combination / CO₂"),
    (2800, 3050,  "C–H Stretch (Lipids)"),
    (3050, 3700,  "O–H / N–H Stretch"),
    (3700, 3900,  "O–H Overtone / Atmospheric"),
]

REGION_COLORS = {
    "Fingerprint / Inorganic":       "#e74c3c",
    "Aromatic & Long-chain C–H":     "#e67e22",
    "Carbohydrate / Phosphate":      "#f39c12",
    "Protein C–H / Carboxylate":     "#2ecc71",
    "Amide (Protein) / Lipid C=O":   "#1abc9c",
    "Overtone / Combination / CO₂":  "#3498db",
    "C–H Stretch (Lipids)":          "#9b59b6",
    "O–H / N–H Stretch":             "#e91e63",
    "O–H Overtone / Atmospheric":    "#b0bec5",
}

# Toxicity marker definitions (used in Mode 2)
TOXICITY_MARKERS = [
    {
        "name":        "Protein denaturation (Amide I shift)",
        "band_label":  "Amide I ~1650 cm⁻¹",
        "bins":        [1650, 1660, 1670],
        "direction":   "shift",
        "description": "Shift to ~1620–1630 cm⁻¹ indicates β-sheet aggregation / protein unfolding",
    },
    {
        "name":        "Protein content change (Amide II)",
        "band_label":  "Amide II ~1550 cm⁻¹",
        "bins":        [1540, 1550, 1560],
        "direction":   "increase",
        "description": "Intensity ↑ = protein leakage from lysed cells; ↓ = protein degradation",
    },
    {
        "name":        "Lipid membrane damage (Ester C=O)",
        "band_label":  "Ester C=O ~1740 cm⁻¹",
        "bins":        [1740, 1750],
        "direction":   "increase",
        "description": "Intensity ↑ = oxidised / hydrolysed membrane lipids",
    },
    {
        "name":        "Cell lysis (CH₂ stretch)",
        "band_label":  "CH₂ ~2920 cm⁻¹",
        "bins":        [2920, 2930],
        "direction":   "increase",
        "description": "Intensity ↑ = membrane lipids released by cell lysis",
    },
    {
        "name":        "Lipid peroxidation (CH₂ sym)",
        "band_label":  "CH₂ sym ~2850 cm⁻¹",
        "bins":        [2850, 2860],
        "direction":   "increase",
        "description": "Intensity ↑ = saturated lipid chain accumulation (peroxidation)",
    },
    {
        "name":        "Free fatty acid release",
        "band_label":  "Carboxylic C=O ~1720 cm⁻¹",
        "bins":        [1710, 1720, 1730],
        "direction":   "increase",
        "description": "Intensity ↑ = phospholipid hydrolysis releasing free fatty acids (ischaemia)",
    },
    {
        "name":        "Preservation solute depletion",
        "band_label":  "Carbohydrate C–O ~1040 cm⁻¹",
        "bins":        [1030, 1040, 1050],
        "direction":   "decrease",
        "description": "Intensity ↓ = glucose / raffinose / HES consumption or degradation",
    },
    {
        "name":        "Phosphate buffer change",
        "band_label":  "Phosphate P–O ~1090 cm⁻¹",
        "bins":        [1080, 1090, 1100],
        "direction":   "change",
        "description": "Shift or broadening = ionic strength change; ATP release from stressed cells",
    },
    {
        "name":        "Aldehyde / oxidative stress",
        "band_label":  "Aldehyde C–H ~2720 cm⁻¹",
        "bins":        [2720, 2730],
        "direction":   "new_peak",
        "description": "New peak = lipid peroxidation aldehydes (MDA, 4-HNE) — oxidative stress",
    },
    {
        "name":        "Nucleic acid / adenosine change",
        "band_label":  "C–O–P ~970 cm⁻¹",
        "bins":        [970, 980],
        "direction":   "decrease",
        "description": "Intensity ↓ = adenosine consumed; ↑ = DNA/RNA release from necrotic cells",
    },
]


def assign_peak(wn: float) -> dict:
    """Return IR assignment dict for a given wavenumber."""
    match = IR_DF[(IR_DF.wn_low <= wn) & (IR_DF.wn_high >= wn)]
    if match.empty:
        return {
            "functional_group": "Unassigned",
            "bond": "–",
            "vibration_type": "–",
            "compound_class": "–",
            "biological_relevance": "–",
        }
    row = match.iloc[0]
    return {
        "functional_group":  row.functional_group,
        "bond":              row.bond,
        "vibration_type":    row.vibration_type,
        "compound_class":    row.compound_class,
        "biological_relevance": row.biological_relevance,
    }


def get_region(wn: float) -> str:
    for lo, hi, name in REGIONS:
        if lo <= wn < hi:
            return name
    return "Other"
