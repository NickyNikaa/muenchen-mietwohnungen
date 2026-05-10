// Mietwohnungen München — Frontend.
// Liest data.json (vom Scraper geschrieben) und stellt Karte + Grid bereit.

const state = {
    all: [],
    filter: { search: "", priceMax: null, sizeMin: null, platform: "", onlyNew: false, sort: "new" },
    map: null,
    markers: [],
};

const fmt = {
    eur: (v) => v == null ? "–" : new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(v),
    m2: (v) => v == null ? "–" : `${v.toFixed(0)} m²`,
    rooms: (v) => v == null ? "–" : `${v} Zi.`,
    date: (iso) => {
        if (!iso) return "–";
        const d = new Date(iso);
        return d.toLocaleString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
    },
};

async function loadData() {
    try {
        const r = await fetch("data.json", { cache: "no-store" });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return await r.json();
    } catch (e) {
        document.body.insertAdjacentHTML("afterbegin",
            `<div class="error-banner">Daten konnten nicht geladen werden: ${e.message}. Vermutlich ist noch kein Scrape-Lauf erfolgt.</div>`);
        return { generated_at: null, listings: [] };
    }
}

function initMap() {
    state.map = L.map("map").setView([48.1374, 11.5754], 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap",
        maxZoom: 19,
    }).addTo(state.map);

    // 4-km-Kreis um Marienplatz
    L.circle([48.1374, 11.5754], { radius: 4000, color: "#2563eb", fillOpacity: 0.04, weight: 1 }).addTo(state.map);
}

function renderMap(listings) {
    state.markers.forEach(m => state.map.removeLayer(m));
    state.markers = [];
    listings.forEach(l => {
        if (l.lat == null || l.lng == null) return;
        const color = l.is_new ? "#16a34a" : "#2563eb";
        const m = L.circleMarker([l.lat, l.lng], {
            radius: 9, color: "#fff", fillColor: color, fillOpacity: 0.95, weight: 2.5,
        });
        const img = l.image_url ? `<img src="${escapeHtml(l.image_url)}" style="width:100%;max-width:240px;height:140px;object-fit:cover;border-radius:4px;margin-bottom:6px"/>` : "";
        m.bindPopup(`${img}<strong>${escapeHtml(l.title || "")}</strong><br>${fmt.eur(l.price)} · ${fmt.m2(l.size_m2)} · ${fmt.rooms(l.rooms)}<br><a href="${l.url}" target="_blank" rel="noopener">Inserat öffnen ↗</a>`);
        m.on("click", () => highlightCard(l.id));
        m.addTo(state.map);
        state.markers.push(m);
    });
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function applyFilters() {
    const f = state.filter;
    let out = state.all.filter(l => {
        if (f.priceMax != null && l.price != null && l.price > f.priceMax) return false;
        if (f.sizeMin != null && l.size_m2 != null && l.size_m2 < f.sizeMin) return false;
        if (f.platform && l.platform !== f.platform) return false;
        if (f.onlyNew && !l.is_new) return false;
        if (f.search) {
            const hay = (l.title + " " + (l.address || "") + " " + (l.description || "")).toLowerCase();
            if (!hay.includes(f.search.toLowerCase())) return false;
        }
        return true;
    });

    switch (f.sort) {
        case "price-asc":  out.sort((a,b) => (a.price ?? 1e9) - (b.price ?? 1e9)); break;
        case "price-desc": out.sort((a,b) => (b.price ?? -1) - (a.price ?? -1)); break;
        case "size-desc":  out.sort((a,b) => (b.size_m2 ?? -1) - (a.size_m2 ?? -1)); break;
        case "date-desc":  out.sort((a,b) => (b.first_seen || "").localeCompare(a.first_seen || "")); break;
        case "new":
        default:
            out.sort((a,b) => {
                if (a.is_new !== b.is_new) return a.is_new ? -1 : 1;
                return (b.first_seen || "").localeCompare(a.first_seen || "");
            });
    }
    return out;
}

function renderGrid(listings) {
    const grid = document.getElementById("grid");
    if (listings.length === 0) {
        grid.innerHTML = `<div class="empty">Keine Treffer mit aktuellen Filtern.</div>`;
        return;
    }
    grid.innerHTML = listings.map(l => `
        <article class="card ${l.is_new ? "new" : ""}" data-id="${escapeHtml(l.id)}" data-lat="${l.lat ?? ""}" data-lng="${l.lng ?? ""}">
            <div class="img-wrap ${l.image_url ? "" : "placeholder"}" style="${l.image_url ? `background-image:url('${escapeHtml(l.image_url)}')` : ""}">
                ${l.is_new ? '<span class="badge">NEU</span>' : ""}
                <span class="platform">${escapeHtml(l.platform)}</span>
            </div>
            <div class="body">
                <div class="title">${escapeHtml(l.title || "")}</div>
                <div class="specs">
                    <span><strong>${fmt.eur(l.price)}</strong></span>
                    <span>${fmt.m2(l.size_m2)}</span>
                    <span>${fmt.rooms(l.rooms)}</span>
                </div>
                <div class="addr">${escapeHtml(l.address || "")}</div>
                <div class="footer">
                    <span>seit ${fmt.date(l.first_seen)}</span>
                    <a class="open" href="${escapeHtml(l.url)}" target="_blank" rel="noopener">öffnen ↗</a>
                </div>
            </div>
        </article>
    `).join("");

    grid.querySelectorAll(".card").forEach(card => {
        card.addEventListener("click", (e) => {
            if (e.target.tagName === "A") return;
            const lat = parseFloat(card.dataset.lat);
            const lng = parseFloat(card.dataset.lng);
            if (!isNaN(lat) && !isNaN(lng)) {
                state.map.setView([lat, lng], 15);
                const marker = state.markers.find(m => {
                    const ll = m.getLatLng();
                    return Math.abs(ll.lat - lat) < 1e-6 && Math.abs(ll.lng - lng) < 1e-6;
                });
                if (marker) marker.openPopup();
            }
        });
    });
}

function highlightCard(id) {
    document.querySelectorAll(".card").forEach(c => c.style.outline = "");
    const el = document.querySelector(`.card[data-id="${CSS.escape(id)}"]`);
    if (el) {
        el.style.outline = "3px solid #2563eb";
        el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
}

function populatePlatformFilter(listings) {
    const sel = document.getElementById("platform");
    const platforms = [...new Set(listings.map(l => l.platform))].sort();
    sel.innerHTML = `<option value="">alle</option>` + platforms.map(p => `<option value="${p}">${p}</option>`).join("");
}

function readFiltersFromForm() {
    state.filter.search   = document.getElementById("search").value;
    state.filter.priceMax = document.getElementById("price-max").value ? +document.getElementById("price-max").value : null;
    state.filter.sizeMin  = document.getElementById("size-min").value  ? +document.getElementById("size-min").value  : null;
    state.filter.platform = document.getElementById("platform").value;
    state.filter.sort     = document.getElementById("sort").value;
    state.filter.onlyNew  = document.getElementById("only-new").checked;
}

function update() {
    readFiltersFromForm();
    const filtered = applyFilters();
    renderGrid(filtered);
    renderMap(filtered);
    document.getElementById("counts").textContent =
        `${filtered.length} angezeigt · ${state.all.filter(l => l.is_new).length} neu · ${state.all.length} gesamt`;
}

function attachFilterEvents() {
    // Live-Update bei Auswahl-Änderungen (Selects, Checkbox)
    ["platform", "sort", "only-new"].forEach(id => {
        document.getElementById(id).addEventListener("change", update);
    });
    // Live-Update mit kurzem Debounce bei Texteingaben — und der Suchen-Button macht's explizit
    let t;
    ["search", "price-max", "size-min"].forEach(id => {
        document.getElementById(id).addEventListener("input", () => {
            clearTimeout(t);
            t = setTimeout(update, 250);
        });
    });
    document.getElementById("reset-btn").addEventListener("click", () => {
        document.getElementById("filter-form").reset();
        update();
    });
    window.applyAndRender = update;
}

(async function init() {
    initMap();
    const data = await loadData();
    state.all = data.listings || [];
    document.getElementById("generated-at").textContent =
        data.generated_at ? `aktualisiert ${fmt.date(data.generated_at)}` : "noch kein Lauf";
    populatePlatformFilter(state.all);
    attachFilterEvents();
    update();
})();
