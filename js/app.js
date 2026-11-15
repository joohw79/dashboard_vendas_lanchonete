/* Interface do painel: carga de dados, filtros, abas e gráficos (Plotly.js). */
(function () {
  "use strict";
  const { DIAS, lerPlanilha, tratar, indicadores, soma } = window.Tratamento;
  const I = window.Insights;
  const { esc, fmt, pct, brl, mesPt, agrupar } = I;

  const KETCHUP = "#C8361B", AZUL = "#2563A8", MOSTARDA = "#B8860B", VERDE = "#2E8B57", ROXO = "#8A4B9A";
  const TINTA = "#2B2118", TINTA_SUAVE = "#7A6A5A", GRADE = "#E8DCC9", CINZA = "#9A8F82", AREIA = "#D9C7A8", CREME = "#FBF6EE";
  const COR_PAGAMENTO = { "Pix": KETCHUP, "Cartão de Crédito": AZUL, "Cartão de Débito": MOSTARDA, "Dinheiro": VERDE, "Não informado": CINZA };
  const COR_CATEGORIA = { "Lanches": KETCHUP, "Porções": AZUL, "Salgados": MOSTARDA, "Bebidas": VERDE, "Sobremesas": ROXO };
  const COR_EXTRA = [AZUL, VERDE, ROXO, MOSTARDA, CINZA];
  const CONFIG = { displayModeBar: false, responsive: true };

  const $ = (id) => document.getElementById(id);
  const estado = { base: null, relatorio: null, exemplo: false, filtrado: [], m: null, aba: "resumo", sujo: new Set() };

  /* ---------- dados ---------- */
  function carregarBuffer(buffer, exemplo) {
    try {
      const { base, relatorio } = tratar(lerPlanilha(buffer));
      if (!base.length) throw new Error("Nenhuma linha válida encontrada na planilha.");
      estado.base = base; estado.relatorio = relatorio; estado.exemplo = exemplo;
      aviso(exemplo ? "Exibindo <b>dados fictícios</b> de demonstração." : "", false);
      montarFiltros();
      aplicar();
    } catch (e) {
      aviso("Não foi possível ler a planilha: " + esc(e.message), true);
    }
  }

  function base64ParaBuffer(b64) {
    const bin = atob(b64), bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return bytes.buffer;
  }

  function aviso(html, erro) {
    const el = $("aviso");
    el.hidden = !html;
    el.className = "aviso" + (erro ? " erro" : "");
    el.innerHTML = html;
  }

  /* ---------- filtros ---------- */
  function chips(containerId, valores, cls) {
    const c = $(containerId);
    c.innerHTML = valores.map((v, i) =>
      `<label class="chip"><input type="checkbox" value="${esc(v)}" checked data-grupo="${cls}"><span>${esc(v)}</span></label>`).join("");
  }

  function montarFiltros() {
    const datas = estado.base.map((r) => r.Data).sort();
    const dmin = datas[0], dmax = datas[datas.length - 1];
    for (const id of ["dataIni", "dataFim"]) { $(id).min = dmin; $(id).max = dmax; }
    $("dataIni").value = dmin; $("dataFim").value = dmax;
    const uniq = (f) => [...new Set(estado.base.map(f))].sort((a, b) => a.localeCompare(b, "pt-BR"));
    chips("filtroCategoria", uniq((r) => r.Categoria), "categoria");
    chips("filtroPagamento", uniq((r) => r.Forma_Pagamento), "pagamento");
  }

  const marcados = (grupo) => new Set([...document.querySelectorAll(`input[data-grupo="${grupo}"]:checked`)].map((i) => i.value));

  function aplicar() {
    const ini = $("dataIni").value || "0000-00-00", fim = $("dataFim").value || "9999-99-99";
    const cats = marcados("categoria"), pgs = marcados("pagamento");
    estado.filtrado = estado.base.filter((r) => r.Data >= ini && r.Data <= fim && cats.has(r.Categoria) && pgs.has(r.Forma_Pagamento));
    const conteudo = $("conteudo");
    if (!estado.filtrado.length) {
      conteudo.hidden = true;
      aviso("Nenhuma venda encontrada com os filtros selecionados.", false);
      return;
    }
    aviso(estado.exemplo ? "Exibindo <b>dados fictícios</b> de demonstração." : "", false);
    conteudo.hidden = false;
    const k = indicadores(estado.filtrado);
    $("kpiFat").textContent = brl(k.faturamento);
    $("kpiPed").textContent = fmt(k.pedidos, 0);
    $("kpiTicket").textContent = brl(k.ticket_medio);
    $("kpiItens").textContent = fmt(k.itens, 0);
    estado.m = I.metricas(estado.filtrado);
    estado.sujo = new Set(["resumo", "tempo", "cardapio", "pagamentos", "qualidade"]);
    renderizarAba(estado.aba);
  }

  /* ---------- gráficos ---------- */
  function layout(titulo, o = {}) {
    return {
      title: { text: titulo, x: 0, xanchor: "left", font: { size: 15, color: TINTA } },
      paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
      font: { color: TINTA_SUAVE, size: 12 },
      margin: { l: 8, r: 8, t: 46, b: 8 },
      showlegend: !!o.legenda, legend: { orientation: "h", y: -0.12, x: 0, title: { text: "" } },
      hoverlabel: { bgcolor: "#fff", bordercolor: GRADE, font: { color: TINTA } },
      height: o.altura,
      xaxis: Object.assign({ showgrid: false, linecolor: GRADE, automargin: true }, o.x),
      yaxis: Object.assign({ gridcolor: GRADE, zeroline: false, automargin: true }, o.y),
      barmode: o.barmode,
    };
  }
  const barra = (cor) => ({ color: cor, cornerradius: 6 });
  const mostrar = (id, dados, lay) => Plotly.react($(id), dados, lay, CONFIG);

  function graficoMapa(linhas) {
    const horas = [...new Set(linhas.filter((r) => r.Hora !== null).map((r) => r.Hora))];
    if (!horas.length) { $("g-heat").innerHTML = ""; return; }
    const hmin = Math.min(...horas), hmax = Math.max(...horas);
    const hs = []; for (let h = hmin; h <= hmax; h++) hs.push(h);
    const cont = {};
    for (const [chave, g] of agrupar(linhas.filter((r) => r.Hora !== null), (r) => r.Dia_Semana + "|" + r.Hora))
      cont[chave] = new Set(g.map((r) => r.ID_Pedido)).size;
    const z = DIAS.map((d) => hs.map((h) => cont[d + "|" + h] || 0));
    mostrar("g-heat", [{
      type: "heatmap", z, x: hs.map((h) => h + "h"), y: DIAS, xgap: 3, ygap: 3,
      colorscale: [[0, "#FBF1E3"], [1, KETCHUP]],
      hovertemplate: "%{y} às %{x}<br>%{z} pedidos<extra></extra>",
      colorbar: { thickness: 10, outlinewidth: 0, title: { text: "" } },
    }], layout("Mapa de movimento: pedidos por dia e horário", { altura: 380, y: { autorange: "reversed", showgrid: false } }));
  }

  function graficoAbc(m) {
    const abc = m.abc;
    const itens = abc.slice(0, 10).map((x) => ({ nome: x.nome, p: x.participacao, a: x.classe_a }));
    const resto = abc.slice(10);
    if (resto.length) itens.push({ nome: `Demais (${resto.length} itens)`, p: soma(resto, (x) => x.participacao), a: false });
    const ordem = itens.map((x) => x.nome).reverse();
    const trace = (nome, cor, sel) => ({
      type: "bar", orientation: "h", name: nome,
      x: sel.map((x) => x.p), y: sel.map((x) => x.nome), marker: barra(cor),
      text: sel.map((x) => fmt(x.p, 1) + "%"), textposition: "outside", cliponaxis: false,
      hovertemplate: "%{y}<br>%{x:.1f}% do faturamento<extra></extra>",
    });
    const max = Math.max(...itens.map((x) => x.p));
    mostrar("g-abc", [
      trace("Itens que somam 80% do faturamento", KETCHUP, itens.filter((x) => x.a)),
      trace("Demais itens", AREIA, itens.filter((x) => !x.a)),
    ], layout("Quem sustenta o faturamento (participação por item)", {
      legenda: true, altura: 400, barmode: "overlay",
      x: { visible: false, range: [0, max * 1.2] }, y: { categoryorder: "array", categoryarray: ordem, showgrid: false },
    }));
  }

  function graficoItens(m) {
    if (!m.ped) { $("g-itens").innerHTML = ""; $("g-pares").innerHTML = ""; return; }
    const faixas = ["1 item", "2 itens", "3 itens", "4 ou mais"];
    const grupos = faixas.map((f, i) => {
      const g = m.ped.filter((p) => Math.min(p.itens, 4) === i + 1);
      return { f, n: g.length, ticket: g.length ? soma(g, (p) => p.valor) / g.length : 0 };
    }).filter((g) => g.n);
    const total = soma(grupos, (g) => g.n);
    const ys = grupos.map((g) => (g.n / total) * 100);
    mostrar("g-itens", [{
      type: "bar", x: grupos.map((g) => g.f), y: ys, marker: barra(MOSTARDA),
      text: grupos.map((g, i) => `${fmt(ys[i], 0)}% · ticket ${brl(g.ticket)}`), textposition: "outside", cliponaxis: false,
      hovertemplate: "%{x}<br>%{y:.1f}% dos pedidos<extra></extra>",
    }], layout("Pedidos por número de itens (e ticket médio de cada grupo)", {
      altura: 270, y: { visible: false, range: [0, Math.max(...ys) * 1.3] },
    }));
    if (m.pares && m.pares.length) {
      const pares = m.pares.map(([[a, b], n]) => ({ nome: `${a} + ${b}`, n })).reverse();
      mostrar("g-pares", [{
        type: "bar", orientation: "h", x: pares.map((p) => p.n), y: pares.map((p) => p.nome), marker: barra(KETCHUP),
        text: pares.map((p) => p.n), textposition: "outside", cliponaxis: false,
        hovertemplate: "%{y}<br>%{x} pedidos<extra></extra>",
      }], layout("Combinações mais pedidas juntas", { altura: 300, x: { range: [0, Math.max(...pares.map((p) => p.n)) * 1.15] } }));
    } else $("g-pares").innerHTML = "";
  }

  function graficoTendencia(linhas) {
    const dia = I.diario(linhas);
    const v = dia.map((d) => d.v);
    const ma = v.map((_, i) => {
      const j = v.slice(Math.max(0, i - 6), i + 1);
      return j.length >= 4 ? j.reduce((a, b) => a + b, 0) / j.length : null;
    });
    mostrar("g-tend", [
      { type: "scatter", mode: "lines", name: "Dia", x: dia.map((d) => d.data), y: v, opacity: 0.3,
        line: { color: KETCHUP, width: 1 }, hovertemplate: "%{x|%d/%m/%Y}<br>R$ %{y:,.2f}<extra></extra>" },
      { type: "scatter", mode: "lines", name: "Média de 7 dias", x: dia.map((d) => d.data), y: ma,
        line: { color: KETCHUP, width: 3 }, hovertemplate: "%{x|%d/%m/%Y}<br>média R$ %{y:,.2f}<extra></extra>" },
    ], layout("Faturamento diário e tendência (média móvel de 7 dias)", { legenda: true, altura: 330 }));
  }

  function graficoTempo(linhas) {
    const dia = I.diario(linhas);
    const porDow = new Map();
    for (const d of dia) {
      const i = (new Date(d.data + "T00:00:00Z").getUTCDay() + 6) % 7;
      if (!porDow.has(i)) porDow.set(i, []);
      porDow.get(i).push(d.v);
    }
    const med = DIAS.map((_, i) => (porDow.has(i) ? porDow.get(i).reduce((a, b) => a + b, 0) / porDow.get(i).length : null));
    mostrar("g-dow", [{ type: "bar", x: DIAS, y: med, marker: barra(KETCHUP),
      hovertemplate: "%{x}<br>média R$ %{y:,.2f} por dia<extra></extra>" }],
      layout("Faturamento médio por dia da semana"));

    const porHora = I.agrupar(linhas.filter((r) => r.Hora !== null), (r) => r.Hora);
    const horas = [...porHora.keys()].sort((a, b) => a - b);
    mostrar("g-hora", [{ type: "bar", x: horas, y: horas.map((h) => new Set(porHora.get(h).map((r) => r.ID_Pedido)).size),
      marker: barra(MOSTARDA), hovertemplate: "%{x}h<br>%{y} pedidos<extra></extra>" }],
      layout("Pedidos por horário", { x: { dtick: 1 } }));

    const meses = [...I.agrupar(linhas, (r) => r.Mes)].sort((a, b) => (a[0] < b[0] ? -1 : 1));
    if (meses.length > 1) {
      mostrar("g-mes", [{ type: "bar", x: meses.map(([k]) => mesPt(k)), y: meses.map(([, g]) => soma(g, (r) => r.Valor_Total)),
        width: meses.map(() => 0.45), marker: barra(KETCHUP), hovertemplate: "%{x}<br>R$ %{y:,.2f}<extra></extra>" }],
        layout("Faturamento por mês", { altura: 300, x: { type: "category" } }));
    } else $("g-mes").innerHTML = "";
  }

  function tabelaProdutos(linhas, m) {
    const classeA = new Set(m.abc.filter((x) => x.classe_a).map((x) => x.nome));
    const g = [...agrupar(linhas, (r) => r.Produto)].map(([nome, rs]) => ({
      nome, qtd: soma(rs, (r) => r.Quantidade), fat: soma(rs, (r) => r.Valor_Total) }));
    g.sort((a, b) => b.fat - a.fat);
    const total = soma(g, (x) => x.fat), maxP = Math.max(...g.map((x) => (x.fat / total) * 100));
    $("tabelaProdutos").innerHTML = `<thead><tr><th>Produto</th><th class="num">Quantidade</th><th class="num">Faturamento</th><th>Participação</th></tr></thead><tbody>` +
      g.map((x) => { const p = (x.fat / total) * 100;
        return `<tr><td>${esc(x.nome)}${classeA.has(x.nome) ? "" : ""}</td><td class="num">${fmt(x.qtd, 0)}</td><td class="num">${brl(x.fat)}</td>` +
          `<td><div class="barra"><div class="trilho"><i style="width:${(p / maxP) * 100}%"></i></div><span>${fmt(p, 1)}%</span></div></td></tr>`; }).join("") + "</tbody>";
  }

  function graficosCardapio(linhas, m) {
    const g = [...agrupar(linhas, (r) => r.Produto)].map(([nome, rs]) => ({ nome, qtd: soma(rs, (r) => r.Quantidade) }));
    g.sort((a, b) => a.qtd - b.qtd);
    const top = g.slice(-10), low = g.slice(0, 5);
    const h = (id, arr, cor, titulo) => mostrar(id, [{ type: "bar", orientation: "h", x: arr.map((x) => x.qtd), y: arr.map((x) => x.nome),
      marker: barra(cor), hovertemplate: "%{y}<br>%{x} unidades<extra></extra>" }], layout(titulo, { y: { showgrid: false, categoryorder: "array", categoryarray: arr.map((x) => x.nome) } }));
    h("g-top", top, KETCHUP, "Top 10 mais vendidos (unidades)");
    h("g-low", low, AREIA, "5 menos vendidos (unidades)");
    rosca("g-cat", agrupar(linhas, (r) => r.Categoria), COR_CATEGORIA, "Participação das categorias no faturamento");
    tabelaProdutos(linhas, m);
  }

  function rosca(id, grupos, mapa, titulo) {
    const dados = [...grupos].map(([nome, rs]) => ({ nome, v: soma(rs, (r) => r.Valor_Total) })).sort((a, b) => b.v - a.v);
    let extra = 0;
    mostrar(id, [{
      type: "pie", hole: 0.58, labels: dados.map((d) => d.nome), values: dados.map((d) => d.v),
      marker: { colors: dados.map((d) => mapa[d.nome] || COR_EXTRA[extra++ % COR_EXTRA.length]), line: { color: CREME, width: 3 } },
      textinfo: "label+percent", insidetextorientation: "horizontal", sort: false,
      hovertemplate: "%{label}<br>R$ %{value:,.2f}<extra></extra>",
    }], layout(titulo, { legenda: true, altura: 420 }));
  }

  function tabelaQualidade() {
    $("tabelaQualidade").innerHTML = `<thead><tr><th>Verificação</th><th class="num">Quantidade</th></tr></thead><tbody>` +
      Object.entries(estado.relatorio).map(([k, v]) => `<tr><td>${esc(k)}</td><td class="num">${fmt(v, 0)}</td></tr>`).join("") + "</tbody>";
  }

  /* ---------- storytelling ---------- */
  function cartao(cap) {
    let corpo;
    if (!cap.pontos.length) corpo = '<div class="vazio">Dados insuficientes no período/filtros selecionados para este bloco.</div>';
    else {
      corpo = "<ul>" + cap.pontos.map((p) => `<li>${p}</li>`).join("") + "</ul>";
      if (cap.dica) corpo += `<div class="dica">💡 <b>Dica:</b> ${esc(cap.dica)}</div>`;
    }
    return `<div class="cap"><span class="tag">${cap.tag}</span><h3>${cap.titulo}</h3>${corpo}</div>`;
  }

  function renderResumo() {
    const m = estado.m, linhas = estado.filtrado;
    const prios = I.prioridades(m);
    $("prioridades").innerHTML = prios.length
      ? `<div class="resumo"><h3>Por onde começar</h3><ol>${prios.map((p) => `<li>${p}</li>`).join("")}</ol></div>` : "";
    I.capitulos(m).forEach((c, i) => { $("cap" + i).innerHTML = cartao(c); });
    graficoMapa(linhas); graficoAbc(m); graficoItens(m); graficoTendencia(linhas);
  }

  /* ---------- abas ---------- */
  function renderizarAba(nome) {
    if (!estado.sujo.has(nome)) return;
    estado.sujo.delete(nome);
    const linhas = estado.filtrado, m = estado.m;
    if (nome === "resumo") renderResumo();
    else if (nome === "tempo") graficoTempo(linhas);
    else if (nome === "cardapio") graficosCardapio(linhas, m);
    else if (nome === "pagamentos") rosca("g-pag", agrupar(linhas, (r) => r.Forma_Pagamento), COR_PAGAMENTO, "Faturamento por forma de pagamento");
    else if (nome === "qualidade") tabelaQualidade();
  }

  function trocarAba(nome) {
    estado.aba = nome;
    document.querySelectorAll(".aba").forEach((b) => {
      const ativa = b.dataset.aba === nome;
      b.classList.toggle("ativa", ativa); b.setAttribute("aria-selected", ativa);
    });
    document.querySelectorAll(".painel-aba").forEach((p) => { p.hidden = p.id !== "aba-" + nome; });
    renderizarAba(nome);
    requestAnimationFrame(() => document.querySelectorAll("#aba-" + nome + " .js-plotly-plot").forEach((g) => Plotly.Plots.resize(g)));
  }

  /* ---------- eventos ---------- */
  document.querySelectorAll(".aba").forEach((b) => b.addEventListener("click", () => trocarAba(b.dataset.aba)));
  ["dataIni", "dataFim"].forEach((id) => $(id).addEventListener("change", aplicar));
  document.addEventListener("change", (e) => { if (e.target.matches("input[data-grupo]")) aplicar(); });
  $("btnExemplo").addEventListener("click", () => carregarBuffer(base64ParaBuffer(window.EXEMPLO_XLSX_B64), true));
  $("arquivo").addEventListener("change", (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const leitor = new FileReader();
    leitor.onload = () => carregarBuffer(leitor.result, false);
    leitor.onerror = () => aviso("Não foi possível abrir o arquivo.", true);
    leitor.readAsArrayBuffer(f);
    e.target.value = "";
  });

  carregarBuffer(base64ParaBuffer(window.EXEMPLO_XLSX_B64), true);
})();
