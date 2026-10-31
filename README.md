# Zählerstand per Foto – Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz)
[![Validate](https://github.com/GITHUB_USER/ha-zaehlerstand/actions/workflows/validate.yml/badge.svg)](https://github.com/GITHUB_USER/ha-zaehlerstand/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/GITHUB_USER/ha-zaehlerstand)](https://github.com/GITHUB_USER/ha-zaehlerstand/releases)

Fotografiere deinen Strom-, Gas- oder Wasserzähler. Eine KI liest den Stand ab und
speichert ihn in einer Sensor-Entität, die du auch im **Energie-Dashboard** nutzen kannst.

## Was du pro Zähler bekommst

| Entität | Typ | Inhalt |
|---|---|---|
| `sensor.<name>_zahlerstand` | Sensor | Zählerstand (kWh bzw. m³), `total_increasing`, übersteht Neustarts |
| `text.<name>_zahlernummer` | Text | Zählernummer, im Dashboard editierbar und dauerhaft gespeichert |
| `image.<name>_letztes_foto` | Bild | Foto der letzten Ablesung |

Der Sensor hat zusätzlich diese Attribute: `letzte_ablesung`, `quelle`, `foto`,
`erkannte_zaehlernummer`, `zaehlernummer_passt`.

**Abgleich der Zählernummer:** Die KI liest auch die aufgedruckte Zählernummer.
- Ist noch keine Nummer gespeichert, wird die erkannte Nummer übernommen.
- Weicht sie von der gespeicherten ab, ist `zaehlernummer_passt: false` und im Log
  erscheint eine Warnung. So merkst du, wenn du das Foto dem falschen Zähler zugeordnet hast.

**Plausibilitätsprüfung:** Ist der neue Wert kleiner als der bisherige, wird er abgelehnt.
Nach einem Zählerwechsel rufst du den Dienst mit `erzwingen: true` auf. Alternativ kannst du
in den Optionen „Sinkenden Zählerstand erlauben“ einschalten.

## Voraussetzungen

- Home Assistant **2025.8 oder neuer** (AI-Task-Funktion; getestet gegen den Code von 2026.x)
- Eine KI-Integration mit **AI Task** und Bildunterstützung, z. B. OpenAI, Google Generative AI,
  Anthropic oder Ollama mit einem Vision-Modell.
- Entweder stellst du in **Einstellungen → System → Allgemein → AI Task** eine Standard-Entität ein
  oder du wählst die Entität bei der Einrichtung des Zählers aus.

> Datenschutz: Mit einem Cloud-Anbieter wird das Foto an diesen Anbieter geschickt.
> Willst du das vermeiden, nutze Ollama lokal mit einem Vision-Modell (z. B. `qwen2.5vl`,
> `llama3.2-vision` oder `gemma3`).

## Installation

### Über HACS (empfohlen)

[![In HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=GITHUB_USER&repository=ha-zaehlerstand&category=integration)

Oder von Hand:
1. Öffne in HACS ⋮ → **Benutzerdefinierte Repositories**.
2. Trage `https://github.com/GITHUB_USER/ha-zaehlerstand` ein und wähle den Typ **Integration**.
3. Installiere „Zählerstand per Foto“ und starte Home Assistant neu.

### Manuell

Lade `zaehlerstand.zip` aus dem neuesten [Release](https://github.com/GITHUB_USER/ha-zaehlerstand/releases)
herunter. Entpacke es nach `/config/custom_components/zaehlerstand/` und starte Home Assistant neu.

### Zähler anlegen

[![Integration hinzufügen](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=zaehlerstand)

Alternativ: **Einstellungen → Geräte & Dienste → Integration hinzufügen → „Zählerstand per Foto“**.
Für Strom, Gas und Wasser fügst du die Integration jeweils einmal hinzu.

## Ablesen direkt mit dem Handy

### Variante 1: Dashboard-Karte (empfohlen)

Die Integration bringt eine eigene Karte mit. Du musst sie nicht separat installieren.
Tippst du auf **Foto**, öffnet sich direkt die Rückkamera. Das Bild wird sofort ausgewertet
und das Ergebnis erscheint in der Karte.

```yaml
type: custom:zaehlerstand-card
title: Zähler
```

Ohne weitere Angaben zeigt die Karte alle Zähler der Integration. Optional:

```yaml
type: custom:zaehlerstand-card
title: Zähler
zaehler:
  - sensor.stromzahler_zahlerstand
  - entity: sensor.wasserzahler_zahlerstand
    name: Wasser (Keller)
max_bildgroesse: 2048   # längste Kante in Pixel, 0 = Originalgröße
```

So funktioniert die Karte:
- Das Foto wird vor dem Hochladen auf 2048 px verkleinert. Das spart Zeit und KI-Kosten.
  Das Zählwerk bleibt gut lesbar.
- Ist der neue Wert kleiner als der bisherige, fragt die Karte nach („Trotzdem speichern“).
- Passt die erkannte Zählernummer nicht zur gespeicherten, erscheint eine Warnung.
- Es reicht ein normales Benutzerkonto, Admin-Rechte sind nicht nötig.

> Erscheint die Karte nach der Installation nicht, starte Home Assistant neu und lade die App
> bzw. den Browser neu (Strg+F5). Auf manchen iPhones fragt iOS zuerst „Foto aufnehmen /
> Mediathek“, statt direkt die Kamera zu öffnen.

### Variante 2: iOS-Kurzbefehl (optional mit NFC-Tag am Zähler)

Zuerst brauchst du ein Token: Klicke in HA links unten auf deinen Benutzernamen → **Sicherheit** →
**Langlebige Zugriffstoken** → **Token erstellen**. Kopiere das Token.

In der App **Kurzbefehle** legst du einen neuen Kurzbefehl an:

1. **Foto aufnehmen** (Kamera: Rückseite, Vorschau anzeigen: ein)
2. **Bild konvertieren** → JPEG
3. **Bildgröße ändern** → Breite 2048 (optional, spart Zeit)
4. **Inhalte von URL abrufen**
   - URL: `https://DEINE-HA-ADRESSE/api/zaehlerstand/upload/sensor.stromzahler_zahlerstand`
   - Methode: **POST**
   - Header: `Authorization` = `Bearer DEIN_TOKEN`
   - Header: `Content-Type` = `image/jpeg`
   - Haupttext anfordern: **Datei** → *Bild mit geänderter Größe*
5. **Wörterbuchwert abrufen** → Schlüssel `zaehlerstand`
6. **Mitteilung anzeigen** → „Stromzähler: *Wörterbuchwert* kWh“

**Mit NFC-Tag:** Klebe einen NFC-Sticker an den Zähler. Lege in Kurzbefehle → **Automation** →
**NFC** eine Automation an, die den Kurzbefehl startet. Danach reicht es, das Handy an den
Zähler zu halten.

### Variante 3: Android mit „HTTP Shortcuts“

Die kostenlose App [HTTP Shortcuts](https://http-shortcuts.rmy.ch) (Play Store / F-Droid)
kann den Request-Body direkt aus der Kamera nehmen:

1. Neuer Shortcut → **Regular Shortcut**
2. Methode **POST**, URL
   `https://DEINE-HA-ADRESSE/api/zaehlerstand/upload/sensor.stromzahler_zahlerstand`
3. **Authentication** → *Bearer Token* → dein langlebiges Zugriffstoken
4. **Request Body** → *File* → Quelle **Kamera**, Content-Type `image/jpeg`
5. **Response Handling** → *Dialog*. Dann siehst du die Antwort mit dem Zählerstand.
6. Den Shortcut als Icon auf dem Homescreen ablegen.

> NFC unter Android: Apps wie „NFC Tools“ können beim Scannen eines Tags einen
> HTTP-Shortcuts-Shortcut starten.

### Upload-Schnittstelle (für eigene Lösungen)

```
POST /api/zaehlerstand/upload/<entity_id oder entry_id>[?erzwingen=1]
Authorization: Bearer <token>
```

- Body: das Bild direkt (`Content-Type: image/jpeg`, `image/png` oder `image/webp`) **oder**
  `multipart/form-data` mit dem Feld `file`.
- Als Ziel geht jede Entität des Zählers (Sensor, Zählernummer, Foto) oder die Entry-ID.
- HEIC wird abgelehnt, weil die KI-Dienste das Format meist nicht verarbeiten. Bitte vorher in
  JPEG umwandeln.

| Status | Bedeutung |
|---|---|
| 200 | Gespeichert. Die Antwort enthält `zaehlerstand`, `einheit`, `zaehlernummer_erkannt`, `zaehlernummer_passt`, `foto`, `zeitpunkt` |
| 400 | Kein oder ungültiges Bild |
| 401 | Nicht angemeldet oder keine Berechtigung für diesen Zähler |
| 404 | Zähler nicht gefunden |
| 409 | Wert kleiner als der bisherige (`code: kleiner_als_bisher`). Zum Speichern mit `?erzwingen=1` erneut senden |
| 422 | Zählerstand nicht erkannt (`code: nicht_erkannt`) |

Mit curl getestet sieht das so aus:

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: image/jpeg" \
  --data-binary @zaehler.jpg \
  https://DEINE-HA-ADRESSE/api/zaehlerstand/upload/sensor.stromzahler_zahlerstand
```

### Variante 4: Über „Lokale Medien“

Du lädst das Foto in der HA-App unter **Medien → Lokale Medien → Hochladen** hoch und rufst danach
den Dienst „Foto auswerten“ auf. Hinweis: Hochladen in die Medien erfordert Admin-Rechte.
Bequemer geht es mit einem Skript und einem Button im Dashboard:

```yaml
# scripts.yaml
zaehler_strom_ablesen:
  alias: Stromzähler ablesen
  fields:
    foto:
      name: Foto
      required: true
      selector:
        media:
          accept: ["image/*"]
  sequence:
    - action: zaehlerstand.foto_auswerten
      target:
        entity_id: sensor.stromzahler_zahlerstand
      data:
        foto: "{{ foto }}"
      response_variable: ergebnis
    - action: persistent_notification.create
      data:
        title: Stromzähler
        message: >
          Neuer Stand: {{ ergebnis.zaehlerstand }} kWh
          {% if ergebnis.zaehlernummer_passt == false %}
          ⚠️ Zählernummer {{ ergebnis.zaehlernummer_erkannt }} passt nicht!
          {% endif %}
```

Dashboard-Karte:

```yaml
type: entities
title: Zähler
entities:
  - sensor.stromzahler_zahlerstand
  - text.stromzahler_zahlernummer
  - sensor.gaszahler_zahlerstand
  - text.gaszahler_zahlernummer
  - sensor.wasserzahler_zahlerstand
  - text.wasserzahler_zahlernummer
```

> Die genauen Entitäts-IDs hängen vom Namen ab, den du vergeben hast. Du findest sie unter
> Einstellungen → Geräte & Dienste → Zählerstand per Foto → Gerät.

## Mit einer festen Kamera (z. B. ESP32-CAM vor dem Zähler)

```yaml
automation:
  - alias: Gaszähler täglich ablesen
    triggers:
      - trigger: time
        at: "06:00:00"
    actions:
      - action: zaehlerstand.foto_auswerten
        target:
          entity_id: sensor.gaszahler_zahlerstand
        data:
          kamera: camera.gaszahler_cam
```

Der Schnappschuss wird unter `Lokale Medien/zaehlerstand/` gespeichert. So kannst du jede
Ablesung später nachprüfen.

## Dienste

### `zaehlerstand.foto_auswerten`
| Feld | Pflicht | Beschreibung |
|---|---|---|
| Ziel (`target`) | ja | Genau ein Zähler: das Gerät (z. B. „Stromzähler“) oder eine seiner Entitäten |
| `foto` | eins von beiden | Foto aus dem Medienbrowser |
| `kamera` | eins von beiden | Kamera-Entität für einen Schnappschuss |
| `ai_task_entity` | nein | Andere KI-Entität für diesen Aufruf |
| `erzwingen` | nein | Auch einen kleineren Wert speichern |

Antwort: `zaehlerstand`, `zaehlernummer_erkannt`, `zaehlernummer_passt`, `foto`, `zeitpunkt`

### `zaehlerstand.wert_setzen`
Setzt den Stand manuell, wenn das Foto nicht lesbar ist: Ziel (Zähler), `wert`, `erzwingen`.

### Event `zaehlerstand_erfasst`
Wird nach jeder erfolgreichen Erfassung ausgelöst und enthält dieselben Daten. Damit kannst du
z. B. die Werte in eine Tabelle schreiben oder an den Versorger melden.

## Tipps für gute Erkennung
- Fotografiere gerade von vorn, ohne Blitz-Spiegelung auf der Scheibe.
- Füll das Bild mit dem Zählwerk, aber lass die Zählernummer mit im Bild.
- Lies den Wert nach jeder Erfassung einmal gegen. Die KI kann sich verlesen, vor allem bei
  Ziffernrollen, die gerade umspringen.
