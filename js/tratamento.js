/* Leitura, validação e cálculo de indicadores da base de vendas.
 * Mesmas regras da versão em Python (versao_python/tratamento.py). */
(function (global) {
  "use strict";

  const DIAS = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"];
  const COLUNAS_OBRIGATORIAS = ["ID_Pedido", "Data", "Horario", "Produto", "Categoria",
    "Quantidade", "Valor_Unitario", "Valor_Total", "Forma_Pagamento"];

  const vazio = (v) => v === null || v === undefined || (typeof v === "number" && Number.isNaN(v)) ||
    (typeof v === "string" && v.trim() === "");

  function numero(v) {
    if (vazio(v)) return null;
    if (typeof v === "number") return Number.isFinite(v) ? v : null;
    let s = String(v).trim().replace(/^R\$\s*/, "");
    if (s.includes(",")) s = s.replace(/\./g, "").replace(",", ".");
    const n = Number(s);
    return Number.isFinite(n) ? n : null;
  }

  const pad = (n) => String(n).padStart(2, "0");

  /* Converte data (serial do Excel, Date, "AAAA-MM-DD" ou "DD/MM/AAAA") em "AAAA-MM-DD", sem fuso horário. */
  function dataISO(v) {
    if (vazio(v)) return null;
    let y, m, d;
    if (typeof v === "number") {
      const t = new Date(Math.round((v - 25569) * 86400000));
      y = t.getUTCFullYear(); m = t.getUTCMonth() + 1; d = t.getUTCDate();
    } else if (v instanceof Date) {
      y = v.getFullYear(); m = v.getMonth() + 1; d = v.getDate();
    } else {
      const s = String(v).trim();
      let r = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
      if (r) { y = +r[1]; m = +r[2]; d = +r[3]; }
      else if ((r = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/))) { d = +r[1]; m = +r[2]; y = +r[3]; }
      else return null;
    }
    const chk = new Date(Date.UTC(y, m - 1, d));
    if (chk.getUTCFullYear() !== y || chk.getUTCMonth() !== m - 1 || chk.getUTCDate() !== d) return null;
    return `${y}-${pad(m)}-${pad(d)}`;
  }

  function horaDe(v) {
    if (vazio(v)) return null;
    if (typeof v === "number") return v >= 0 && v < 1 ? Math.floor(v * 24 + 1e-9) : null;
    const r = String(v).trim().match(/^(\d{1,2}):(\d{2})/);
    return r && +r[1] < 24 ? +r[1] : null;
  }

  /* 0 = segunda ... 6 = domingo */
  function diaDaSemana(iso) {
    const [y, m, d] = iso.split("-").map(Number);
    return (new Date(Date.UTC(y, m - 1, d)).getUTCDay() + 6) % 7;
  }

  function lerPlanilha(buffer) {
    const wb = XLSX.read(buffer, { type: "array", cellDates: false });
    const ws = wb.Sheets[wb.SheetNames[0]];
    const linhas = XLSX.utils.sheet_to_json(ws, { defval: null, raw: true });
    if (!linhas.length) throw new Error("A planilha está vazia.");
    const cols = Object.keys(linhas[0]);
    const faltando = COLUNAS_OBRIGATORIAS.filter((c) => !cols.includes(c));
    if (faltando.length) throw new Error("Colunas obrigatórias ausentes: " + faltando.join(", "));
    return linhas;
  }

  function tratar(brutas) {
    const rel = { "Linhas lidas": brutas.length };

    // 1) tipos
    let linhas = brutas.map((r) => ({
      ID_Pedido: vazio(r.ID_Pedido) ? null : String(r.ID_Pedido).trim(),
      Data: dataISO(r.Data),
      Horario: vazio(r.Horario) ? null : r.Horario,
      Produto: vazio(r.Produto) ? null : String(r.Produto).trim(),
      Categoria: vazio(r.Categoria) ? null : String(r.Categoria).trim(),
      Quantidade: numero(r.Quantidade),
      Valor_Unitario: numero(r.Valor_Unitario),
      Valor_Total: numero(r.Valor_Total),
      Forma_Pagamento: vazio(r.Forma_Pagamento) ? null : String(r.Forma_Pagamento).trim(),
    }));

    // 2) duplicadas
    const vistos = new Set();
    const semDup = [];
    for (const r of linhas) {
      const k = JSON.stringify([r.ID_Pedido, r.Data, r.Horario, r.Produto, r.Categoria,
        r.Quantidade, r.Valor_Unitario, r.Valor_Total, r.Forma_Pagamento]);
      if (vistos.has(k)) continue;
      vistos.add(k); semDup.push(r);
    }
    rel["Linhas duplicadas removidas"] = linhas.length - semDup.length;
    linhas = semDup;

    // 3) valor total ausente é recalculado (quantidade x unitário)
    let recalc = 0;
    for (const r of linhas) {
      if (r.Valor_Total === null && r.Quantidade !== null && r.Quantidade > 0 && r.Valor_Unitario !== null) {
        r.Valor_Total = r.Quantidade * r.Valor_Unitario; recalc++;
      }
    }
    rel["Valor total recalculado (qtd x unitário)"] = recalc;

    // 4) inválidas
    const invalida = (r) => r.Data === null || r.Produto === null || r.Quantidade === null ||
      r.Quantidade <= 0 || r.Valor_Total === null || r.Valor_Total < 0;
    const antes = linhas.length;
    linhas = linhas.filter((r) => !invalida(r));
    rel["Linhas inválidas removidas"] = antes - linhas.length;

    // 5) pagamento ausente
    let semPg = 0;
    for (const r of linhas) {
      if (r.Forma_Pagamento === null) { r.Forma_Pagamento = "Não informado"; semPg++; }
    }
    rel["Forma de pagamento não informada"] = semPg;

    // 6) colunas derivadas
    for (const r of linhas) {
      r.Hora = horaDe(r.Horario);
      r.DiaIdx = diaDaSemana(r.Data);
      r.Dia_Semana = DIAS[r.DiaIdx];
      r.Mes = r.Data.slice(0, 7);
      if (r.Categoria === null) r.Categoria = "Sem categoria";
      if (r.ID_Pedido === null) r.ID_Pedido = "sem-id-" + r.Data + "-" + r.Hora;
    }
    rel["Linhas utilizadas"] = linhas.length;
    return { base: linhas, relatorio: rel };
  }

  const soma = (arr, f) => arr.reduce((a, r) => a + f(r), 0);

  function indicadores(linhas) {
    const faturamento = soma(linhas, (r) => r.Valor_Total);
    const pedidos = new Set(linhas.map((r) => r.ID_Pedido)).size;
    return {
      faturamento, pedidos,
      ticket_medio: pedidos ? faturamento / pedidos : 0,
      itens: soma(linhas, (r) => r.Quantidade),
    };
  }

  global.Tratamento = { DIAS, COLUNAS_OBRIGATORIAS, lerPlanilha, tratar, indicadores, soma };
})(window);
