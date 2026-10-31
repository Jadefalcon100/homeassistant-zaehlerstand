/*
 * Zählerstand-Karte – Foto mit der Handykamera aufnehmen und direkt auswerten.
 * Wird von der Integration „Zählerstand per Foto“ automatisch geladen.
 *
 * type: custom:zaehlerstand-card
 * title: Zähler                  # optional
 * zaehler:                       # optional, Standard: alle Zähler der Integration
 *   - sensor.stromzahler_zahlerstand
 *   - entity: sensor.gaszahler_zahlerstand
 *     name: Gas
 * max_bildgroesse: 2048          # optional, längste Kante in Pixel (0 = Original)
 */

const DOMAIN = "zaehlerstand";
const CARD_VERSION = "1.1.0";

const ICONS = {
  energy: "mdi:flash",
  gas: "mdi:fire",
  water: "mdi:water",
};

const STYLE = `
  :host { display: block; }
  ha-card { overflow: hidden; }
  .header {
    padding: 16px 16px 0;
    font-size: var(--ha-card-header-font-size, 24px);
    color: var(--ha-card-header-color, var(--primary-text-color));
  }
  .list { padding: 8px 16px 16px; display: flex; flex-direction: column; gap: 4px; }
  .meter { padding: 8px 0; }
  .meter + .meter { border-top: 1px solid var(--divider-color); }
  .row { display: flex; align-items: center; gap: 12px; }
  .icon {
    flex: none; width: 40px; height: 40px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.12);
    color: var(--primary-color);
  }
  .info { flex: 1; min-width: 0; }
  .name { font-weight: 500; color: var(--primary-text-color); }
  .value { font-size: 1.1em; color: var(--primary-text-color); font-variant-numeric: tabular-nums; }
  .meta {
    font-size: 0.85em; color: var(--secondary-text-color);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .shoot {
    position: relative; flex: none; overflow: hidden;
    display: inline-flex; align-items: center; gap: 6px;
    padding: 0 16px; height: 40px; border-radius: 20px;
    background: var(--primary-color); color: var(--text-primary-color, #fff);
    font-weight: 500; cursor: pointer; user-select: none;
  }
  .shoot.busy { opacity: 0.6; pointer-events: none; }
  /* Unsichtbares Eingabefeld über dem Button – zuverlässiger als display:none in mobilen WebViews */
  .shoot input {
    position: absolute; inset: 0; width: 100%; height: 100%;
    opacity: 0; cursor: pointer; font-size: 0;
  }
  .status {
    display: none; margin-top: 8px; padding: 8px 10px; border-radius: 8px;
    font-size: 0.9em; align-items: center; gap: 10px;
  }
  .status.show { display: flex; }
  .status img { width: 48px; height: 48px; object-fit: cover; border-radius: 6px; flex: none; }
  .status .text { flex: 1; }
  .status.info { background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.1); }
  .status.ok { background: rgba(var(--rgb-success-color, 67, 160, 71), 0.15); }
  .status.warn { background: rgba(var(--rgb-warning-color, 255, 166, 0), 0.18); }
  .status.error { background: rgba(var(--rgb-error-color, 219, 68, 55), 0.15); }
  .status button {
    border: none; border-radius: 16px; padding: 6px 12px; cursor: pointer;
    background: var(--primary-color); color: var(--text-primary-color, #fff); font: inherit;
  }
  .empty { padding: 16px; color: var(--secondary-text-color); }
`;

class ZaehlerstandCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._rows = new Map(); // entity_id -> DOM-Referenzen
    this._signature = "";
  }

  static getStubConfig() {
    return {};
  }

  setConfig(config) {
    this._config = { max_bildgroesse: 2048, ...(config || {}) };
    this._signature = "";
    if (this._hass) this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const meters = this._meters();
    const signature = meters.map((m) => m.entity).join("|") + "|" + (this._config?.title ?? "");
    if (signature !== this._signature) {
      this._signature = signature;
      this._render();
    } else {
      this._update();
    }
  }

  getCardSize() {
    return 1 + Math.max(1, this._meters().length);
  }

  // ---------------------------------------------------------------- Daten
  _meters() {
    const hass = this._hass;
    if (!hass) return [];
    const configured = this._config?.zaehler;
    let list;
    if (Array.isArray(configured) && configured.length) {
      list = configured.map((z) => (typeof z === "string" ? { entity: z } : { ...z }));
    } else {
      list = Object.values(hass.entities || {})
        .filter((e) => e.platform === DOMAIN && e.entity_id.startsWith("sensor."))
        .map((e) => ({ entity: e.entity_id }))
        .sort((a, b) => this._name(a).localeCompare(this._name(b), "de"));
    }
    return list.filter((m) => m.entity);
  }

  _name(meter) {
    const hass = this._hass;
    if (meter.name) return meter.name;
    const reg = hass.entities?.[meter.entity];
    const device = reg?.device_id ? hass.devices?.[reg.device_id] : undefined;
    return (
      device?.name_by_user ||
      device?.name ||
      hass.states[meter.entity]?.attributes.friendly_name ||
      meter.entity
    );
  }

  _numberEntity(meter) {
    const hass = this._hass;
    const reg = hass.entities?.[meter.entity];
    if (!reg?.device_id) return undefined;
    return Object.values(hass.entities).find(
      (e) => e.device_id === reg.device_id && e.platform === DOMAIN && e.entity_id.startsWith("text.")
    )?.entity_id;
  }

  _formatValue(stateObj) {
    if (!stateObj || ["unknown", "unavailable"].includes(stateObj.state)) return "Noch kein Zählerstand";
    if (typeof this._hass.formatEntityState === "function") {
      return this._hass.formatEntityState(stateObj);
    }
    const unit = stateObj.attributes.unit_of_measurement || "";
    const num = Number(stateObj.state);
    const text = Number.isFinite(num) ? num.toLocaleString("de-DE") : stateObj.state;
    return `${text} ${unit}`.trim();
  }

  _relative(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    if (isNaN(date)) return "";
    const lang = this._hass.locale?.language || this._hass.language || "de";
    const rtf = new Intl.RelativeTimeFormat(lang, { numeric: "auto" });
    const seconds = Math.round((date - Date.now()) / 1000);
    const steps = [
      [60, "second"], [60, "minute"], [24, "hour"], [7, "day"], [4.345, "week"], [12, "month"], [Infinity, "year"],
    ];
    let value = seconds;
    for (const [factor, unit] of steps) {
      if (Math.abs(value) < factor) return rtf.format(Math.round(value), unit);
      value /= factor;
    }
    return "";
  }

  // ---------------------------------------------------------------- Darstellung
  _render() {
    const root = this.shadowRoot;
    root.innerHTML = "";
    this._rows.clear();

    const style = document.createElement("style");
    style.textContent = STYLE;
    root.appendChild(style);

    const card = document.createElement("ha-card");
    if (this._config?.title) {
      const header = document.createElement("div");
      header.className = "header";
      header.textContent = this._config.title;
      card.appendChild(header);
    }

    const meters = this._meters();
    if (!meters.length) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent =
        "Keine Zähler gefunden. Richte zuerst einen Zähler in der Integration „Zählerstand per Foto“ ein.";
      card.appendChild(empty);
      root.appendChild(card);
      return;
    }

    const list = document.createElement("div");
    list.className = "list";
    for (const meter of meters) list.appendChild(this._buildRow(meter));
    card.appendChild(list);
    root.appendChild(card);
    this._update();
  }

  _buildRow(meter) {
    const el = document.createElement("div");
    el.className = "meter";
    el.innerHTML = `
      <div class="row">
        <div class="icon"><ha-icon></ha-icon></div>
        <div class="info">
          <div class="name"></div>
          <div class="value"></div>
          <div class="meta"></div>
        </div>
        <label class="shoot"><ha-icon icon="mdi:camera"></ha-icon><span>Foto</span></label>
      </div>
      <div class="status"><img alt="" hidden><div class="text"></div></div>`;

    const refs = {
      meter,
      icon: el.querySelector(".icon ha-icon"),
      name: el.querySelector(".name"),
      value: el.querySelector(".value"),
      meta: el.querySelector(".meta"),
      shoot: el.querySelector(".shoot"),
      status: el.querySelector(".status"),
      thumb: el.querySelector(".status img"),
      statusText: el.querySelector(".status .text"),
      blob: null,
    };
    this._newInput(refs);
    this._rows.set(meter.entity, refs);
    return el;
  }

  // Eingabefeld nach jeder Nutzung neu anlegen – manche Android-WebViews feuern sonst kein change-Event mehr
  _newInput(refs) {
    refs.shoot.querySelector("input")?.remove();
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.setAttribute("capture", "environment");
    input.addEventListener("change", () => {
      const file = input.files && input.files[0];
      this._newInput(refs);
      if (file) this._handleFile(refs, file);
    });
    refs.shoot.appendChild(input);
  }

  _update() {
    for (const refs of this._rows.values()) {
      const stateObj = this._hass.states[refs.meter.entity];
      refs.icon.icon =
        refs.meter.icon || ICONS[stateObj?.attributes.device_class] || "mdi:counter";
      refs.name.textContent = this._name(refs.meter);
      refs.value.textContent = stateObj ? this._formatValue(stateObj) : `${refs.meter.entity} nicht gefunden`;

      const parts = [];
      const numberId = this._numberEntity(refs.meter);
      const number = numberId ? this._hass.states[numberId]?.state : undefined;
      if (number && !["unknown", "unavailable", ""].includes(number)) parts.push(`Nr. ${number}`);
      const rel = this._relative(stateObj?.attributes.letzte_ablesung);
      if (rel) parts.push(rel);
      refs.meta.textContent = parts.join(" · ");
    }
  }

  _setStatus(refs, kind, text, action) {
    refs.status.className = `status show ${kind}`;
    refs.statusText.textContent = text;
    refs.status.querySelector("button")?.remove();
    if (action) {
      const btn = document.createElement("button");
      btn.textContent = action.label;
      btn.addEventListener("click", action.onClick);
      refs.status.appendChild(btn);
    }
  }

  // ---------------------------------------------------------------- Ablauf
  async _handleFile(refs, file) {
    refs.shoot.classList.add("busy");
    try {
      this._setStatus(refs, "info", "Foto wird vorbereitet …");
      const blob = await this._shrink(file);
      refs.blob = blob;
      if (refs.thumb.src) URL.revokeObjectURL(refs.thumb.src);
      refs.thumb.src = URL.createObjectURL(blob);
      refs.thumb.hidden = false;
      await this._upload(refs, false);
    } finally {
      refs.shoot.classList.remove("busy");
    }
  }

  async _shrink(file) {
    const max = Number(this._config?.max_bildgroesse) || 0;
    try {
      const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
      const scale = max > 0 ? Math.min(1, max / Math.max(bitmap.width, bitmap.height)) : 1;
      if (scale === 1 && file.type === "image/jpeg" && file.size < 4 * 1024 * 1024) {
        bitmap.close?.();
        return file;
      }
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(bitmap.width * scale);
      canvas.height = Math.round(bitmap.height * scale);
      canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
      bitmap.close?.();
      const blob = await new Promise((res) => canvas.toBlob(res, "image/jpeg", 0.88));
      return blob || file;
    } catch (err) {
      console.warn("zaehlerstand-card: Verkleinern nicht möglich, sende Original", err);
      return file;
    }
  }

  async _post(url, body) {
    if (typeof this._hass.fetchWithAuth === "function") {
      return this._hass.fetchWithAuth(url, { method: "POST", body });
    }
    const token = this._hass.auth?.data?.access_token;
    return fetch(url, {
      method: "POST",
      body,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  }

  async _upload(refs, force) {
    const blob = refs.blob;
    if (!blob) return;
    this._setStatus(refs, "info", "Wird ausgewertet … das dauert einige Sekunden.");
    refs.shoot.classList.add("busy");

    const form = new FormData();
    form.append("file", blob, blob.name || "zaehler.jpg");
    const url =
      `/api/zaehlerstand/upload/${encodeURIComponent(refs.meter.entity)}` + (force ? "?erzwingen=1" : "");

    let response, data;
    try {
      response = await this._post(url, form);
      data = await response.json().catch(() => ({}));
    } catch (err) {
      this._setStatus(refs, "error", `Verbindung fehlgeschlagen: ${err.message || err}`);
      refs.shoot.classList.remove("busy");
      return;
    }
    refs.shoot.classList.remove("busy");

    if (response.ok) {
      const unit = data.einheit || "";
      const value = Number(data.zaehlerstand).toLocaleString(this._hass.locale?.language || "de-DE", {
        maximumFractionDigits: 4,
      });
      if (data.zaehlernummer_passt === false) {
        this._setStatus(
          refs,
          "warn",
          `Gespeichert: ${value} ${unit}. Achtung: Auf dem Foto steht Zählernummer ${data.zaehlernummer_erkannt} – passt nicht zur gespeicherten Nummer!`
        );
      } else {
        this._setStatus(refs, "ok", `Gespeichert: ${value} ${unit}`);
      }
      refs.blob = null;
      return;
    }

    const message = data.message || `Fehler ${response.status}`;
    if (response.status === 409) {
      this._setStatus(refs, "warn", message, {
        label: "Trotzdem speichern",
        onClick: () => this._upload(refs, true),
      });
    } else if (response.status === 422) {
      this._setStatus(refs, "error", `${message.split(" (KI-Antwort")[0]} Bitte ein neues Foto aufnehmen.`);
    } else if (response.status === 401) {
      this._setStatus(refs, "error", "Nicht angemeldet oder keine Berechtigung für diesen Zähler.");
    } else {
      this._setStatus(refs, "error", message, {
        label: "Nochmal senden",
        onClick: () => this._upload(refs, false),
      });
    }
  }
}

if (!customElements.get("zaehlerstand-card")) {
  customElements.define("zaehlerstand-card", ZaehlerstandCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "zaehlerstand-card",
    name: "Zählerstand per Foto",
    description: "Zähler mit der Handykamera fotografieren und direkt auswerten lassen.",
    preview: false,
    documentationURL: "https://github.com/jadefalcon100/ha-zaehlerstand",
  });
  console.info(`%c ZAEHLERSTAND-CARD %c ${CARD_VERSION} `, "background:#03a9f4;color:#fff", "");
}
