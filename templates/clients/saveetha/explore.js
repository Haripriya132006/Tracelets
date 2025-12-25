/* ======================= Fullscreen image viewer ======================= */
const images   = document.querySelectorAll('.floor-card img');
const modal    = document.getElementById('imageModal');
const modalImg = document.getElementById('modalImg');
const closeBtn = document.getElementById('closeModal');
const zoomInBtn  = document.getElementById('zoomIn');
const zoomOutBtn = document.getElementById('zoomOut');

let scale = 1, minScale = 0.5, maxScale = 5;
let x = 0, y = 0;
let startX = 0, startY = 0;
let isDragging = false;

images.forEach(img => {
  img.addEventListener('click', () => {
    modal.style.display = 'flex';
    modalImg.src = img.src;
    resetView();
  });
});

function resetView() {
  scale = 1; x = 0; y = 0;
  updateTransform();
}

function updateTransform() {
  modalImg.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
}

function clampPosition() {
  const containerW = modal.clientWidth;
  const containerH = modal.clientHeight;
  const baseW = modalImg.clientWidth;
  const baseH = modalImg.clientHeight;

  const scaledW = baseW * scale;
  const scaledH = baseH * scale;

  const maxX = Math.max(0, (scaledW - containerW) / 2);
  const maxY = Math.max(0, (scaledH - containerH) / 2);

  x = Math.min(maxX, Math.max(-maxX, x));
  y = Math.min(maxY, Math.max(-maxY, y));
}

function zoomAt(factor, clientX, clientY) {
  const prev = scale;
  scale = Math.min(maxScale, Math.max(minScale, scale * factor));

  const rect = modalImg.getBoundingClientRect();
  const imgCenterX = rect.left + rect.width / 2;
  const imgCenterY = rect.top  + rect.height / 2;

  const dx = clientX - imgCenterX;
  const dy = clientY - imgCenterY;

  x -= dx * (scale / prev - 1);
  y -= dy * (scale / prev - 1);

  clampPosition();
  updateTransform();
}

modalImg.addEventListener('wheel', (e) => {
  e.preventDefault();
  const factor = e.deltaY > 0 ? 0.9 : 1.1;
  zoomAt(factor, e.clientX, e.clientY);
}, { passive: false });

zoomInBtn.addEventListener('click', () => zoomAt(1.15, window.innerWidth/2, window.innerHeight/2));
zoomOutBtn.addEventListener('click', () => zoomAt(1/1.15, window.innerWidth/2, window.innerHeight/2));

modalImg.addEventListener('mousedown', (e) => {
  isDragging = true;
  startX = e.clientX - x;
  startY = e.clientY - y;
  modalImg.style.cursor = 'grabbing';
});
document.addEventListener('mousemove', (e) => {
  if (!isDragging) return;
  x = e.clientX - startX;
  y = e.clientY - startY;
  clampPosition();
  updateTransform();
});
document.addEventListener('mouseup', () => {
  isDragging = false;
  modalImg.style.cursor = 'grab';
});

closeBtn.addEventListener('click', () => { modal.style.display = 'none'; });
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') modal.style.display = 'none';
  if (e.key === '+') zoomAt(1.15, window.innerWidth/2, window.innerHeight/2);
  if (e.key === '-') zoomAt(1/1.15, window.innerWidth/2, window.innerHeight/2);
});

modalImg.addEventListener('dragstart', (e) => e.preventDefault());
