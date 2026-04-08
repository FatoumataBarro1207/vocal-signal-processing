/**
 * utils.js – Fonctions utilitaires partagées
 */

/**
 * Formate un nombre de secondes en MM:SS
 * @param {number} seconds
 * @returns {string}
 */
function formatTime(seconds) {
  var m = Math.floor(seconds / 60);
  var s = Math.floor(seconds % 60);
  return m + ':' + (s < 10 ? '0' : '') + s;
}

/**
 * Affiche une notification toast temporaire.
 * @param {string} message
 * @param {string} type - 'success', 'error', ou 'info'
 * @param {number} duration - ms
 */
function showToast(message, type, duration) {
  type     = type     || 'info';
  duration = duration || 3500;

  var container = document.getElementById('toast-container');
  if (!container) return;

  var toast = document.createElement('div');
  toast.className = 'toast ' + type;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(function() {
    toast.style.opacity   = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all .3s';
    setTimeout(function() {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, duration);
}

/**
 * Active ou desactive un bouton HTML
 * @param {string} id
 * @param {boolean} enabled
 */
function setButtonEnabled(id, enabled) {
  var btn = document.getElementById(id);
  if (btn) btn.disabled = !enabled;
}

/**
 * Affiche ou masque un element HTML
 * @param {string} id
 * @param {boolean} visible
 */
function setVisible(id, visible) {
  var el = document.getElementById(id);
  if (!el) return;
  if (visible) el.classList.remove('hidden');
  else         el.classList.add('hidden');
}

console.log('[Utils] Charge OK – formatTime, showToast disponibles');