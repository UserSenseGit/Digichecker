const SYSTEM_PROMPT = `Je bent een logistiek en productie-assistent voor een atelier dat aluminium ramen en deuren maakt. Jouw taak is om foto's van papieren projectfiches om te zetten in een strakke, gefilterde lijst.
CRUCIALE REGELS:
1. Werk ALTIJD met een schone lei per gesprek.
2. Gebruik NOOIT selectievakjes-tekens zoals [ ] of - [ ] in je tekst.
3. Combineer het hoofdonderdeel, de aantallen, bestelbonnummers en leverdata (LD) op dezelfde regel achter elkaar tussen haakjes.
4. SUB-ITEMS TOEGESTAAN: Als er specifieke sub-onderdelen of details onder een hoofdcategorie staan, mag je deze op een nieuwe regel plaatsen beginnend met een streepje (-).
FILTER-LOGICA:
- De categorieën "Voorraadlijst" en "Elementen" moeten ALTIJD aanwezig zijn.
- Voor ALLE ANDERE categorieën: een schuine streep (/) betekent NIET van toepassing. Laat die categorie dan VOLLEDIG weg.
- STRIKTE GLAS-SCHEIDING: Mogelijke leveranciers: "Ceyssens", "AID" en "Mosa". Combineer ze nooit.
TITEL FORMAT STRIKT VEREIST:
P000000 - Naam van het project (exact dit format: P gevolgd door 6 cijfers, een spatie, koppelteken, spatie, en de naam).
OUTPUT FORMAT:
Geef het antwoord in exact deze twee blokken zonder extra tekst of markdown:
1. De Titel
[Hier de strikt geformatteerde titel]
2. De Items
[Zet hier de regels onder elkaar. Gebruik een '-' vooraan de regel voor sub-items. Plaats de titel NIET in deze lijst.]`;

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).end();

  // 1. Controleer of de gebruiker ingelogd is bij Firebase
  const token = (req.headers.authorization || "").replace("Bearer ", "");
  if (!token) return res.status(401).json({ error: "Niet ingelogd" });

  const check = await fetch(
    `https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=${process.env.FIREBASE_API_KEY}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ idToken: token }),
    }
  );
  if (!check.ok) return res.status(401).json({ error: "Ongeldige login" });

  // 2. Controleer de invoer
  const { images } = req.body || {};
  if (!Array.isArray(images) || images.length === 0 || images.length > 6) {
    return res.status(400).json({ error: "Ongeldige invoer" });
  }
  if (images.some((i) => typeof i !== "string" || i.length > 1_500_000)) {
    return res.status(400).json({ error: "Afbeelding te groot" });
  }

  // 3. Roep Gemini aan
  const payload = {
    systemInstruction: { parts: [{ text: SYSTEM_PROMPT }] },
    contents: [
      {
        role: "user",
        parts: [
          { text: "Verwerk deze projectfiche(s) en bouw de lijst. Vergeet de titel niet." },
          ...images.map((b64) => ({
            inlineData: { mimeType: "image/jpeg", data: b64.split(",")[1] },
          })),
        ],
      },
    ],
  };

  const r = await fetch(
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-goog-api-key": process.env.GEMINI_API_KEY,
      },
      body: JSON.stringify(payload),
    }
  );

  const data = await r.json();
  res.status(r.status).json(data);
}