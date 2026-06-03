/* ── State ────────────────────────────────────────────────── */
let currentCategory = 'TOP_250_MOVIES';
let currentGenreId = null;

const GENRES = {
  2: '🎭 Драма',
  6: '👽 Фантастика',
  1: '🔪 Триллер',
  13: '😂 Комедия',
  11: '💥 Боевик',
};

/* ── DOM refs ────────────────────────────────────────────── */
const tabs = document.querySelectorAll('.tab');
const genresPanel = document.getElementById('genres-panel');
const genreTags = document.querySelectorAll('.genre-tag');
const loader = document.getElementById('loader');
const movieCard = document.getElementById('movie-card');
const errorEl = document.getElementById('error');
const retryBtn = document.getElementById('retry-btn');
const nextBtn = document.getElementById('next-btn');

const poster = document.getElementById('poster');
const ratingBadge = document.getElementById('rating-badge');
const titleEl = document.getElementById('title');
const yearEl = document.getElementById('year');
const genresEl = document.getElementById('genres');
const descText = document.getElementById('desc-text');
const descToggle = document.getElementById('desc-toggle');
const descSection = document.getElementById('description');

/* ── Telegram WebApp ─────────────────────────────────────── */
if (window.Telegram?.WebApp) {
  Telegram.WebApp.ready();
  Telegram.WebApp.expand();
}

/* ── Tab switching ───────────────────────────────────────── */
tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    tabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');

    const mode = tab.dataset.mode;

    if (mode === 'genres') {
      genresPanel.classList.toggle('hidden');
      return;
    }

    genresPanel.classList.add('hidden');
    currentCategory = mode;
    currentGenreId = null;
    fetchMovie(currentCategory);
  });
});

/* ── Genre tags ──────────────────────────────────────────── */
genreTags.forEach(tag => {
  tag.addEventListener('click', () => {
    currentCategory = 'genre';
    currentGenreId = parseInt(tag.dataset.id, 10);
    genresPanel.classList.add('hidden');
    tabs.forEach(t => t.classList.remove('active'));
    fetchMovie(currentCategory);
  });
});

/* ── Description toggle ──────────────────────────────────── */
descToggle.addEventListener('click', () => {
  const isCollapsed = descSection.classList.toggle('collapsed');
  descToggle.textContent = isCollapsed ? 'Читать далее' : 'Свернуть';
});

/* ── Retry ───────────────────────────────────────────────── */
retryBtn.addEventListener('click', () => fetchMovie(currentCategory));

/* ── Next button ─────────────────────────────────────────── */
nextBtn.addEventListener('click', () => fetchMovie(currentCategory));

/* ── Fetch movie ─────────────────────────────────────────── */
async function fetchMovie(category) {
  // Fade-out the card if visible
  if (!movieCard.classList.contains('hidden')) {
    movieCard.classList.add('fade-out');
    await sleep(250);
    movieCard.classList.add('hidden');
    movieCard.classList.remove('fade-out');
  }

  // Show loader, hide error
  loader.classList.remove('hidden');
  errorEl.classList.add('hidden');

  // Build URL
  let url;
  if (category === 'recent') {
    url = '/api/movies/recent';
  } else if (category === 'genre' && currentGenreId) {
    url = `/api/movies/random?genre=${currentGenreId}`;
  } else if (category === 'TOP_250_MOVIES') {
    url = '/api/movies/random?type=TOP_250_MOVIES';
  } else {
    url = `/api/movies/random?type=${category}`;
  }

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data || data.error) throw new Error(data?.error || 'Empty response');

    renderMovie(data);
  } catch (err) {
    console.error('Fetch error:', err);
    loader.classList.add('hidden');
    errorEl.classList.remove('hidden');
  }
}

/* ── Render movie ────────────────────────────────────────── */
function renderMovie(movie) {
  loader.classList.add('hidden');
  errorEl.classList.add('hidden');

  // Poster
  poster.src = movie.posterUrl || movie.posterUrlPreview || '';
  poster.alt = movie.nameRu || 'Poster';

  // Rating badge
  const rating = parseFloat(movie.ratingKinopoisk) || 0;
  if (rating) {
    ratingBadge.textContent = `⭐ ${rating.toFixed(1)}`;
    ratingBadge.className = 'rating-badge';
    if (rating >= 8) ratingBadge.classList.add('high');
    else if (rating >= 6) ratingBadge.classList.add('mid');
    else ratingBadge.classList.add('low');
    ratingBadge.style.display = '';
  } else {
    ratingBadge.style.display = 'none';
  }

  // Title
  titleEl.textContent = movie.nameRu || movie.nameOriginal || 'Без названия';

  // Year
  yearEl.textContent = movie.year ? `📅 ${movie.year}` : '';

  // Genres
  const genreNames = (movie.genres || [])
    .map(g => g.genre)
    .filter(Boolean)
    .join(', ');
  genresEl.textContent = genreNames ? `🎭 ${genreNames}` : '';

  // Description
  const desc = movie.description || movie.shortDescription || '';
  if (desc) {
    descText.textContent = desc;
    descSection.classList.remove('collapsed');
    descToggle.textContent = 'Свернуть';
    descSection.style.display = '';
    if (desc.length <= 200) {
      descToggle.style.display = 'none';
    } else {
      descToggle.style.display = '';
      descSection.classList.add('collapsed');
      descToggle.textContent = 'Читать далее';
    }
  } else {
    descSection.style.display = 'none';
  }

  // Fade-in the card
  movieCard.classList.remove('hidden');
  movieCard.classList.add('fade-in');
  setTimeout(() => movieCard.classList.remove('fade-in'), 400);

  // Scroll to top smoothly
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ── Utility ─────────────────────────────────────────────── */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/* ── Initial load ────────────────────────────────────────── */
fetchMovie(currentCategory);