// ===================================================================
// app.js — Tradutor Pro
// Rotas usadas:
//   POST /translate          -> translation.py
//   POST /upload             -> upload.py
//   GET  /download/{arquivo} -> download.py
// ===================================================================

const orbWrap          = document.getElementById('orbWrap');
const statusBar        = document.getElementById('statusBar');
const sourceText       = document.getElementById('sourceText');
const targetText       = document.getElementById('targetText');
const charCount        = document.getElementById('charCount');
const btnTranslateText = document.getElementById('btnTranslateText');
const btnDownload      = document.getElementById('btnDownload');
const btnExport        = document.getElementById('btnExport');

let lastTranslatedFilename = null; // nome do arquivo no servidor (ex: "livro_traduzido.pdf")
let lastTranslatedText     = null; // texto traduzido inline (sem arquivo)

sourceText.addEventListener('input', () => {
  charCount.textContent = sourceText.value.length;
});

document.getElementById('swapBtn').addEventListener('click', () => {
  const a = document.getElementById('fromLang');
  const b = document.getElementById('toLang');
  if (a.value !== 'auto') {
    const tmp = a.value; a.value = b.value; b.value = tmp;
  }
});

function setBusy(on, message) {
  orbWrap.classList.toggle('is-busy', on);
  statusBar.textContent = message || '';
  statusBar.classList.remove('success');
}

// ===================================================================
// 1) TRADUÇÃO DE TEXTO (sem arquivo)
// ===================================================================
btnTranslateText.addEventListener('click', async () => {
  const text = sourceText.value.trim();
  if (!text) { statusBar.textContent = 'Digite algum texto para traduzir.'; return; }

  const source = document.getElementById('fromLang').value;
  const target = document.getElementById('toLang').value;

  setBusy(true, 'Traduzindo texto...');
  btnTranslateText.disabled = true;

  try {
    const res = await fetch('/translate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, source, target }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.erro || 'Falha ao traduzir.');
    }
    const data = await res.json();
    targetText.value       = data.translated_text;
    lastTranslatedText     = data.translated_text;
    lastTranslatedFilename = null;

    setBusy(false, 'Tradução concluída.');
    statusBar.classList.add('success');
    btnDownload.disabled = false;
    btnExport.disabled   = false;
  } catch (e) {
    setBusy(false, e.message || 'Erro ao traduzir texto.');
  } finally {
    btnTranslateText.disabled = false;
  }
});

// ===================================================================
// 2) UPLOAD DE ARQUIVOS
// ===================================================================
const dropzone          = document.getElementById('dropzone');
const fileInput         = document.getElementById('fileInput');
const fileList          = document.getElementById('fileList');
const btnTranslateFiles = document.getElementById('btnTranslateFiles');
const fromLangSelect    = document.getElementById('fromLang');
const toLangSelect      = document.getElementById('toLang');
let files = [];

// --- Modal de idiomas -------------------------------------------------
const langModalOverlay = document.getElementById('langModalOverlay');
const langModalClose   = document.getElementById('langModalClose');
const langModalConfirm = document.getElementById('langModalConfirm');
const modalFromLang    = document.getElementById('modalFromLang');
const modalToLang      = document.getElementById('modalToLang');
let pendingFiles = null;

function openLangModal(fl) {
  pendingFiles = fl;
  // pré-seleciona com o que já está nos campos do painel de texto, se aplicável
  if ([...modalFromLang.options].some(o => o.value === fromLangSelect.value)) {
    modalFromLang.value = fromLangSelect.value === 'auto' ? 'en' : fromLangSelect.value;
  }
  if ([...modalToLang.options].some(o => o.value === toLangSelect.value)) {
    modalToLang.value = toLangSelect.value;
  }
  langModalOverlay.classList.add('is-open');
}

function closeLangModal() {
  langModalOverlay.classList.remove('is-open');
  pendingFiles = null;
  fileInput.value = ''; // permite re-selecionar o mesmo arquivo depois
}

langModalClose.addEventListener('click', closeLangModal);
langModalOverlay.addEventListener('click', e => {
  if (e.target === langModalOverlay) closeLangModal();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && langModalOverlay.classList.contains('is-open')) closeLangModal();
});

langModalConfirm.addEventListener('click', () => {
  if (!pendingFiles) return;

  // sincroniza a escolha do modal com os seletores principais
  fromLangSelect.value = modalFromLang.value;
  toLangSelect.value   = modalToLang.value;

  const fl = pendingFiles;
  langModalOverlay.classList.remove('is-open');
  pendingFiles = null;

  addFiles(fl);
  translateFiles();
});

function fmtSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

function renderFiles() {
  fileList.innerHTML = '';
  files.forEach((f, i) => {
    const item = document.createElement('div');
    item.className = 'file-item';
    item.innerHTML = `
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
      <span class="fname">${f.name}</span>
      <span class="fsize">${fmtSize(f.size)}</span>
      <button class="remove" data-i="${i}" title="Remover">✕</button>
    `;
    fileList.appendChild(item);
  });
  btnTranslateFiles.disabled = files.length === 0;
}

function addFiles(fl) {
  Array.from(fl).forEach(f => files.push(f));
  renderFiles();
}

// Em vez de adicionar o arquivo direto, abre o modal de idiomas primeiro
fileInput.addEventListener('change', e => {
  if (e.target.files.length) openLangModal(e.target.files);
});

['dragenter','dragover'].forEach(evt =>
  dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.add('drag-over'); })
);
['dragleave','drop'].forEach(evt =>
  dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.remove('drag-over'); })
);
dropzone.addEventListener('drop', e => {
  if (e.dataTransfer.files.length) openLangModal(e.dataTransfer.files);
});

fileList.addEventListener('click', e => {
  if (e.target.classList.contains('remove')) {
    files.splice(Number(e.target.dataset.i), 1);
    renderFiles();
  }
});

async function translateFiles() {
  if (!files.length) return;

  const source = fromLangSelect.value;
  const target = toLangSelect.value;

  setBusy(true, `Traduzindo ${files.length} arquivo(s)... isso pode levar alguns minutos.`);
  btnTranslateFiles.disabled = true;

  try {
    let lastFilename = null;

    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('source', source);
      formData.append('target', target);

      const res = await fetch('/upload', { method: 'POST', body: formData });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.erro || `Falha ao traduzir ${file.name}.`);
      }

      const data = await res.json();

      // upload.py retorna { mensagem, arquivo_traduzido, preview }
      // arquivo_traduzido = nome do melhor arquivo disponível (PDF ou TXT)
      lastFilename = data.arquivo_traduzido;
    }

    lastTranslatedFilename = lastFilename;
    lastTranslatedText     = null;

    if (!lastTranslatedFilename) {
      setBusy(false, '⚠️ Tradução concluída, mas o servidor não retornou o nome do arquivo.');
      return;
    }

    setBusy(false, '✅ Tradução concluída! Clique em Download para baixar.');
    statusBar.classList.add('success');
    btnDownload.disabled = false;
    btnExport.disabled   = false;

  } catch (e) {
    setBusy(false, e.message || 'Erro ao traduzir arquivos.');
  } finally {
    btnTranslateFiles.disabled = false;
  }
}

btnTranslateFiles.addEventListener('click', translateFiles);

// ===================================================================
// 3) DOWNLOAD
// ===================================================================

function downloadAsTextFile(text, filename) {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function doDownload() {
  if (lastTranslatedFilename) {
    // Cria um link invisível e clica — mais confiável que window.open
    // (evita bloqueio de popup e funciona em todos os navegadores)
    const url = `/download/${encodeURIComponent(lastTranslatedFilename)}`;
    const a   = document.createElement('a');
    a.href    = url;
    a.download = lastTranslatedFilename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } else if (lastTranslatedText) {
    downloadAsTextFile(lastTranslatedText, 'traducao.txt');
  } else {
    statusBar.textContent = 'Nada para baixar ainda. Traduza um arquivo primeiro.';
  }
}

btnDownload.addEventListener('click', () => {
  statusBar.textContent = 'Preparando download...';
  statusBar.classList.remove('success');
  doDownload();
});

btnExport.addEventListener('click', () => {
  statusBar.textContent = 'Exportando resultado...';
  statusBar.classList.remove('success');
  doDownload();
});