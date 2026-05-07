"""
Phase 6 — Patient handout PDF generator.

Generates plain-language disease handouts in 4 languages for the 5 most
demo-relevant One Health diseases. Output: app/handouts/<disease>_<lang>.pdf

Languages:
  en  — English (real, written from CDC + ADHS plain-language disease pages)
  es  — Spanish (real translation by reviewer; AZ has 30%+ Spanish-speaking population)
  nv  — Diné Bizaad / Navajo (placeholder — pending tribal-IRB-vetted translator)
  apw — Ndee Biyáti' / Western Apache (placeholder — pending tribal-IRB-vetted translator)

Provenance & honesty:
  - English & Spanish handouts are written from public CDC and ADHS plain-language
    disease pages (https://www.cdc.gov/...; https://www.azdhs.gov/preparedness/...).
  - Diné and Apache versions are PLACEHOLDERS; LLM-generated medical content in
    these languages is unsafe without review by a fluent medical translator
    working under the relevant tribal IRB.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUT_DIR = Path(__file__).resolve().parents[2] / "app" / "handouts"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CARDINAL = colors.HexColor("#AB0520")
NAVY     = colors.HexColor("#0C234B")
INK1     = colors.HexColor("#1F2937")
INK2     = colors.HexColor("#374151")
INK3     = colors.HexColor("#6B7280")
AMBER    = colors.HexColor("#C5933E")
BG_ALT   = colors.HexColor("#F5F1E8")


# ----------------------------------------------------------------------
# Content — English + Spanish
# ----------------------------------------------------------------------
HANDOUTS = {
    # =====================================================================
    "valley_fever": {
        "en": {
            "title": "Valley Fever — What you need to know",
            "subtitle": "Coccidioidomycosis · A common Arizona desert lung infection",
            "what_is_it": (
                "Valley Fever is an infection caused by a fungus called <i>Coccidioides</i>. "
                "The fungus lives in dry desert soil, especially in southern Arizona. People "
                "and animals get Valley Fever by breathing in dust that contains the fungus's "
                "spores — usually after a windstorm, dust storm, or any activity that disturbs "
                "the soil (digging, construction, gardening, off-road driving)."
            ),
            "symptoms_title": "Symptoms",
            "symptoms": [
                "Cough that lasts more than two weeks",
                "Fever, often low-grade",
                "Tiredness that doesn't go away",
                "Chest pain or shortness of breath",
                "Headache",
                "Skin rash on the upper body or legs (sometimes)",
                "Joint pain, especially knees and ankles",
            ],
            "what_to_do_title": "What you should do",
            "what_to_do": [
                "Take all medications exactly as prescribed. Most people are treated with an antifungal pill called <b>fluconazole</b> for at least 3 to 6 months.",
                "Rest. Valley Fever is a slow infection. Even mild cases take weeks to recover from.",
                "Tell your doctor right away if symptoms worsen — especially if you have new headaches, stiff neck, weight loss, or weakness on one side of the body. These can be signs the infection has spread.",
                "Do not stop your medication early, even if you feel better. The infection can come back.",
                "Drink plenty of water and avoid alcohol while on antifungal medication.",
            ],
            "household_title": "If your dog or other pet was diagnosed first",
            "household": (
                "Valley Fever is <b>not contagious between people, or between pets and people</b>. "
                "But everyone in the household was likely exposed to the same dust. If your dog "
                "was diagnosed first, that does not mean the dog gave it to you — it means the "
                "soil around your home or yard had the fungus, and you all breathed it in. Tell "
                "your doctor about the household exposure; it helps make the diagnosis faster."
            ),
            "recovery_title": "Recovery",
            "recovery": (
                "Most healthy adults recover fully from Valley Fever, but it can take 6 months to "
                "a year. About 1 out of 200 people develops a more serious form that needs lifelong "
                "treatment. People with weakened immune systems, pregnant women, and people of "
                "African or Filipino descent are at higher risk for severe disease."
            ),
            "when_to_call": "Call 911 or go to the emergency room if you have:",
            "when_to_call_items": [
                "Severe difficulty breathing",
                "Chest pain that doesn't go away",
                "Confusion, severe headache, or stiff neck",
                "Weakness on one side of the body or trouble speaking",
            ],
            "resources_title": "More information",
            "resources": [
                "Arizona Department of Health Services Valley Fever Program: 602-364-3676",
                "CDC Valley Fever page: cdc.gov/fungal/diseases/coccidioidomycosis",
                "Valley Fever Center for Excellence (University of Arizona): vfce.arizona.edu",
            ],
        },
        "es": {
            "title": "Fiebre del Valle — Lo que necesita saber",
            "subtitle": "Coccidioidomicosis · Una infección pulmonar común del desierto de Arizona",
            "what_is_it": (
                "La Fiebre del Valle es una infección causada por un hongo llamado <i>Coccidioides</i>. "
                "El hongo vive en el suelo seco del desierto, especialmente en el sur de Arizona. Las "
                "personas y los animales contraen la Fiebre del Valle al respirar polvo que contiene "
                "las esporas del hongo — generalmente después de una tormenta de viento, una tormenta "
                "de polvo, o cualquier actividad que mueva la tierra (excavar, construir, trabajar en el "
                "jardín, manejar fuera del camino)."
            ),
            "symptoms_title": "Síntomas",
            "symptoms": [
                "Tos que dura más de dos semanas",
                "Fiebre, generalmente baja",
                "Cansancio que no desaparece",
                "Dolor de pecho o falta de aire",
                "Dolor de cabeza",
                "Sarpullido en el torso o las piernas (a veces)",
                "Dolor en las articulaciones, especialmente rodillas y tobillos",
            ],
            "what_to_do_title": "Qué debe hacer",
            "what_to_do": [
                "Tome todos los medicamentos exactamente como se los recetaron. La mayoría de las personas son tratadas con una pastilla antifúngica llamada <b>fluconazol</b> por al menos 3 a 6 meses.",
                "Descanse. La Fiebre del Valle es una infección de progresión lenta. Incluso los casos leves toman semanas en recuperarse.",
                "Avise a su médico inmediatamente si los síntomas empeoran — especialmente si tiene nuevos dolores de cabeza, rigidez en el cuello, pérdida de peso, o debilidad en un lado del cuerpo. Estas pueden ser señales de que la infección se ha extendido.",
                "No deje de tomar su medicamento antes de tiempo, aunque se sienta mejor. La infección puede regresar.",
                "Tome mucha agua y evite el alcohol mientras esté tomando el medicamento antifúngico.",
            ],
            "household_title": "Si su perro o mascota fue diagnosticado primero",
            "household": (
                "La Fiebre del Valle <b>no se contagia entre personas, ni entre mascotas y personas</b>. "
                "Pero todos en el hogar probablemente fueron expuestos al mismo polvo. Si su perro fue "
                "diagnosticado primero, no significa que el perro se la pasó a usted — significa que la "
                "tierra alrededor de su casa tenía el hongo, y todos lo respiraron. Avise a su médico "
                "sobre la exposición en el hogar; esto ayuda a hacer el diagnóstico más rápidamente."
            ),
            "recovery_title": "Recuperación",
            "recovery": (
                "La mayoría de los adultos sanos se recuperan completamente de la Fiebre del Valle, "
                "pero puede tomar de 6 meses a un año. Aproximadamente 1 de cada 200 personas desarrolla "
                "una forma más grave que requiere tratamiento de por vida. Las personas con sistema "
                "inmunológico debilitado, las mujeres embarazadas, y las personas de ascendencia africana "
                "o filipina tienen mayor riesgo de enfermedad grave."
            ),
            "when_to_call": "Llame al 911 o vaya a la sala de emergencia si tiene:",
            "when_to_call_items": [
                "Dificultad severa para respirar",
                "Dolor de pecho que no se quita",
                "Confusión, dolor de cabeza severo, o cuello rígido",
                "Debilidad en un lado del cuerpo o dificultad para hablar",
            ],
            "resources_title": "Más información",
            "resources": [
                "Programa de Fiebre del Valle del Departamento de Salud de Arizona: 602-364-3676",
                "Página de Fiebre del Valle del CDC: cdc.gov/fungal/diseases/coccidioidomycosis",
                "Centro de Excelencia para la Fiebre del Valle (Universidad de Arizona): vfce.arizona.edu",
            ],
        },
    },

    # =====================================================================
    "rmsf": {
        "en": {
            "title": "Rocky Mountain Spotted Fever — What you need to know",
            "subtitle": "A serious tick-borne infection that needs early treatment",
            "what_is_it": (
                "Rocky Mountain Spotted Fever (RMSF) is a serious infection spread by ticks. In "
                "Arizona, the tick that carries it is the brown dog tick, which can live in and "
                "around homes where dogs are kept outdoors. RMSF can become life-threatening "
                "within a week of symptoms starting, so <b>early treatment is critical</b>."
            ),
            "symptoms_title": "Symptoms",
            "symptoms": [
                "High fever (often above 102°F)",
                "Severe headache",
                "Muscle pain",
                "Vomiting and stomach pain",
                "A rash that often starts on wrists, ankles, palms, and soles, then spreads",
                "Confusion in severe cases",
            ],
            "what_to_do_title": "What you should do",
            "what_to_do": [
                "Take <b>doxycycline</b> exactly as prescribed. Even children should be treated with doxycycline for RMSF — it is the only antibiotic that is reliably effective and the benefits far outweigh the risk of tooth staining at the doses used.",
                "Do not wait for blood test results to start treatment. Your doctor will start treatment based on symptoms because RMSF can be fatal if treated late.",
                "Watch all household members closely for fever or rash for the next 14 days.",
                "Treat all dogs in the household with a tick preventive recommended by your veterinarian. Dogs are the source of the ticks that bite people.",
                "Inspect your home and yard for ticks; remove any tick-attractive habitat (piles of debris, dog houses with cracks).",
            ],
            "household_title": "If your dog was diagnosed first",
            "household": (
                "RMSF is <b>not contagious between people, or directly between pets and people</b>. "
                "But the same ticks that bit your dog can bite the humans in the household. If your "
                "dog was diagnosed with RMSF (or any tick-borne disease), every human in the home "
                "should be checked for tick attachment, and every animal in the home should be "
                "treated with a vet-recommended tick preventive. The household needs to be treated "
                "as a unit."
            ),
            "recovery_title": "Recovery",
            "recovery": (
                "If treatment is started within 5 days of symptoms beginning, most people recover "
                "fully. Untreated, RMSF has a death rate of about 30%. This is why your doctor will "
                "treat you immediately based on symptoms even before lab confirmation."
            ),
            "when_to_call": "Call your doctor or go to the emergency room if you have:",
            "when_to_call_items": [
                "Fever after a known tick bite — at any time within the last 30 days",
                "Confusion, severe headache, or stiff neck",
                "A spreading rash, especially with fever",
                "Severe vomiting that prevents you from keeping medication down",
            ],
            "resources_title": "More information",
            "resources": [
                "Arizona Department of Health Services: 602-364-4562",
                "CDC RMSF page: cdc.gov/rmsf",
                "Tick-borne disease prevention: cdc.gov/ticks",
            ],
        },
        "es": {
            "title": "Fiebre Manchada de las Montañas Rocosas",
            "subtitle": "Una infección grave transmitida por garrapatas que requiere tratamiento temprano",
            "what_is_it": (
                "La Fiebre Manchada de las Montañas Rocosas (RMSF) es una infección grave transmitida "
                "por garrapatas. En Arizona, la garrapata que la transmite es la garrapata marrón del "
                "perro, que puede vivir dentro y alrededor de casas donde se tienen perros al aire libre. "
                "La RMSF puede volverse mortal dentro de una semana después de que comienzan los "
                "síntomas, por lo que <b>el tratamiento temprano es crítico</b>."
            ),
            "symptoms_title": "Síntomas",
            "symptoms": [
                "Fiebre alta (frecuentemente más de 102°F / 39°C)",
                "Dolor de cabeza severo",
                "Dolor muscular",
                "Vómitos y dolor de estómago",
                "Sarpullido que a menudo comienza en muñecas, tobillos, palmas, y plantas, y se extiende",
                "Confusión en casos graves",
            ],
            "what_to_do_title": "Qué debe hacer",
            "what_to_do": [
                "Tome <b>doxiciclina</b> exactamente como se la recetaron. Incluso los niños deben ser tratados con doxiciclina para la RMSF — es el único antibiótico confiablemente eficaz y los beneficios superan ampliamente el riesgo de manchas en los dientes a las dosis utilizadas.",
                "No espere los resultados de los análisis de sangre para comenzar el tratamiento. Su médico comenzará el tratamiento basado en los síntomas porque la RMSF puede ser mortal si se trata tarde.",
                "Observe a todos los miembros del hogar cuidadosamente para detectar fiebre o sarpullido durante los próximos 14 días.",
                "Trate a todos los perros del hogar con un preventivo de garrapatas recomendado por su veterinario. Los perros son la fuente de las garrapatas que pican a las personas.",
                "Inspeccione su hogar y patio en busca de garrapatas; elimine cualquier hábitat que las atraiga (montones de escombros, casas para perros con grietas).",
            ],
            "household_title": "Si su perro fue diagnosticado primero",
            "household": (
                "La RMSF <b>no se contagia entre personas, ni directamente entre mascotas y personas</b>. "
                "Pero las mismas garrapatas que picaron a su perro pueden picar a los humanos del hogar. "
                "Si su perro fue diagnosticado con RMSF (o cualquier enfermedad transmitida por "
                "garrapatas), cada humano en el hogar debe ser examinado para detectar garrapatas "
                "adheridas, y cada animal en el hogar debe ser tratado con un preventivo recomendado "
                "por el veterinario. El hogar debe tratarse como una unidad."
            ),
            "recovery_title": "Recuperación",
            "recovery": (
                "Si el tratamiento comienza dentro de los 5 días de iniciarse los síntomas, la mayoría "
                "de las personas se recuperan completamente. Sin tratamiento, la RMSF tiene una tasa de "
                "mortalidad de aproximadamente 30%. Por esto su médico lo tratará inmediatamente basado "
                "en los síntomas, antes de la confirmación de laboratorio."
            ),
            "when_to_call": "Llame a su médico o vaya a la sala de emergencia si tiene:",
            "when_to_call_items": [
                "Fiebre después de una picadura conocida de garrapata — en cualquier momento dentro de los últimos 30 días",
                "Confusión, dolor de cabeza severo, o cuello rígido",
                "Sarpullido que se extiende, especialmente con fiebre",
                "Vómitos severos que no le permiten retener el medicamento",
            ],
            "resources_title": "Más información",
            "resources": [
                "Departamento de Salud de Arizona: 602-364-4562",
                "Página de RMSF del CDC: cdc.gov/rmsf",
                "Prevención de enfermedades transmitidas por garrapatas: cdc.gov/ticks",
            ],
        },
    },

    # =====================================================================
    "plague": {
        "en": {
            "title": "Plague — What you need to know",
            "subtitle": "A bacterial infection from infected rodents and their fleas — treatable when caught early",
            "what_is_it": (
                "Plague is a bacterial infection (<i>Yersinia pestis</i>) that lives in wild rodents — "
                "in Arizona, especially prairie dogs, ground squirrels, and chipmunks in the northern "
                "part of the state (Coconino, Apache, and Navajo counties). It can spread to humans "
                "and pets through infected fleas, by handling sick or dead animals, or rarely through "
                "respiratory droplets from sick cats. <b>Plague is fully treatable with antibiotics if "
                "caught early — but is rapidly fatal if not treated.</b>"
            ),
            "symptoms_title": "Symptoms",
            "symptoms": [
                "Sudden high fever and chills",
                "Severe headache",
                "Painful, swollen lymph nodes (called 'buboes') in the groin, armpit, or neck",
                "Extreme weakness",
                "Cough with bloody sputum (in pneumonic plague — rare but dangerous)",
            ],
            "what_to_do_title": "What you should do",
            "what_to_do": [
                "Get to a doctor or emergency room immediately. Time matters.",
                "Take antibiotics exactly as prescribed — usually streptomycin, gentamicin, or doxycycline for at least 10 days.",
                "If you have pneumonic plague (cough with bloody sputum), follow isolation precautions until you have been on antibiotics for at least 48 hours.",
                "Treat all pets in the household for fleas. Cats are particularly susceptible to plague and can give it to humans.",
                "Avoid contact with wild rodents or rodent burrows. Do not let pets hunt prairie dogs or ground squirrels.",
            ],
            "household_title": "If your cat was diagnosed first",
            "household": (
                "Cats with plague can transmit the infection to humans through respiratory droplets, "
                "particularly to veterinarians and family members caring for the sick cat. <b>If your "
                "cat was diagnosed with plague, contact your doctor right away — even before you have "
                "symptoms.</b> Your doctor may give you preventive antibiotics. Veterinarians and "
                "household contacts of cats with plague have been documented sources of human cases."
            ),
            "recovery_title": "Recovery",
            "recovery": (
                "With prompt antibiotic treatment, most people recover fully. Untreated plague has "
                "a 30–60% death rate. The earlier antibiotics start, the better the outcome."
            ),
            "when_to_call": "Call 911 immediately if you have:",
            "when_to_call_items": [
                "Sudden severe fever after exposure to wild rodents or sick pets",
                "Painful swollen lump in groin, armpit, or neck with fever",
                "Coughing up blood",
                "A pet (especially a cat) that died unexpectedly with fever",
            ],
            "resources_title": "More information",
            "resources": [
                "Arizona Department of Health Services Vector-borne Disease Program: 602-364-4562",
                "CDC Plague page: cdc.gov/plague",
                "Coconino County Health Department: 928-679-7272",
            ],
        },
        "es": {
            "title": "Peste — Lo que necesita saber",
            "subtitle": "Una infección bacteriana de roedores infectados y sus pulgas — tratable cuando se detecta temprano",
            "what_is_it": (
                "La peste es una infección bacteriana (<i>Yersinia pestis</i>) que vive en roedores "
                "silvestres — en Arizona, especialmente perros de las praderas, ardillas terrestres, y "
                "tamias en el norte del estado (condados de Coconino, Apache, y Navajo). Puede "
                "transmitirse a humanos y mascotas a través de pulgas infectadas, al manejar animales "
                "enfermos o muertos, o raramente a través de gotitas respiratorias de gatos enfermos. "
                "<b>La peste es completamente tratable con antibióticos si se detecta temprano — pero "
                "es rápidamente mortal si no se trata.</b>"
            ),
            "symptoms_title": "Síntomas",
            "symptoms": [
                "Fiebre alta repentina y escalofríos",
                "Dolor de cabeza severo",
                "Ganglios linfáticos hinchados y dolorosos (llamados 'bubones') en la ingle, axila, o cuello",
                "Debilidad extrema",
                "Tos con esputo con sangre (en peste neumónica — rara pero peligrosa)",
            ],
            "what_to_do_title": "Qué debe hacer",
            "what_to_do": [
                "Vaya a un médico o sala de emergencia inmediatamente. El tiempo es crítico.",
                "Tome los antibióticos exactamente como se los recetaron — generalmente estreptomicina, gentamicina, o doxiciclina por al menos 10 días.",
                "Si tiene peste neumónica (tos con esputo con sangre), siga las precauciones de aislamiento hasta que haya tomado antibióticos por al menos 48 horas.",
                "Trate a todas las mascotas del hogar contra pulgas. Los gatos son particularmente susceptibles a la peste y pueden contagiársela a los humanos.",
                "Evite el contacto con roedores silvestres o sus madrigueras. No deje que sus mascotas cacen perros de las praderas o ardillas.",
            ],
            "household_title": "Si su gato fue diagnosticado primero",
            "household": (
                "Los gatos con peste pueden transmitir la infección a humanos a través de gotitas "
                "respiratorias, particularmente a veterinarios y miembros de la familia que cuidan al "
                "gato enfermo. <b>Si su gato fue diagnosticado con peste, contacte a su médico "
                "inmediatamente — incluso antes de tener síntomas.</b> Su médico puede darle "
                "antibióticos preventivos. Los veterinarios y contactos del hogar de gatos con peste "
                "han sido fuentes documentadas de casos humanos."
            ),
            "recovery_title": "Recuperación",
            "recovery": (
                "Con tratamiento antibiótico oportuno, la mayoría de las personas se recuperan "
                "completamente. La peste no tratada tiene una tasa de mortalidad de 30–60%. Mientras "
                "más temprano comiencen los antibióticos, mejor el resultado."
            ),
            "when_to_call": "Llame al 911 inmediatamente si tiene:",
            "when_to_call_items": [
                "Fiebre alta repentina después de exposición a roedores silvestres o mascotas enfermas",
                "Bulto hinchado y doloroso en la ingle, axila, o cuello con fiebre",
                "Tos con sangre",
                "Una mascota (especialmente un gato) que murió inesperadamente con fiebre",
            ],
            "resources_title": "Más información",
            "resources": [
                "Programa de Enfermedades Transmitidas por Vectores del Departamento de Salud de Arizona: 602-364-4562",
                "Página de Peste del CDC: cdc.gov/plague",
                "Departamento de Salud del Condado Coconino: 928-679-7272",
            ],
        },
    },

    # =====================================================================
    "west_nile": {
        "en": {
            "title": "West Nile Virus — What you need to know",
            "subtitle": "A mosquito-borne virus most active in Arizona during late summer and fall",
            "what_is_it": (
                "West Nile virus is spread by mosquitoes that have fed on infected birds. Most "
                "people who get infected (about 80%) have no symptoms at all. About 1 in 5 develop "
                "a flu-like illness called West Nile fever. About 1 in 150 develops a serious illness "
                "affecting the brain or spinal cord (West Nile neuroinvasive disease)."
            ),
            "symptoms_title": "Symptoms",
            "symptoms": [
                "Fever and chills",
                "Headache and body aches",
                "Tiredness and weakness",
                "Joint pains",
                "Nausea or vomiting",
                "A fine red rash on the chest, stomach, and back (sometimes)",
                "Severe: stiff neck, confusion, tremors, weakness on one side, seizures",
            ],
            "what_to_do_title": "What you should do",
            "what_to_do": [
                "Rest and drink plenty of fluids. There is no specific antiviral medication for West Nile virus; treatment is supportive.",
                "Take over-the-counter pain and fever medications as needed.",
                "Watch for severe symptoms — stiff neck, confusion, weakness on one side of the body. Go to the ER right away if these develop.",
                "Drain standing water around your home where mosquitoes breed (flowerpot saucers, gutters, pool covers, buckets).",
                "Use EPA-registered insect repellent containing DEET, picaridin, or oil of lemon eucalyptus during dawn and dusk.",
            ],
            "household_title": "If a horse on your property was diagnosed first",
            "household": (
                "West Nile virus is <b>not directly contagious from horses to humans</b> — both species "
                "get the virus from mosquito bites. But a confirmed equine West Nile case means "
                "infected mosquitoes are active in your area, and humans on the property are at risk. "
                "Take mosquito protection seriously: drain standing water, use repellent, avoid being "
                "outdoors at dawn and dusk."
            ),
            "recovery_title": "Recovery",
            "recovery": (
                "Most people with West Nile fever recover fully within a few weeks, though tiredness "
                "and weakness can last months. People who develop the neuroinvasive form may have "
                "long-lasting weakness, memory problems, or seizures. People over 60 and those with "
                "weakened immune systems are at higher risk."
            ),
            "when_to_call": "Go to the emergency room if you have:",
            "when_to_call_items": [
                "Severe headache with stiff neck",
                "Confusion or unusual sleepiness",
                "Weakness on one side of the body or trouble walking",
                "Seizure",
                "Tremors or muscle twitching with fever",
            ],
            "resources_title": "More information",
            "resources": [
                "Arizona Department of Health Services Vector-borne Disease Program: 602-364-4562",
                "CDC West Nile Virus page: cdc.gov/westnile",
                "Maricopa County Vector Control: 602-506-0700",
            ],
        },
        "es": {
            "title": "Virus del Nilo Occidental",
            "subtitle": "Un virus transmitido por mosquitos, más activo en Arizona durante el verano tardío y otoño",
            "what_is_it": (
                "El virus del Nilo Occidental es transmitido por mosquitos que se han alimentado de "
                "aves infectadas. La mayoría de las personas que se infectan (aproximadamente 80%) no "
                "tienen síntomas. Aproximadamente 1 de cada 5 desarrolla una enfermedad similar a la "
                "gripe llamada fiebre del Nilo Occidental. Aproximadamente 1 de cada 150 desarrolla "
                "una enfermedad grave que afecta el cerebro o la médula espinal."
            ),
            "symptoms_title": "Síntomas",
            "symptoms": [
                "Fiebre y escalofríos",
                "Dolor de cabeza y dolores corporales",
                "Cansancio y debilidad",
                "Dolor en las articulaciones",
                "Náuseas o vómitos",
                "Sarpullido fino y rojo en pecho, estómago, y espalda (a veces)",
                "Grave: cuello rígido, confusión, temblores, debilidad de un lado, convulsiones",
            ],
            "what_to_do_title": "Qué debe hacer",
            "what_to_do": [
                "Descanse y tome muchos líquidos. No hay medicamento antiviral específico para el virus del Nilo Occidental; el tratamiento es de apoyo.",
                "Tome medicamentos de venta libre para dolor y fiebre según sea necesario.",
                "Esté atento a síntomas graves — cuello rígido, confusión, debilidad en un lado del cuerpo. Vaya a emergencias inmediatamente si estos aparecen.",
                "Drene el agua estancada alrededor de su hogar donde se reproducen los mosquitos (platos de macetas, canaletas, cubiertas de piscinas, cubetas).",
                "Use repelente de insectos registrado por la EPA con DEET, picaridina, o aceite de eucalipto limón durante el amanecer y atardecer.",
            ],
            "household_title": "Si un caballo en su propiedad fue diagnosticado primero",
            "household": (
                "El virus del Nilo Occidental <b>no se contagia directamente de caballos a humanos</b> — "
                "ambas especies contraen el virus por picaduras de mosquitos. Pero un caso equino "
                "confirmado significa que mosquitos infectados están activos en su área, y los humanos "
                "en la propiedad están en riesgo. Tome la protección contra mosquitos en serio: drene "
                "el agua estancada, use repelente, evite estar al aire libre al amanecer y atardecer."
            ),
            "recovery_title": "Recuperación",
            "recovery": (
                "La mayoría de las personas con fiebre del Nilo Occidental se recuperan completamente "
                "en unas pocas semanas, aunque el cansancio y la debilidad pueden durar meses. Las "
                "personas que desarrollan la forma neuroinvasiva pueden tener debilidad prolongada, "
                "problemas de memoria, o convulsiones. Las personas mayores de 60 años y aquellas con "
                "sistema inmunológico debilitado tienen mayor riesgo."
            ),
            "when_to_call": "Vaya a la sala de emergencia si tiene:",
            "when_to_call_items": [
                "Dolor de cabeza severo con cuello rígido",
                "Confusión o somnolencia inusual",
                "Debilidad en un lado del cuerpo o dificultad para caminar",
                "Convulsión",
                "Temblores o espasmos musculares con fiebre",
            ],
            "resources_title": "Más información",
            "resources": [
                "Programa de Enfermedades Transmitidas por Vectores de Arizona: 602-364-4562",
                "Página del Virus del Nilo Occidental del CDC: cdc.gov/westnile",
                "Control de Vectores del Condado Maricopa: 602-506-0700",
            ],
        },
    },

    # =====================================================================
    "ehrlichiosis": {
        "en": {
            "title": "Ehrlichiosis — What you need to know",
            "subtitle": "A tick-borne infection that responds well to early treatment",
            "what_is_it": (
                "Ehrlichiosis is a bacterial infection spread by ticks. In Arizona, dogs are the most "
                "common reservoir, and the brown dog tick is the main vector. Like Rocky Mountain "
                "Spotted Fever, ehrlichiosis can become serious if not treated quickly, and treatment "
                "is started based on symptoms even before lab confirmation."
            ),
            "symptoms_title": "Symptoms",
            "symptoms": [
                "Fever and chills",
                "Severe headache",
                "Muscle aches",
                "Nausea or vomiting",
                "Tiredness",
                "Sometimes a rash (less common than in RMSF)",
            ],
            "what_to_do_title": "What you should do",
            "what_to_do": [
                "Take <b>doxycycline</b> as prescribed for 7 to 14 days, even if you feel better quickly.",
                "Tell anyone in your household who develops fever in the next 14 days that they were exposed and need to see a doctor.",
                "Treat all dogs in the household for ticks with a vet-recommended preventive.",
                "Inspect your home and yard for ticks. Brown dog ticks live in cracks, dog houses, and bedding.",
            ],
            "household_title": "If your dog was diagnosed first",
            "household": (
                "Ehrlichiosis is not contagious between people or directly between pets and people, "
                "but everyone in the household is exposed to the same ticks. If your dog was "
                "diagnosed with ehrlichiosis, watch yourself and other family members for symptoms "
                "for the next 14 days, treat all pets with tick preventive, and clean tick habitat "
                "from the home and yard."
            ),
            "recovery_title": "Recovery",
            "recovery": (
                "With early treatment, most people recover fully within 1 to 2 weeks. Severe disease "
                "is uncommon when treatment starts within the first 5 days of symptoms."
            ),
            "when_to_call": "Call your doctor if you have:",
            "when_to_call_items": [
                "Fever after a tick bite or after a household pet is diagnosed with a tick-borne disease",
                "Severe headache or stiff neck",
                "Inability to keep medications down due to vomiting",
            ],
            "resources_title": "More information",
            "resources": [
                "Arizona Department of Health Services: 602-364-4562",
                "CDC Ehrlichiosis page: cdc.gov/ehrlichiosis",
            ],
        },
        "es": {
            "title": "Ehrlichiosis — Lo que necesita saber",
            "subtitle": "Una infección transmitida por garrapatas que responde bien al tratamiento temprano",
            "what_is_it": (
                "La ehrlichiosis es una infección bacteriana transmitida por garrapatas. En Arizona, "
                "los perros son el reservorio más común, y la garrapata marrón del perro es el "
                "vector principal. Como la Fiebre Manchada, la ehrlichiosis puede volverse grave si "
                "no se trata rápidamente, y el tratamiento comienza basado en síntomas incluso antes "
                "de la confirmación de laboratorio."
            ),
            "symptoms_title": "Síntomas",
            "symptoms": [
                "Fiebre y escalofríos",
                "Dolor de cabeza severo",
                "Dolores musculares",
                "Náuseas o vómitos",
                "Cansancio",
                "A veces sarpullido (menos común que en RMSF)",
            ],
            "what_to_do_title": "Qué debe hacer",
            "what_to_do": [
                "Tome <b>doxiciclina</b> como se la recetaron por 7 a 14 días, aunque se sienta mejor rápidamente.",
                "Avise a cualquier persona en el hogar que desarrolle fiebre en los próximos 14 días que estuvo expuesta y necesita ver a un médico.",
                "Trate a todos los perros del hogar contra garrapatas con un preventivo recomendado por el veterinario.",
                "Inspeccione su hogar y patio en busca de garrapatas. Las garrapatas marrones del perro viven en grietas, casas de perros, y camas.",
            ],
            "household_title": "Si su perro fue diagnosticado primero",
            "household": (
                "La ehrlichiosis no se contagia entre personas ni directamente entre mascotas y "
                "personas, pero todos en el hogar están expuestos a las mismas garrapatas. Si su perro "
                "fue diagnosticado con ehrlichiosis, observe a usted y otros miembros de la familia "
                "para detectar síntomas durante los próximos 14 días, trate a todas las mascotas con "
                "preventivo de garrapatas, y limpie el hábitat de garrapatas del hogar y patio."
            ),
            "recovery_title": "Recuperación",
            "recovery": (
                "Con tratamiento temprano, la mayoría de las personas se recuperan completamente en 1 "
                "a 2 semanas. La enfermedad grave es poco común cuando el tratamiento comienza dentro "
                "de los primeros 5 días de síntomas."
            ),
            "when_to_call": "Llame a su médico si tiene:",
            "when_to_call_items": [
                "Fiebre después de una picadura de garrapata o después de que una mascota del hogar es diagnosticada con una enfermedad transmitida por garrapatas",
                "Dolor de cabeza severo o cuello rígido",
                "Imposibilidad de retener medicamentos debido a vómitos",
            ],
            "resources_title": "Más información",
            "resources": [
                "Departamento de Salud de Arizona: 602-364-4562",
                "Página de Ehrlichiosis del CDC: cdc.gov/ehrlichiosis",
            ],
        },
    },
}


def _build_styles():
    """Build the paragraph styles for the handout."""
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "Title", parent=base["Title"], fontName="Helvetica-Bold",
            fontSize=22, leading=26, textColor=NAVY, alignment=TA_LEFT,
            spaceAfter=4
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"], fontName="Helvetica-Oblique",
            fontSize=12, leading=14, textColor=INK3, spaceAfter=14
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontName="Helvetica-Bold",
            fontSize=13, leading=16, textColor=CARDINAL, spaceBefore=12, spaceAfter=6
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"], fontName="Helvetica",
            fontSize=11, leading=15.5, textColor=INK1, spaceAfter=8
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["Normal"], fontName="Helvetica",
            fontSize=11, leading=15, textColor=INK1, leftIndent=18, bulletIndent=8,
            spaceAfter=4
        ),
        "callout_h": ParagraphStyle(
            "CalloutH", parent=base["Heading3"], fontName="Helvetica-Bold",
            fontSize=12, leading=14, textColor=CARDINAL, spaceAfter=4
        ),
        "callout": ParagraphStyle(
            "Callout", parent=base["Normal"], fontName="Helvetica",
            fontSize=10.5, leading=14, textColor=INK1, spaceAfter=6
        ),
        "footer": ParagraphStyle(
            "Footer", parent=base["Normal"], fontName="Helvetica-Oblique",
            fontSize=8.5, leading=11, textColor=INK3, spaceBefore=14, alignment=TA_LEFT
        ),
    }
    return styles


def render_handout(disease_id: str, lang: str, content: dict, out_path: Path):
    """Render one handout PDF."""
    styles = _build_styles()
    doc = SimpleDocTemplate(
        str(out_path), pagesize=LETTER,
        leftMargin=0.85*inch, rightMargin=0.85*inch,
        topMargin=0.7*inch, bottomMargin=0.7*inch,
        title=content["title"], author="ONE-HealthRecord (synthetic demo)"
    )
    story = []

    # Header band
    header_table = Table(
        [["ONE-HealthRecord · Patient handout", f"Issued {datetime.now().strftime('%Y-%m-%d')}"]],
        colWidths=[5.0*inch, 1.8*inch]
    )
    header_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK3),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.6, CARDINAL),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 12))

    # Title + subtitle
    story.append(Paragraph(content["title"], styles["title"]))
    story.append(Paragraph(content["subtitle"], styles["subtitle"]))

    # What is it
    story.append(Paragraph(content["what_is_it"], styles["body"]))

    # Symptoms
    story.append(Paragraph(content["symptoms_title"], styles["h2"]))
    for s in content["symptoms"]:
        story.append(Paragraph(s, styles["bullet"], bulletText="•"))
    story.append(Spacer(1, 4))

    # What to do
    story.append(Paragraph(content["what_to_do_title"], styles["h2"]))
    for i, item in enumerate(content["what_to_do"], 1):
        story.append(Paragraph(item, styles["bullet"], bulletText=f"{i}."))
    story.append(Spacer(1, 4))

    # Household callout
    callout = Table(
        [[Paragraph(content["household_title"], styles["callout_h"])],
         [Paragraph(content["household"], styles["callout"])]],
        colWidths=[6.8*inch]
    )
    callout.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_ALT),
        ("BOX", (0, 0), (-1, -1), 0.5, AMBER),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBEFORE", (0, 0), (0, -1), 3, AMBER),
    ]))
    story.append(KeepTogether(callout))
    story.append(Spacer(1, 14))

    # Recovery
    story.append(Paragraph(content["recovery_title"], styles["h2"]))
    story.append(Paragraph(content["recovery"], styles["body"]))

    # When to call (red urgent box)
    urgent = [[Paragraph(content["when_to_call"], styles["callout_h"])]]
    for item in content["when_to_call_items"]:
        urgent.append([Paragraph("• " + item, styles["callout"])])
    urgent_table = Table(urgent, colWidths=[6.8*inch])
    urgent_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FBEAEC")),
        ("BOX", (0, 0), (-1, -1), 0.5, CARDINAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBEFORE", (0, 0), (0, -1), 3, CARDINAL),
    ]))
    story.append(KeepTogether(urgent_table))
    story.append(Spacer(1, 14))

    # Resources
    story.append(Paragraph(content["resources_title"], styles["h2"]))
    for r in content["resources"]:
        story.append(Paragraph(r, styles["bullet"], bulletText="•"))

    # Footer / provenance
    story.append(Paragraph(
        "ONE-HealthRecord MVP · Synthetic demonstration · "
        "Content drawn from public CDC and Arizona Department of Health Services plain-language disease pages. "
        "This handout is informational and does not replace medical advice from your clinician.",
        styles["footer"]
    ))

    doc.build(story)


def render_pending_placeholder(disease_id: str, lang_code: str, lang_label_native: str,
                                lang_label_en: str, disease_label_en: str, out_path: Path):
    """For Diné and Western Apache: render a clear placeholder."""
    styles = _build_styles()
    doc = SimpleDocTemplate(
        str(out_path), pagesize=LETTER,
        leftMargin=0.85*inch, rightMargin=0.85*inch,
        topMargin=0.7*inch, bottomMargin=0.7*inch,
        title=f"{disease_label_en} — translation pending",
        author="ONE-HealthRecord (synthetic demo)"
    )
    story = []

    header_table = Table([
        ["ONE-HealthRecord · Patient handout", f"Issued {datetime.now().strftime('%Y-%m-%d')}"]
    ], colWidths=[5.0*inch, 1.8*inch])
    header_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK3),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 0.6, CARDINAL),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 24))

    story.append(Paragraph(disease_label_en, styles["title"]))
    story.append(Paragraph(f"{lang_label_native} ({lang_label_en}) translation — pending tribal-IRB-vetted translator",
                           styles["subtitle"]))
    story.append(Spacer(1, 24))

    warning_text = (
        "<b>TRANSLATION PENDING — DO NOT DISTRIBUTE.</b><br/><br/>"
        f"This handout template requires review and translation by a {lang_label_native} "
        f"({lang_label_en})-fluent medical translator working under the relevant tribal IRB before it "
        "is provided to a patient.<br/><br/>"
        f"The English-language source content for this handout exists in this repository "
        f"(<font face='Courier'>handouts/{disease_id}_en.pdf</font>) and may be used as the source "
        f"text for a translator commissioned through:"
    )
    warning_table = Table(
        [[Paragraph(warning_text, styles["callout"])]],
        colWidths=[6.8*inch]
    )
    warning_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FBEAEC")),
        ("BOX", (0, 0), (-1, -1), 0.7, CARDINAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("RIGHTPADDING", (0, 0), (-1, -1), 16),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LINEBEFORE", (0, 0), (0, -1), 4, CARDINAL),
    ]))
    story.append(warning_table)
    story.append(Spacer(1, 14))

    if lang_code == "nv":
        contacts = [
            "• Navajo Nation Department of Health, Office of Communications & Health Education",
            "• Diné College Center for Diné Studies — medical translation services",
            "• Navajo Area IHS Office of Public Health Support",
        ]
    else:
        contacts = [
            "• San Carlos Apache Healthcare Corporation — community outreach",
            "• White Mountain Apache Tribal Public Health",
            "• Arizona State University Center for Indian Country Development — translation review network",
        ]
    for c in contacts:
        story.append(Paragraph(c, styles["bullet"], bulletText=" "))

    story.append(Spacer(1, 18))
    story.append(Paragraph(
        "<b>Why this matters.</b> Distributing machine-generated medical content in Indigenous "
        "languages without fluent medical-translator review carries a real risk of clinical harm "
        "and a real risk of cultural disrespect. The architecture supports the language; the "
        "process for filling the slot is itself the work.",
        styles["body"]
    ))

    story.append(Paragraph(
        "ONE-HealthRecord MVP · Synthetic demonstration · This placeholder is a feature, not a gap.",
        styles["footer"]
    ))

    doc.build(story)


def main():
    # Real handouts in English + Spanish
    for did, langs in HANDOUTS.items():
        for lang in ("en", "es"):
            content = langs[lang]
            out_path = OUT_DIR / f"{did}_{lang}.pdf"
            render_handout(did, lang, content, out_path)
            print(f"  wrote {out_path.name}  ({out_path.stat().st_size} bytes)")

    # Placeholder handouts in Diné and Apache for the same diseases
    pending = [
        ("nv",  "Diné Bizaad",   "Navajo"),
        ("apw", "Ndee Biyáti'",  "Western Apache"),
    ]
    disease_labels_en = {
        "valley_fever":  "Valley Fever (Coccidioidomycosis)",
        "rmsf":          "Rocky Mountain Spotted Fever",
        "plague":        "Plague (Yersinia pestis)",
        "west_nile":     "West Nile Virus",
        "ehrlichiosis":  "Ehrlichiosis",
    }
    for did in HANDOUTS.keys():
        for lang_code, native, english in pending:
            out_path = OUT_DIR / f"{did}_{lang_code}.pdf"
            render_pending_placeholder(
                did, lang_code, native, english,
                disease_labels_en[did], out_path
            )
            print(f"  wrote {out_path.name}  (pending placeholder)")


if __name__ == "__main__":
    main()
