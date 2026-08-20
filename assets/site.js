const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const setupEditorialMotion = () => {
  if (reducedMotion) return;

  const style = document.createElement('style');
  style.dataset.editorialMotion = 'true';
  style.textContent = `
    .motion-ready .hero-copy > .eyebrow,
    .motion-ready .hero-copy > h1,
    .motion-ready .hero-copy > .lead,
    .motion-ready .hero-copy > .hero-meta {
      opacity: 0;
      transform: translateY(14px);
      animation: hero-intro .9s cubic-bezier(.2,.7,.2,1) forwards;
    }
    .motion-ready .hero-copy > .eyebrow { animation-delay: .08s; }
    .motion-ready .hero-copy > h1 { animation-delay: .16s; }
    .motion-ready .hero-copy > .lead { animation-delay: .28s; }
    .motion-ready .hero-copy > .hero-meta { animation-delay: .4s; }
    .motion-ready .reveal {
      opacity: 0;
      transform: translateY(20px);
      transition: opacity .78s cubic-bezier(.2,.7,.2,1), transform .78s cubic-bezier(.2,.7,.2,1);
    }
    .motion-ready .reveal.is-visible { opacity: 1; transform: none; }
    .motion-ready .gallery .shot.reveal:nth-child(1) { transition-delay: .02s; }
    .motion-ready .gallery .shot.reveal:nth-child(2) { transition-delay: .08s; }
    .motion-ready .gallery .shot.reveal:nth-child(3) { transition-delay: .14s; }
    .motion-ready .gallery .shot.reveal:nth-child(4) { transition-delay: .2s; }
    @keyframes hero-intro { to { opacity: 1; transform: none; } }
    @media (max-width: 760px) {
      .motion-ready .reveal { transform: translateY(14px); }
    }
    @media (prefers-reduced-motion: reduce) {
      .motion-ready .hero-copy > .eyebrow,
      .motion-ready .hero-copy > h1,
      .motion-ready .hero-copy > .lead,
      .motion-ready .hero-copy > .hero-meta,
      .motion-ready .reveal {
        opacity: 1;
        transform: none;
        animation: none;
        transition: none;
      }
    }
  `;
  document.head.append(style);

  const revealTargets = [
    document.querySelector('.profile'),
    document.querySelector('.section-head'),
    ...document.querySelectorAll('.gallery .shot'),
    document.querySelector('.concept'),
  ].filter(Boolean);

  revealTargets.forEach((element) => element.classList.add('reveal'));

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });

    revealTargets.forEach((element) => observer.observe(element));
  } else {
    revealTargets.forEach((element) => element.classList.add('is-visible'));
  }

  document.documentElement.classList.add('motion-ready');
};

try {
  setupEditorialMotion();
} catch (error) {
  document.documentElement.classList.remove('motion-ready');
  document.querySelectorAll('.reveal').forEach((element) => {
    element.classList.add('is-visible');
  });
}

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
