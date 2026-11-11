// Actualiza el panel en vivo consultando /api/estado/ cada segundo.
(function () {
  const $ = (id) => document.getElementById(id);
  const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const lista = (el, items, vacio) => {
    el.innerHTML = items.length ? items.join("") : `<li class="vacio">${vacio}</li>`;
  };

  async function refrescar() {
    try {
      const r = await fetch(window.VG_ESTADO_URL, { cache: "no-store" });
      if (!r.ok) throw new Error(r.status);
      const e = await r.json();

      $("k-presentes").textContent = e.presentes_hoy;
      $("k-registros").textContent = e.registros_hoy;
      const cam = $("k-camara");
      cam.textContent = e.camara_conectada ? `Conectada · ${e.fps} fps` : "Sin señal";
      cam.className = "estado " + (e.camara_conectada ? "ok" : "mal");
      const mod = $("k-modelo");
      mod.textContent = e.modelo_entrenado ? "Entrenado" : "Sin entrenar";
      mod.className = "estado " + (e.modelo_entrenado ? "ok" : "mal");
      $("vivo").classList.toggle("caido", !e.camara_conectada);

      lista($("detecciones"), e.detecciones.map((d) =>
        `<li><b>${esc(d.nombre)}</b><span class="chip ${d.reconocido ? "verde" : "rojo"}">${
          d.reconocido ? "reconocido" : (d.distancia === null ? "rostro" : "desconocido")}</span></li>`), "Nadie detectado");
      lista($("ultimas"), e.ultimas.map((a) =>
        `<li><b>${esc(a.nombre)}</b><span>${a.hora} · ${a.confianza}%</span></li>`), "Sin registros todavía");
      lista($("eventos"), e.eventos.map((v) =>
        `<li><span>${v.hora}</span>${esc(v.mensaje)}</li>`), "—");
    } catch (err) {
      $("k-camara").textContent = "Sin conexión";
      $("k-camara").className = "estado mal";
    }
  }
  refrescar();
  setInterval(refrescar, 1000);
})();
