/* ── State ────────────────────────────────────────────────── */
let currentMode = 'random';
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
    currentMode = mode;
    currentGenreId = null;
    loadMovie();
  });
});

/* ── Genre tags ──────────────────────────────────────────── */
genreTags.forEach(tag => {
  tag.addEventListener('click', () => {
    currentMode = 'genre';
    currentGenreId = parseInt(tag.dataset.id, 10);
    genresPanel.classList.add('hidden');
    tabs.forEach(t => t.classList.remove('active'));
    loadMovie();
  });
});

/* ── Description toggle ──────────────────────────────────── */
descToggle.addEventListener('click', () => {
  const isCollapsed = descSection.classList.toggle('collapsed');
  descToggle.textContent = isCollapsed ? 'Читать далее' : 'Свернуть';
});

/* ── Retry ───────────────────────────────────────────────── */
retryBtn.addEventListener('click', loadMovie);

/* ── Load movie ──────────────────────────────────────────── */
async function loadMovie() {
  // Show loader, hide card & error
  loader.classList.remove('hidden');
  movieCard.classList.add('hidden');
  errorEl.classList.add('hidden');

  // Build URL
  let url = '/api/movies/random';
  if (currentMode === 'genre' && currentGenreId) {
    url += `?genre=${currentGenreId}`;
  } else if (currentMode !== 'random') {
    url += `?type=${currentMode}`;
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
  movieCard.classList.remove('hidden');

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
    // If short enough, hide toggle
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

  // Scroll to top smoothly
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/* ── Initial load ────────────────────────────────────────── */
loadMovie();