// ==========================================
// CONFIGURAÇÃO APENAS PARA A ABA "GB"
// ==========================================
const CONFIG_GB = {
  PASTA_DRIVE_ID: "0AEUY-NNQ293bUk9PVA",
  NOME_ABA: "GB",
  DELIMITADOR: ",",
  
  ARQUIVOS: {
    CONFORMIDADE: "Conformidade",
    CONVERSACAO: "Conversação média",
    TRATAMENTO: "Tratamento médio e espera média"
  }
};

// ==========================================
// FUNÇÃO PRINCIPAL (Rode esta)
// ==========================================
function atualizarSomenteGB() {
  const planilha = SpreadsheetApp.getActiveSpreadsheet();
  let aba = planilha.getSheetByName(CONFIG_GB.NOME_ABA);

  // Cria a aba GB se não existir
  if (!aba) {
    aba = planilha.insertSheet(CONFIG_GB.NOME_ABA);
    aba.appendRow(["Data Importação", "Conformidade", "Conversação Média", "Tratamento Médio", "Espera Média", "TPC Médio"]);
    aba.setFrozenRows(1);
  }

  const pasta = DriveApp.getFolderById(CONFIG_GB.PASTA_DRIVE_ID);

  // --- 1. CONFORMIDADE (Pega o último dado registrado) ---
  let valConformidade = "-";
  const arqConf = buscarArquivo(pasta, CONFIG_GB.ARQUIVOS.CONFORMIDADE);
  if (arqConf) {
    valConformidade = extrairUltimoValor(lerCSV(arqConf), "Conformidade");
  }

  // --- 2. CONVERSAÇÃO (Calcula Média da Equipe) ---
  let valConversacao = "-";
  const arqConv = buscarArquivo(pasta, CONFIG_GB.ARQUIVOS.CONVERSACAO);
  if (arqConv) {
    valConversacao = calcularMediaEquipe(lerCSV(arqConv), "Conversação média");
  }

  // --- 3. TRATAMENTO, ESPERA E TPC (Calcula Média da Equipe) ---
  let valTratamento = "-", valEspera = "-", valTPC = "-";
  const arqTrat = buscarArquivo(pasta, CONFIG_GB.ARQUIVOS.TRATAMENTO);
  if (arqTrat) {
    const dados = lerCSV(arqTrat);
    valTratamento = calcularMediaEquipe(dados, "Tratamento médio");
    valEspera = calcularMediaEquipe(dados, "Espera média");
    valTPC = calcularMediaEquipe(dados, "TPC médio");
  }

  // --- 4. GRAVAR DADOS ---
  const dataHoje = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "dd/MM/yyyy HH:mm");
  
  aba.appendRow([
    dataHoje,
    valConformidade,
    valConversacao,
    valTratamento,
    valEspera,
    valTPC
  ]);
  
  Logger.log("✅ Aba GB atualizada com sucesso!");
}

// ==========================================
// FUNÇÕES AUXILIARES
// ==========================================

function buscarArquivo(pasta, nomeParcial) {
  const arquivos = pasta.getFiles();
  let arqRecente = null;
  let dataRecente = new Date(0);
  while (arquivos.hasNext()) {
    let a = arquivos.next();
    if (a.getName().includes(nomeParcial) && !a.isTrashed() && a.getDateCreated() > dataRecente) {
      dataRecente = a.getDateCreated();
      arqRecente = a;
    }
  }
  return arqRecente;
}

function lerCSV(arquivo) {
  return Utilities.parseCsv(arquivo.getBlob().getDataAsString(), CONFIG_GB.DELIMITADOR);
}

function extrairUltimoValor(dados, nomeColuna) {
  if (dados.length < 2) return "-";
  const i = dados[0].indexOf(nomeColuna);
  if (i < 0) return "-";
  for (let x = dados.length - 1; x > 0; x--) {
    if (dados[x][i]) return dados[x][i];
  }
  return "-";
}

function calcularMediaEquipe(dados, nomeColuna) {
  if (dados.length < 2) return "-";
  const i = dados[0].indexOf(nomeColuna);
  if (i < 0) return "-";
  
  let total = 0, count = 0;
  for (let x = 1; x < dados.length; x++) {
    if (dados[x][i] && dados[x][i] !== "-" && dados[x][i] !== "nan") {
      total += textoParaSegundos(dados[x][i]);
      count++;
    }
  }
  return count === 0 ? "-" : segundosParaTexto(total / count);
}

function textoParaSegundos(t) {
  if (!t) return 0;
  let s = 0;
  const h = t.match(/(\d+)h/), m = t.match(/(\d+)m/), sc = t.match(/(\d+)s/);
  if (h) s += parseInt(h[1]) * 3600;
  if (m) s += parseInt(m[1]) * 60;
  if (sc) s += parseInt(sc[1]);
  return s;
}

function segundosParaTexto(s) {
  let h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sc = Math.round(s % 60);
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${sc.toString().padStart(2, '0')}`;
}
