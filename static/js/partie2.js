/**
 * partie2.js – Upload audio, FFT, filtrage rectangulaire
 */

var currentFilename    = null;
var currentSampleRate  = null;
var selectedFilterType = 'passband';
var origTimeData       = [];
var origAmpData        = [];
var origFftPath        = '';

document.addEventListener('DOMContentLoaded', function() {
  console.log('[P2] DOM chargé');
  initUploadZone();
  initFilterUI();
  drawMaskCanvas();
});

// ── Upload ────────────────────────────────────────────────────────────
function initUploadZone() {
  var zone  = document.getElementById('upload-zone');
  var input = document.getElementById('audio-upload');
  if (!input) return;

  input.addEventListener('change', function() {
    if (input.files && input.files[0]) uploadFile(input.files[0]);
  });

  if (zone) {
    zone.addEventListener('dragover', function(e) {
      e.preventDefault();
      zone.classList.add('dragover');
    });
    zone.addEventListener('dragleave', function() {
      zone.classList.remove('dragover');
    });
    zone.addEventListener('drop', function(e) {
      e.preventDefault();
      zone.classList.remove('dragover');
      if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0]);
    });
  }
}

function uploadFile(file) {
  console.log('[P2] Upload:', file.name, file.type, file.size);

  document.getElementById('upload-spinner').classList.remove('hidden');
  document.getElementById('file-info').classList.add('hidden');
  document.getElementById('original-plots').classList.add('hidden');
  document.getElementById('original-placeholder').classList.remove('hidden');
  document.getElementById('btn-filter').disabled = true;

  var formData = new FormData();
  formData.append('audio', file);

  fetch('/api/upload_audio', { method: 'POST', body: formData })
    .then(function(res) {
      console.log('[P2] Réponse upload HTTP:', res.status);
      return res.json();
    })
    .then(function(data) {
      document.getElementById('upload-spinner').classList.add('hidden');
      console.log('[P2] Données reçues:', data);

      if (!data.success) {
        showToast('Erreur : ' + data.error, 'error');
        return;
      }

      currentFilename  = data.filename;
      currentSampleRate = data.sample_rate;
      origTimeData     = data.time_data   || [];
      origAmpData      = data.amplitude   || [];
      origFftPath      = data.plot_fft    || '';

      // Infos fichier
      document.getElementById('info-filename').textContent = data.filename;
      document.getElementById('info-meta').textContent =
        data.sample_rate + ' Hz · ' + data.duration.toFixed(2) + 's';
      document.getElementById('file-info').classList.remove('hidden');

      // Graphiques – ajouter timestamp pour forcer le rechargement
      var ts = '?t=' + Date.now();
      document.getElementById('plot-time-orig').src = data.plot_time + ts;
      document.getElementById('plot-fft-orig').src  = data.plot_fft  + ts;
      document.getElementById('plot-fft-orig-cmp').src = data.plot_fft + ts;

      document.getElementById('original-placeholder').classList.add('hidden');
      document.getElementById('original-plots').classList.remove('hidden');

      // Bornes filtre
      var nyquist = data.sample_rate / 2;
      document.getElementById('fmax').max   = nyquist;
      document.getElementById('fmax').value = Math.min(3400, nyquist);

      document.getElementById('btn-filter').disabled = false;
      drawMaskCanvas();
      showToast('Fichier analysé ! Spectre FFT affiché.', 'success');
    })
    .catch(function(err) {
      document.getElementById('upload-spinner').classList.add('hidden');
      console.error('[P2] Erreur upload:', err);
      showToast('Erreur réseau : ' + err.message, 'error');
    });
}

// ── Interface filtre ──────────────────────────────────────────────────
function initFilterUI() {
  document.querySelectorAll('#filter-type-group .btn-choice').forEach(function(btn) {
    btn.addEventListener('click', function() {
      document.querySelectorAll('#filter-type-group .btn-choice').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      selectedFilterType = btn.dataset.value;
      updateFormulaDisplay();
      drawMaskCanvas();
    });
  });

  var fminEl = document.getElementById('fmin');
  var fmaxEl = document.getElementById('fmax');
  if (fminEl) fminEl.addEventListener('input', drawMaskCanvas);
  if (fmaxEl) fmaxEl.addEventListener('input', drawMaskCanvas);

  // Tabs
  document.querySelectorAll('.tab-btn').forEach(function(btn) {
    btn.addEventListener('click', function() {
      document.querySelectorAll('.tab-btn').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      document.querySelectorAll('.tab-content').forEach(function(c) { c.classList.add('hidden'); });
      var tabEl = document.getElementById('tab-' + btn.dataset.tab);
      if (tabEl) tabEl.classList.remove('hidden');
    });
  });

  var btnFilter = document.getElementById('btn-filter');
  if (btnFilter) btnFilter.addEventListener('click', applyFilter);
}

function updateFormulaDisplay() {
  var fmin = document.getElementById('fmin').value;
  var fmax = document.getElementById('fmax').value;
  var div  = document.getElementById('formula-display');
  if (!div) return;
  if (selectedFilterType === 'passband') {
    div.innerHTML = 'H(f) = 1 si ' + fmin + ' &le; |f| &le; ' + fmax + ' Hz <em>(passe-bande)</em>';
  } else {
    div.innerHTML = 'H&#773;(f) = 1 &minus; H(f) si ' + fmin + ' &le; |f| &le; ' + fmax + ' Hz <em>(coupe-bande)</em>';
  }
}

function drawMaskCanvas() {
  var canvas = document.getElementById('mask-canvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  canvas.width = canvas.offsetWidth || 360;
  var W = canvas.width, H = canvas.height;

  var fmin    = parseFloat(document.getElementById('fmin').value) || 0;
  var fmax    = parseFloat(document.getElementById('fmax').value) || 4000;
  var nyquist = currentSampleRate ? currentSampleRate / 2 : 8000;
  var pband   = selectedFilterType === 'passband';

  ctx.fillStyle = '#F5F0E8';
  ctx.fillRect(0, 0, W, H);

  var x1 = (fmin / nyquist) * W;
  var x2 = (fmax / nyquist) * W;

  if (pband) {
    ctx.fillStyle = 'rgba(229,220,207,0.9)';
    ctx.fillRect(0, 0, x1, H);
    ctx.fillRect(x2, 0, W - x2, H);
    ctx.fillStyle = 'rgba(8,145,178,0.18)';
    ctx.fillRect(x1, 0, x2 - x1, H);
    ctx.strokeStyle = '#06b6d4';
    ctx.lineWidth = 2;
    ctx.strokeRect(x1, 2, x2 - x1, H - 4);
  } else {
    ctx.fillStyle = 'rgba(8,145,178,0.12)';
    ctx.fillRect(0, 0, x1, H);
    ctx.fillRect(x2, 0, W - x2, H);
    ctx.fillStyle = 'rgba(220,38,38,0.15)';
    ctx.fillRect(x1, 0, x2 - x1, H);
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 2;
    ctx.strokeRect(x1, 2, x2 - x1, H - 4);
  }

  // Labels
  ctx.font = '10px monospace';
  ctx.fillStyle = '#78716C';
  ctx.fillText('0', 4, H - 4);
  ctx.fillText(Math.round(nyquist) + ' Hz', W - 60, H - 4);
  ctx.fillStyle = pband ? '#06b6d4' : '#ef4444';
  ctx.fillText(fmin + ' Hz', Math.max(2, x1 - 2), 12);
  ctx.fillText(fmax + ' Hz', Math.min(W - 60, x2 + 2), 12);

  updateFormulaDisplay();
}

// ── Application du filtre ─────────────────────────────────────────────
function applyFilter() {
  if (!currentFilename) {
    showToast('Chargez un fichier audio d\'abord.', 'error');
    return;
  }

  var fmin = parseFloat(document.getElementById('fmin').value);
  var fmax = parseFloat(document.getElementById('fmax').value);

  if (isNaN(fmin) || isNaN(fmax) || fmin >= fmax || fmin < 0) {
    showToast('Bornes invalides : fmin doit être < fmax et ≥ 0', 'error');
    return;
  }

  console.log('[P2] Filtrage:', currentFilename, fmin, fmax, selectedFilterType);

  document.getElementById('filter-spinner').classList.remove('hidden');
  document.getElementById('filtered-card').classList.add('hidden');
  document.getElementById('btn-filter').disabled = true;

  fetch('/api/filter_audio', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filename:    currentFilename,
      fmin:        fmin,
      fmax:        fmax,
      filter_type: selectedFilterType
    })
  })
  .then(function(res) {
    console.log('[P2] Réponse filtre HTTP:', res.status);
    return res.json();
  })
  .then(function(data) {
    document.getElementById('filter-spinner').classList.add('hidden');
    document.getElementById('btn-filter').disabled = false;
    console.log('[P2] Résultat filtre:', data);

    if (!data.success) {
      showToast('Erreur filtrage : ' + data.error, 'error');
      return;
    }

    var ts = '?t=' + Date.now();

    // Graphiques filtrés
    document.getElementById('plot-fft-filtered').src = data.plot_fft_filtered + ts;

    // Badge filtre
    var label = selectedFilterType === 'passband'
      ? 'Passe-bande [' + fmin + '–' + fmax + ' Hz]'
      : 'Coupe-bande [' + fmin + '–' + fmax + ' Hz]';
    var badge = document.getElementById('filter-badge-label');
    if (badge) badge.textContent = label;

    // Lecteur audio filtré
    var player = document.getElementById('filtered-player');
    if (player) player.src = data.filtered_url + ts;

    // Lien téléchargement
    var dl = document.getElementById('download-link');
    if (dl) {
      dl.href     = data.filtered_url;
      dl.download = data.filtered_filename;
    }

    // Dessin comparaison temporelle
    if (data.time_filtered && data.amp_filtered) {
      drawTemporalComparison(origTimeData, origAmpData, data.time_filtered, data.amp_filtered);
    }

    document.getElementById('filtered-card').classList.remove('hidden');
    showToast('Filtre appliqué ! Signal reconstruit par IFFT.', 'success');
  })
  .catch(function(err) {
    document.getElementById('filter-spinner').classList.add('hidden');
    document.getElementById('btn-filter').disabled = false;
    console.error('[P2] Erreur fetch filtre:', err);
    showToast('Erreur réseau : ' + err.message, 'error');
  });
}

function drawTemporalComparison(t1, a1, t2, a2) {
  var canvas = document.getElementById('compare-canvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  canvas.width = canvas.offsetWidth || 600;
  var W = canvas.width, H = canvas.height;

  ctx.fillStyle = '#F5F0E8';
  ctx.fillRect(0, 0, W, H);

  function drawSig(times, amps, color, label) {
    if (!times || !times.length) return;
    var tMax = times[times.length - 1] || 1;
    var aMax = 0;
    amps.forEach(function(v) { if (Math.abs(v) > aMax) aMax = Math.abs(v); });
    if (!aMax) aMax = 1;

    ctx.strokeStyle = color;
    ctx.lineWidth   = 1.2;
    ctx.globalAlpha = 0.85;
    ctx.beginPath();
    times.forEach(function(t, i) {
      var x = (t / tMax) * W;
      var y = H / 2 - (amps[i] / aMax) * (H / 2 - 10);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.globalAlpha = 1;

    ctx.fillStyle = color;
    ctx.font = '11px sans-serif';
    ctx.fillText(label, 8, label.includes('Avant') ? 14 : 28);
  }

  drawSig(t1, a1, '#7c3aed', '— Avant filtrage');
  drawSig(t2, a2, '#06b6d4', '— Après filtrage');

  // Ligne centrale
  ctx.strokeStyle = '#DDD8CE';
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(0, H / 2); ctx.lineTo(W, H / 2);
  ctx.stroke();
  ctx.setLineDash([]);
}