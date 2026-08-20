const box = document.querySelector('.lightbox');
const big = box.querySelector('img');
const close = box.querySelector('button');
let lastFocused = null;

const openBox = (element) => {
  lastFocused = document.activeElement;
  big.src = element.dataset.full;
  box.classList.add('open');
  box.setAttribute('aria-hidden', 'false');
  document.body.classList.add('lightbox-open');
  close.focus();
};

document.querySelectorAll('.shot').forEach((element) => {
  element.addEventListener('click', () => openBox(element));
  element.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openBox(element);
    }
  });
});

const closeBox = () => {
  box.classList.remove('open');
  box.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('lightbox-open');
  big.removeAttribute('src');
  if (lastFocused && typeof lastFocused.focus === 'function') {
    lastFocused.focus();
  }
  lastFocused = null;
};

close.addEventListener('click', closeBox);
box.addEventListener('click', (event) => {
  if (event.target === box) closeBox();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && box.classList.contains('open')) closeBox();
});
