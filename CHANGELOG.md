# Changelog

## 1.1.0 – 2026-10-31
- Neue Dashboard-Karte `custom:zaehlerstand-card`: Foto direkt mit der Handykamera aufnehmen und
  auswerten. Die Integration liefert sie automatisch mit.
- Neuer Upload-Endpunkt `POST /api/zaehlerstand/upload/<ziel>` für die Karte, iOS-Kurzbefehle,
  Android „HTTP Shortcuts“ und eigene Skripte. Braucht keine Admin-Rechte.
- Antworten enthalten jetzt die Einheit (`einheit`).

## 1.0.1 – 2026-10-31
- Dienste `foto_auswerten` und `wert_setzen` nutzen jetzt die Zielauswahl (`target`). Den Zähler
  wählst du in der Oberfläche als Gerät oder Entität.
- Aufrufe mit `entity_id` unter `data:` funktionieren weiterhin.

## 1.0.0 – 2026-10-31
- Erste Version
- Zählerstand per Foto (Medienbrowser) oder Kamera-Schnappschuss über AI Task auslesen
- Sensor „Zählerstand“ (Energie-Dashboard-kompatibel), Text „Zählernummer“, Bild „Letztes Foto“
- Abgleich der erkannten mit der gespeicherten Zählernummer
- Plausibilitätsprüfung gegen sinkende Zählerstände
- Dienst zum manuellen Setzen des Zählerstands
