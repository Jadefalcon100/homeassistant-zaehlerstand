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

## Ablesen per Handy (Companion App)

1. In der HA-App **Medien → Lokale Medien** öffnen, rechts oben **Hochladen** antippen und
   „Foto aufnehmen“ wählen. Das Foto landet im lokalen Medienordner.
2. Den Dienst **„Zählerstand per Foto: Foto auswerten“** aufrufen, Zähler wählen, Foto wählen. Fertig.

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
      data:
        entity_id: sensor.stromzahler_zahlerstand
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
        data:
          entity_id: sensor.gaszahler_zahlerstand
          kamera: camera.gaszahler_cam
```

Der Schnappschuss wird unter `Lokale Medien/zaehlerstand/` gespeichert. So kannst du jede
Ablesung später nachprüfen.

## Dienste

### `zaehlerstand.foto_auswerten`
| Feld | Pflicht | Beschreibung |
|---|---|---|
| `entity_id` | ja | Zählerstand-Sensor |
| `foto` | eins von beiden | Foto aus dem Medienbrowser |
| `kamera` | eins von beiden | Kamera-Entität für einen Schnappschuss |
| `ai_task_entity` | nein | Andere KI-Entität für diesen Aufruf |
| `erzwingen` | nein | Auch einen kleineren Wert speichern |

Antwort: `zaehlerstand`, `zaehlernummer_erkannt`, `zaehlernummer_passt`, `foto`, `zeitpunkt`

### `zaehlerstand.wert_setzen`
Setzt den Stand manuell, wenn das Foto nicht lesbar ist: `entity_id`, `wert`, `erzwingen`.

### Event `zaehlerstand_erfasst`
Wird nach jeder erfolgreichen Erfassung ausgelöst und enthält dieselben Daten. Damit kannst du
z. B. die Werte in eine Tabelle schreiben oder an den Versorger melden.

## Tipps für gute Erkennung
- Fotografiere gerade von vorn, ohne Blitz-Spiegelung auf der Scheibe.
- Füll das Bild mit dem Zählwerk, aber lass die Zählernummer mit im Bild.
- Lies den Wert nach jeder Erfassung einmal gegen. Die KI kann sich verlesen, vor allem bei
  Ziffernrollen, die gerade umspringen.
