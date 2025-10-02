// static/js/pwa.js
window.addEventListener('load', async () => {
  if ('serviceWorker' in navigator) {
    try {
      const reg = await navigator.serviceWorker.register('/sw.js');
      console.log('Service worker registered', reg);
      const statusEl = document.getElementById('status');
      if (statusEl) statusEl.textContent = 'Service worker ready.';
    } catch (err) {
      console.error('Service worker registration failed', err);
    }
  }
});


// Optional: custom install prompt
let deferredPrompt;
const installBtn = document.getElementById('install-btn');

window.addEventListener('beforeinstallprompt', (e) => {
  // Prevent the mini-infobar from appearing on mobile
  e.preventDefault();
  deferredPrompt = e;
  installBtn.hidden = false;
});

installBtn?.addEventListener('click', async () => {
  installBtn.hidden = true;
  if (!deferredPrompt) return;
  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  console.log(`User response to the install prompt: ${outcome}`);
  deferredPrompt = null;
});
