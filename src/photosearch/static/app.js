const $ = (selector) => document.querySelector(selector);
const grid = $("#grid");
const query = $("#query");
const status = $("#status");
const chip = $("#chip");
const viewer = $("#viewer");

let current = null; // foto abierta en el visor
let lastRequest = 0; // para descartar respuestas de búsquedas que ya no importan

const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

async function load(url, options, describe) {
  const request = ++lastRequest;
  const data = await fetch(url, options).then((response) => response.json());
  if (request !== lastRequest) return;
  render(data.results);
  status.textContent = describe(data);
}

function render(results) {
  grid.replaceChildren(
    ...results.map((photo) => {
      const card = document.createElement("button");
      card.className = "card";
      card.innerHTML = `<img src="${photo.thumb}" loading="lazy" alt="">`;
      if (photo.score !== undefined) {
        card.insertAdjacentHTML("beforeend", `<span class="score">${photo.score.toFixed(2)}</span>`);
      }
      card.onclick = () => openViewer(photo);
      return card;
    }),
  );
}

function setChip(src) {
  chip.hidden = !src;
  if (src) chip.querySelector("img").src = src;
}

function showLatest() {
  setChip(null);
  load("/api/photos", {}, (d) => `${plural(d.results.length, "foto")} recientes`);
}

function searchText(text) {
  setChip(null);
  if (!text.trim()) return showLatest();
  load(`/api/search?q=${encodeURIComponent(text)}`, {}, (d) => `${plural(d.results.length, "foto")} · ${d.ms} ms`);
}

function searchSimilar(photo) {
  query.value = "";
  setChip(photo.thumb);
  load(`/api/similar/${photo.id}`, {}, (d) => `${plural(d.results.length, "foto")} parecidas · ${d.ms} ms`);
}

function searchByImage(file) {
  query.value = "";
  setChip(URL.createObjectURL(file));
  const body = new FormData();
  body.append("file", file);
  load("/api/search-by-image", { method: "POST", body }, (d) => `${plural(d.results.length, "foto")} parecidas · ${d.ms} ms`);
}

// Búsqueda mientras escribes, con un pequeño margen entre teclas
let typingTimer;
query.addEventListener("input", () => {
  clearTimeout(typingTimer);
  typingTimer = setTimeout(() => searchText(query.value), 200);
});
$("#search").addEventListener("submit", (event) => {
  event.preventDefault();
  searchText(query.value);
});
chip.querySelector("button").onclick = () => {
  showLatest();
  query.focus();
};

// Visor
function openViewer(photo) {
  current = photo;
  $("#viewer-img").src = `/api/photos/${photo.id}/original`;
  $("#viewer-date").textContent = photo.taken_at
    ? new Date(photo.taken_at).toLocaleDateString("es-ES", { dateStyle: "long" })
    : "";
  viewer.showModal();
}
$("#more").onclick = () => {
  viewer.close();
  searchSimilar(current);
};
$("#close").onclick = () => viewer.close();
viewer.addEventListener("click", (event) => {
  if (event.target === viewer) viewer.close();
});

// Arrastrar una foto desde el escritorio
const drop = $("#drop");
addEventListener("dragover", (event) => {
  event.preventDefault();
  drop.classList.add("on");
});
addEventListener("dragleave", (event) => {
  if (!event.relatedTarget) drop.classList.remove("on");
});
addEventListener("drop", (event) => {
  event.preventDefault();
  drop.classList.remove("on");
  const file = event.dataTransfer.files[0];
  if (file?.type.startsWith("image/")) searchByImage(file);
});

$("#scores").onchange = (event) => document.body.classList.toggle("show-scores", event.target.checked);

showLatest();
