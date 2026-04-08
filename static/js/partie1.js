/**
 * partie1.js – Enregistrement microphone et segmentation
 * Utilise l'API MediaRecorder du navigateur
 */

// ── État global ──────────────────────────────────────────────────────
let mediaRecorder  = null;
let audioChunks    = [];
let audioBlob      = null;
let timerInterval  = null;
let timerSeconds   = 0;
let animFrame      = null;
let audioCtx       = null;
let analyser       = null;

let selectedSampleRate = 16000;
let selectedBitDepth   = 16;

// ── DOM Ready ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  console.log('[P1] DOM chargé');
  initButtonGroups();
  initRecorderButtons();
  initSegmentationUI();
  loadRecordingsList();
  drawIdleWaveform();
});

// ── Groupes de boutons ────────────────────────────────────────────────
function initButtonGroups() {
  document.querySelectorAll('#sr-group .btn-choice').forEach(function(btn) {
    btn.addEventListener('click', function() {
      document.querySelectorAll('#sr-group .btn-choice').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      selectedSampleRate = parseInt(btn.dataset.value);
      console.log('[P1] Sample rate:', selectedSampleRate);
    });
  });

  document.querySelectorAll('#bd-group .btn-choice').forEach(function(btn) {
    btn.addEventListener('click', function() {
      document.querySelectorAll('#bd-group .btn-choice').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      selectedBitDepth = parseInt(btn.dataset.value);
    });
  });
}

// ── Boutons enregistrement ────────────────────────────────────────────
function initRecorderButtons() {
  var btnRecord = document.getElementById('btn-record');
  var btnStop   = document.getElementById('btn-stop');
  var btnSave   = document.getElementById('btn-save');

  if (btnRecord) btnRecord.addEventListener('click', startRecording);
  if (btnStop)   btnStop.addEventListener('click', stopRecording);
  if (btnSave)   btnSave.addEventListener('click', saveRecording);
}

// ── Démarrage enregistrement ──────────────────────────────────────────
function startRecording() {
  console.log('[P1] Demande accès microphone...');

  // Vérifier support MediaRecorder
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showSaveResult('error', '✗ Votre navigateur ne supporte pas l\'enregistrement. Utilisez Chrome ou Edge.');
    return;
  }

  navigator.mediaDevices.getUserMedia({ audio: true, video: false })
    .then(function(stream) {
      console.log('[P1] Micro OK, démarrage enregistrement');

      // Web Audio pour visualisation
      try {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioCtx.createAnalyser();
        analyser.fftSize = 512;
        var source = audioCtx.createMediaStreamSource(stream);
        source.connect(analyser);
        drawLiveWaveform();
      } catch(e) {
        console.warn('[P1] Visualisation non disponible:', e);
      }

      // Choisir le bon format MIME
      var mimeType = 'audio/webm';
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
        mimeType = 'audio/ogg;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
        mimeType = 'audio/mp4';
      }
      console.log('[P1] MIME type:', mimeType);

      mediaRecorder = new MediaRecorder(stream, { mimeType: mimeType });
      audioChunks = [];

      mediaRecorder.ondataavailable = function(e) {
        if (e.data && e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = function() {
        console.log('[P1] Enregistrement arrêté, chunks:', audioChunks.length);
        audioBlob = new Blob(audioChunks, { type: mimeType });
        console.log('[P1] Blob size:', audioBlob.size);

        var url = URL.createObjectURL(audioBlob);
        var preview = document.getElementById('audio-preview');
        if (preview) preview.src = url;

        document.getElementById('preview-wrap').classList.remove('hidden');
        document.getElementById('btn-save').disabled = false;
        drawIdleWaveform();
        showToast('Enregistrement terminé ! Cliquez sur Sauvegarder.', 'success');
      };

      mediaRecorder.onerror = function(e) {
        console.error('[P1] Erreur MediaRecorder:', e);
        showToast('Erreur enregistrement: ' + e.error, 'error');
      };

      mediaRecorder.start(250);
      console.log('[P1] MediaRecorder démarré');

      // Timer
      timerSeconds = 0;
      updateTimerDisplay();
      timerInterval = setInterval(function() {
        timerSeconds++;
        updateTimerDisplay();
        // Limite de securite absolue a 120s - l utilisateur arrete manuellement
        if (timerSeconds >= 120) {
          showToast('Limite de 120 secondes atteinte.', 'info');
          stopRecording();
        }
      }, 1000);

      setUiRecording(true);
      showToast('Enregistrement démarré…', 'info');
    })
    .catch(function(err) {
      console.error('[P1] Erreur getUserMedia:', err);
      var msg = 'Accès microphone refusé.';
      if (err.name === 'NotAllowedError') msg = '✗ Accès microphone refusé. Autorisez le micro dans le navigateur.';
      else if (err.name === 'NotFoundError') msg = '✗ Aucun microphone trouvé sur cet appareil.';
      else msg = '✗ Erreur micro : ' + err.message;
      showSaveResult('error', msg);
      showToast(msg, 'error');
    });
}

// ── Arrêt enregistrement ──────────────────────────────────────────────
function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(function(t) { t.stop(); });
  }
  clearInterval(timerInterval);
  if (animFrame) cancelAnimationFrame(animFrame);
  if (audioCtx) { try { audioCtx.close(); } catch(e) {} audioCtx = null; }
  setUiRecording(false);
}

// ── Sauvegarde ────────────────────────────────────────────────────────
function saveRecording() {
  if (!audioBlob || audioBlob.size === 0) {
    showSaveResult('error', '✗ Aucun enregistrement à sauvegarder.');
    return;
  }

  var locuteur = document.getElementById('locuteur').value.trim() || 'locuteur_01';
  var session  = document.getElementById('session').value.trim()  || 'session_01';

  var formData = new FormData();
  // Extension selon le type MIME
  var ext = audioBlob.type.includes('ogg') ? '.ogg' : audioBlob.type.includes('mp4') ? '.mp4' : '.webm';
  formData.append('audio', audioBlob, 'recording' + ext);
  formData.append('sample_rate', selectedSampleRate.toString());
  formData.append('bit_depth', selectedBitDepth.toString());
  formData.append('locuteur', locuteur);
  formData.append('session', session);

  showSaveResult('info', '⏳ Sauvegarde en cours…');
  document.getElementById('btn-save').disabled = true;

  console.log('[P1] Envoi au serveur, taille blob:', audioBlob.size, 'type:', audioBlob.type);

  fetch('/api/save_audio', {
    method: 'POST',
    body: formData
  })
  .then(function(res) {
    console.log('[P1] Réponse HTTP:', res.status);
    return res.json();
  })
  .then(function(data) {
    console.log('[P1] Réponse serveur:', data);
    document.getElementById('btn-save').disabled = false;
    if (data.success) {
      showSaveResult('success', '✓ Sauvegardé : ' + data.filename);
      showToast('Fichier sauvegardé !', 'success');
      loadRecordingsList();
    } else {
      showSaveResult('error', '✗ Erreur : ' + data.error);
      showToast(data.error, 'error');
    }
  })
  .catch(function(err) {
    console.error('[P1] Erreur fetch:', err);
    document.getElementById('btn-save').disabled = false;
    showSaveResult('error', '✗ Erreur réseau : ' + err.message);
  });
}

// ── Helpers UI ────────────────────────────────────────────────────────
function setUiRecording(active) {
  document.getElementById('btn-record').disabled = active;
  document.getElementById('btn-stop').disabled   = !active;
  var dot  = document.getElementById('rec-dot');
  var text = document.getElementById('rec-status-text');
  if (dot)  { dot.className  = active ? 'rec-dot active' : 'rec-dot'; }
  if (text) { text.textContent = active ? 'Enregistrement…' : 'Arrêté'; }
}

function updateTimerDisplay() {
  var el  = document.getElementById('timer-display');
  var bar = document.getElementById('timer-bar');
  // Afficher le temps ecoule - la barre progresse sur 120s max
  if (el)  el.textContent = formatTime(timerSeconds);
  if (bar) bar.style.width = Math.min(100, (timerSeconds / 120) * 100) + '%';
}

function showSaveResult(type, msg) {
  var el = document.getElementById('save-result');
  if (!el) return;
  el.className = 'save-result ' + (type === 'success' ? 'success' : type === 'error' ? 'error' : '');
  el.textContent = msg;
  el.classList.remove('hidden');
}

// ── Waveform canvas ───────────────────────────────────────────────────
function drawIdleWaveform() {
  var canvas = document.getElementById('waveform-canvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  canvas.width = canvas.offsetWidth || 400;
  var W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  ctx.strokeStyle = '#C4B9A8';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  for (var x = 0; x < W; x++) {
    var y = H / 2 + Math.sin((x / W) * Math.PI * 8) * 8;
    x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();
}

function drawLiveWaveform() {
  if (!analyser) return;
  var canvas = document.getElementById('waveform-canvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  canvas.width = canvas.offsetWidth || 400;
  var W = canvas.width, H = canvas.height;
  var bufLen  = analyser.frequencyBinCount;
  var dataArr = new Uint8Array(bufLen);

  function draw() {
    if (!analyser) return;
    animFrame = requestAnimationFrame(draw);
    analyser.getByteTimeDomainData(dataArr);
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#F5F0E8';
    ctx.fillRect(0, 0, W, H);
    ctx.lineWidth = 2;
    ctx.strokeStyle = '#6D28D9';
    ctx.beginPath();
    var sliceW = W / bufLen;
    var x = 0;
    for (var i = 0; i < bufLen; i++) {
      var v = dataArr[i] / 128.0;
      var y = (v * H) / 2;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      x += sliceW;
    }
    ctx.stroke();
  }
  draw();
}

// ── Segmentation ──────────────────────────────────────────────────────
function initSegmentationUI() {
  var slider = document.getElementById('threshold');
  if (slider) {
    slider.addEventListener('input', function() {
      var val = document.getElementById('threshold-val');
      if (val) val.textContent = parseFloat(slider.value).toFixed(3);
    });
  }

  var btnRefresh = document.getElementById('btn-refresh-list');
  if (btnRefresh) btnRefresh.addEventListener('click', loadRecordingsList);

  var btnSeg = document.getElementById('btn-segment');
  if (btnSeg) btnSeg.addEventListener('click', runSegmentation);
}

function loadRecordingsList() {
  console.log('[P1] Chargement liste enregistrements...');
  fetch('/api/list_recordings')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      console.log('[P1] Enregistrements:', data);
      if (!data.success) return;

      var sel = document.getElementById('seg-file-select');
      if (!sel) return;
      var prev = sel.value;
      sel.innerHTML = '<option value="">— Sélectionner un enregistrement —</option>';
      data.recordings.forEach(function(r) {
        var opt = document.createElement('option');
        opt.value = r.path;
        opt.textContent = r.locuteur + ' / ' + r.session + ' / ' + r.filename;
        sel.appendChild(opt);
      });
      if (prev) sel.value = prev;
      buildDbTree(data.recordings);
    })
    .catch(function(e) { console.error('[P1] Erreur liste:', e); });
}

function buildDbTree(recordings) {
  var tree = document.getElementById('db-tree');
  if (!tree) return;
  if (!recordings.length) {
    tree.innerHTML = '<span class="empty-state">Aucun enregistrement. Commencez par enregistrer.</span>';
    return;
  }
  var grouped = {};
  recordings.forEach(function(r) {
    if (!grouped[r.locuteur]) grouped[r.locuteur] = {};
    if (!grouped[r.locuteur][r.session]) grouped[r.locuteur][r.session] = [];
    grouped[r.locuteur][r.session].push(r.filename);
  });
  var html = '';
  Object.keys(grouped).forEach(function(loc) {
    html += '<div class="db-locuteur">📁 ' + loc + '/</div>';
    Object.keys(grouped[loc]).forEach(function(ses) {
      html += '<div class="db-session">📂 ' + ses + '/</div>';
      grouped[loc][ses].forEach(function(f) {
        html += '<div class="db-file">' + f + '</div>';
      });
    });
  });
  tree.innerHTML = html;
}

function runSegmentation() {
  var filepath = document.getElementById('seg-file-select').value;
  if (!filepath) { showToast('Sélectionnez un fichier à segmenter.', 'error'); return; }

  var threshold    = parseFloat(document.getElementById('threshold').value);
  var minSilenceMs = parseInt(document.getElementById('min-silence').value);

  document.getElementById('seg-spinner').classList.remove('hidden');
  document.getElementById('segments-wrap').classList.add('hidden');

  console.log('[P1] Segmentation:', filepath, threshold, minSilenceMs);

  fetch('/api/segment', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filepath: filepath, threshold: threshold, min_silence_ms: minSilenceMs })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    document.getElementById('seg-spinner').classList.add('hidden');
    console.log('[P1] Résultat segmentation:', data);
    if (!data.success) { showToast(data.error, 'error'); return; }
    renderSegmentsTable(data.segments);
    showToast(data.segments.length + ' segment(s) détecté(s) !', 'success');
  })
  .catch(function(err) {
    document.getElementById('seg-spinner').classList.add('hidden');
    showToast('Erreur : ' + err.message, 'error');
  });
}

function renderSegmentsTable(segments) {
  document.getElementById('seg-count').textContent = segments.length + ' segment(s)';
  var tbody = document.getElementById('seg-tbody');
  tbody.innerHTML = '';
  segments.forEach(function(seg, i) {
    var tr = document.createElement('tr');
    tr.innerHTML =
      '<td>' + (i+1) + '</td>' +
      '<td>' + seg.filename + '</td>' +
      '<td>' + seg.start_s + 's</td>' +
      '<td>' + seg.end_s + 's</td>' +
      '<td>' + seg.duration + 's</td>' +
      '<td><a class="seg-link" href="' + seg.url + '" target="_blank">▶ Écouter</a></td>' +
      '<td><a class="dl-link" href="/api/download_segment/' + seg.filename + '" download>↓</a></td>';
    tbody.appendChild(tr);
  });
  document.getElementById('segments-wrap').classList.remove('hidden');
}