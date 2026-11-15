/* Métricas e textos de storytelling (mesma lógica de versao_python/insights.py).
 * Os textos descrevem o que os dados mostram e sugerem ações; não afirmam causas nem prometem resultados. */
(function (global) {
  "use strict";
  const { DIAS, soma } = global.Tratamento;
  const MIN_PEDIDOS = 30;

  const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const fmt = (v, casas) => v.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });
  const pct = (x, casas = 1) => fmt(x, casas) + "%";
  const brl = (v) => "R$ " + fmt(v, 2);
  const lista = (nomes) => {
    const n = nomes.map((x) => `<b>${esc(x)}</b>`);
    return n.length <= 1 ? n.join("") : n.slice(0, -1).join(", ") + " e " + n[n.length - 1];
  };
  const capitalize = (s) => (s ? s[0].toUpperCase() + s.slice(1).toLowerCase() : s);
  const NOMES_MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  const mesPt = (periodo) => { const [a, m] = periodo.split("-"); return `${NOMES_MES[+m - 1]}/${a}`; };
  const media = (a) => a.reduce((x, y) => x + y, 0) / a.length;

  /* agrupa linhas por chave */
  function agrupar(linhas, chave) {
    const m = new Map();
    for (const r of linhas) {
      const k = chave(r);
      if (!m.has(k)) m.set(k, []);
      m.get(k).push(r);
    }
    return m;
  }

  function pedidosDf(linhas) {
    const out = [];
    for (const [, g] of agrupar(linhas, (r) => r.ID_Pedido)) {
      out.push({
        itens: new Set(g.map((r) => r.Produto)).size,
        valor: soma(g, (r) => r.Valor_Total),
        bebida: g.some((r) => r.Categoria === "Bebidas"),
        lanche: g.some((r) => r.Categoria === "Lanches"),
      });
    }
    return out;
  }

  function curvaAbc(linhas) {
    const p = [...agrupar(linhas, (r) => r.Produto)].map(([nome, g]) => ({ nome, faturamento: soma(g, (r) => r.Valor_Total) }));
    p.sort((a, b) => b.faturamento - a.faturamento);
    const total = soma(p, (x) => x.faturamento);
    let acum = 0;
    for (const x of p) {
      x.participacao = total ? (x.faturamento / total) * 100 : 0;
      x.classe_a = acum < 80;
      acum += x.participacao;
    }
    return p;
  }

  function paresFrequentes(linhas, n = 6) {
    const cont = new Map();
    const ids = [...agrupar(linhas, (r) => r.ID_Pedido)];
    ids.sort((a, b) => (isNaN(a[0]) || isNaN(b[0]) ? (a[0] < b[0] ? -1 : 1) : a[0] - b[0]));
    for (const [, g] of ids) {
      const prods = [...new Set(g.map((r) => r.Produto))].sort();
      for (let i = 0; i < prods.length; i++)
        for (let j = i + 1; j < prods.length; j++) {
          const k = prods[i] + "\u0000" + prods[j];
          cont.set(k, (cont.get(k) || 0) + 1);
        }
    }
    return [...cont].sort((a, b) => b[1] - a[1]).slice(0, n)
      .map(([k, c]) => [k.split("\u0000"), c]);
  }

  /* soma diária por data (ordenada) */
  function diario(linhas) {
    const m = new Map();
    for (const r of linhas) m.set(r.Data, (m.get(r.Data) || 0) + r.Valor_Total);
    return [...m].sort((a, b) => (a[0] < b[0] ? -1 : 1)).map(([data, v]) => ({ data, v }));
  }

  function metricas(linhas) {
    const m = {};
    m.pedidos = new Set(linhas.map((r) => r.ID_Pedido)).size;
    const dia = diario(linhas);
    m.dias = dia.length;

    // horários de pico e de vale (janelas de 3 horas)
    const porHora = new Map();
    for (const [h, g] of agrupar(linhas.filter((r) => r.Hora !== null), (r) => r.Hora))
      porHora.set(h, new Set(g.map((r) => r.ID_Pedido)).size);
    if (porHora.size) {
      const hs = [...porHora.keys()];
      const hmin = Math.min(...hs), hmax = Math.max(...hs);
      const serie = [];
      for (let h = hmin; h <= hmax; h++) serie.push([h, porHora.get(h) || 0]);
      m.por_hora = serie;
      if (serie.length >= 7) {
        const jan = [];
        for (let i = 2; i < serie.length; i++) jan.push([serie[i][0], serie[i][1] + serie[i - 1][1] + serie[i - 2][1]]);
        let pico = jan[0];
        for (const j of jan) if (j[1] > pico[1]) pico = j;
        m.pico = [pico[0] - 2, pico[0] + 1, (pico[1] / m.pedidos) * 100];
        const interior = jan.filter((j) => j[0] - 2 >= hmin + 1 && j[0] <= hmax - 1);
        if (interior.length) {
          let vale = interior[0];
          for (const j of interior) if (j[1] < vale[1]) vale = j;
          m.vale = [vale[0] - 2, vale[0] + 1, (vale[1] / m.pedidos) * 100];
        }
      }
    }

    // dias da semana (média por dia)
    if (m.dias >= 14) {
      const porDow = new Map();
      for (const d of dia) {
        const dow = (new Date(d.data + "T00:00:00Z").getUTCDay() + 6) % 7;
        if (!porDow.has(dow)) porDow.set(dow, []);
        porDow.get(dow).push(d.v);
      }
      if (porDow.size >= 5) {
        const dd = [...porDow].map(([dow, v]) => [dow, media(v)]).sort((a, b) => a[0] - b[0]);
        let forte = dd[0], fraco = dd[0];
        for (const x of dd) { if (x[1] > forte[1]) forte = x; if (x[1] < fraco[1]) fraco = x; }
        m.dia_forte = [DIAS[forte[0]], forte[1]];
        m.dia_fraco = [DIAS[fraco[0]], fraco[1]];
        m.razao_dias = fraco[1] > 0 ? forte[1] / fraco[1] : null;
      }
    }

    // curva ABC
    m.abc = curvaAbc(linhas);
    m.n_a = m.abc.filter((x) => x.classe_a).length;
    m.n_itens = m.abc.length;
    m.cauda = m.abc.filter((x) => !x.classe_a && x.participacao < 2);
    m.cauda_total = soma(m.cauda, (x) => x.participacao);

    // como o cliente compra
    if (m.pedidos >= MIN_PEDIDOS) {
      const ped = pedidosDf(linhas);
      m.ped = ped;
      m.share_1item = (ped.filter((p) => p.itens === 1).length / ped.length) * 100;
      const um = ped.filter((p) => p.itens === 1), varios = ped.filter((p) => p.itens >= 2);
      if (um.length && varios.length) {
        m.ticket_1 = media(um.map((p) => p.valor));
        m.ticket_2mais = media(varios.map((p) => p.valor));
      }
      const lanche = ped.filter((p) => p.lanche);
      const bebidas = linhas.filter((r) => r.Categoria === "Bebidas");
      if (lanche.length >= MIN_PEDIDOS && bebidas.length) {
        const sem = lanche.filter((p) => !p.bebida).length;
        m.lanche_sem_bebida = sem;
        m.share_lanche_sem_bebida = (sem / lanche.length) * 100;
        m.preco_bebida = soma(bebidas, (r) => r.Valor_Total) / soma(bebidas, (r) => r.Quantidade);
        m.sim_10 = 0.1 * sem * m.preco_bebida;
      }
      m.pares = paresFrequentes(linhas);
    }

    // evolução
    const porMes = new Map();
    for (const d of dia) {
      const k = d.data.slice(0, 7);
      if (!porMes.has(k)) porMes.set(k, []);
      porMes.get(k).push(d.v);
    }
    const mm = [...porMes].filter(([, v]) => v.length >= 7).sort((a, b) => (a[0] < b[0] ? -1 : 1))
      .map(([k, v]) => [k, media(v)]);
    if (mm.length >= 2) {
      m.mes_ini = mm[0]; m.mes_fim = mm[mm.length - 1];
      m.cresc = (mm[mm.length - 1][1] / mm[0][1] - 1) * 100;
    }
    const inicio = dia.filter((d) => { const n = +d.data.slice(8); return n >= 5 && n <= 10; }).map((d) => d.v);
    const resto = dia.filter((d) => { const n = +d.data.slice(8); return !(n >= 5 && n <= 10); }).map((d) => d.v);
    if (inicio.length >= 6 && resto.length >= 14 && media(resto) > 0)
      m.inicio_mes = (media(inicio) / media(resto) - 1) * 100;
    return m;
  }

  function capitulos(m) {
    const caps = [];
    const montar = (tag, titulo, pontos, dica) =>
      caps.push({ tag, titulo, pontos, dica: dica.length ? capitalize(dica.join("; ")) + "." : "" });

    // 1) Quando
    let pts = [], dica = [];
    if (m.pico) {
      const [s, e, p] = m.pico;
      pts.push(`<b>${pct(p, 0)}</b> dos pedidos se concentram entre <b>${s}h e ${e}h</b>, a janela de maior movimento.`);
      dica.push(`reforce equipe e estoque entre ${s}h e ${e}h, quando o movimento é maior`);
    }
    if (m.vale) {
      const [s, e, p] = m.vale;
      pts.push(`Entre <b>${s}h e ${e}h</b> ficam só <b>${pct(p, 0)}</b> dos pedidos: é a faixa mais ociosa.`);
      dica.push(`teste uma oferta leve entre ${s}h e ${e}h (combo ou café com salgado) para ocupar a capacidade ociosa`);
    }
    if (m.dia_forte && m.razao_dias) {
      pts.push(`<b>${m.dia_forte[0]}</b> é o dia mais forte (média de ${brl(m.dia_forte[1])} por dia), ` +
        `cerca de <b>${fmt(Math.round(m.razao_dias * 10) / 10, 1)}×</b> o de <b>${m.dia_fraco[0].toLowerCase()}</b>.`);
      dica.push(`planeje compras e escala pelo calendário e use ${m.dia_fraco[0].toLowerCase()} para divulgar promoções`);
    }
    montar("Quando vender", "Quando a lanchonete mais vende?", pts, dica);

    // 2) O que vende
    pts = []; dica = [];
    if (m.n_itens >= 5) {
      pts.push(`<b>${m.n_a} de ${m.n_itens}</b> itens geram 80% do faturamento. Lideram: ${lista(m.abc.slice(0, 3).map((x) => x.nome))}.`);
      dica.push("proteja estoque e qualidade dos itens líderes, que sustentam o caixa");
      if (m.cauda.length) {
        const nomes = [...m.cauda].sort((a, b) => a.participacao - b.participacao).slice(0, 4).map((x) => x.nome);
        pts.push(`<b>${m.cauda.length}</b> itens têm menos de 2% do faturamento cada (somam ${pct(m.cauda_total)}): ${lista(nomes)}.`);
        dica.push("avalie combinar, reposicionar ou retirar os itens de baixa participação, olhando também a margem de cada um (não disponível nesta planilha)");
      }
    }
    montar("O que vende", "O que sustenta o faturamento?", pts, dica);

    // 3) Como compra
    pts = []; dica = [];
    if (m.share_1item !== undefined) {
      if (m.ticket_1 !== undefined) {
        pts.push(`<b>${pct(m.share_1item, 0)}</b> dos pedidos têm um único item (ticket médio de ${brl(m.ticket_1)}), ` +
          `contra <b>${brl(m.ticket_2mais)}</b> nos pedidos com 2 ou mais itens.`);
        dica.push("treine o atendimento para sugerir um item a mais no caixa");
      }
      if (m.share_lanche_sem_bebida !== undefined) {
        pts.push(`<b>${pct(m.share_lanche_sem_bebida, 0)}</b> dos pedidos com lanche saem sem bebida.`);
        dica.push("crie um combo lanche + bebida");
        pts.push(`Simulação: se 10% desses pedidos incluíssem uma bebida (média de ${brl(m.preco_bebida)}), ` +
          `seriam cerca de <b>${brl(m.sim_10)}</b> a mais no período (estimativa simples, sem custos).`);
      }
      if (m.pares && m.pares.length) {
        const [[a, b], n] = m.pares[0];
        pts.push(`O par mais pedido junto é ${lista([a, b])} (${n} pedidos).`);
        dica.push("transforme os pares mais frequentes em combos com preço atrativo");
      }
    }
    montar("Como o cliente compra", "Como o cliente monta o pedido?", pts, dica);

    // 4) Evolução
    pts = []; dica = [];
    if (m.cresc !== undefined) {
      const [m1, v1] = m.mes_ini, [m2, v2] = m.mes_fim;
      const verbo = m.cresc >= 0 ? "subiu" : "caiu";
      pts.push(`A média diária de faturamento ${verbo} de <b>${brl(v1)}</b> (${mesPt(m1)}) para <b>${brl(v2)}</b> ` +
        `(${mesPt(m2)}): <b>${m.cresc >= 0 ? "+" : ""}${pct(m.cresc)}</b>.`);
      dica.push("acompanhe esse indicador todo mês para saber se as ações estão funcionando");
    }
    if (m.inicio_mes !== undefined) {
      const sinal = m.inicio_mes >= 0 ? "maior" : "menor";
      pts.push(`Nos dias 5 a 10 de cada mês, a média diária foi <b>${pct(Math.abs(m.inicio_mes))} ${sinal}</b> ` +
        `que nos demais dias, período em que costuma haver mais renda circulando.`);
      dica.push("antecipe estoque e destaque promoções nessa janela, e confira se o padrão se repete nos próximos meses");
    }
    montar("Evolução", "Para onde o negócio caminha?", pts, dica);
    return caps;
  }

  function prioridades(m) {
    const itens = [];
    if (m.share_lanche_sem_bebida !== undefined)
      itens.push(`Testar um <b>combo lanche + bebida</b>: ${pct(m.share_lanche_sem_bebida, 0)} dos pedidos com lanche saem sem bebida.`);
    if (m.vale) {
      const [s, e, p] = m.vale;
      itens.push(`Criar uma <b>oferta para a faixa das ${s}h às ${e}h</b>, hoje com só ${pct(p, 0)} dos pedidos.`);
    }
    if (m.cauda.length)
      itens.push(`Revisar os <b>${m.cauda.length} itens de baixa participação</b> (menos de 2% do faturamento cada).`);
    if (m.pico && itens.length < 3) {
      const [s, e] = m.pico;
      itens.push(`Reforçar <b>equipe e estoque entre ${s}h e ${e}h</b>, o horário de maior movimento.`);
    }
    return itens.slice(0, 3);
  }

  global.Insights = { metricas, capitulos, prioridades, esc, fmt, pct, brl, mesPt, agrupar, diario };
})(window);
