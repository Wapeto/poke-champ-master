"use strict";

// ── State ─────────────────────────────────────────────────────────────────────
let ALL_POKEMON = [];   // [{name, tier, types, image_url}] — names are canonical English
let TIER_DATA   = {};   // grouped tier list, cached for filtering
let META_TEAMS  = [];   // cached meta teams for re-render on language switch
const tbPool   = [];    // team-builder pool
const myPool   = [];    // matchup my team
const oppPool  = [];    // matchup opponent team

// Last computed responses, kept so a language switch can re-render in place.
let lastSuggest = null;
let lastBuild   = null;
let lastMatchup = null;

// Team-builder editable state (one entry per built team slot).
let tbTeam     = [];   // [{name,tier,types,image_url,role,build,movePool,bestNames(Set),selected[]}]
let tbCoverage = { covered_types: [], uncovered_types: [] };
let tbShared   = {};   // shared weaknesses (type-based, unaffected by move edits)
let tbScore    = 0;
let tbEditing  = -1;   // index of the slot whose move editor is open (-1 = none)
let tierQuery   = "";
let currentModalName = null;

const CHIP_RENDERERS = [];  // renderChips for each search pool

// ── Helpers ───────────────────────────────────────────────────────────────────
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

function typeBadge(type) {
  return `<span class="type-badge type-${type}">${tType(type)}</span>`;
}

function tierBadge(tier) {
  const cls = tier === 'A+' ? 'Ap' : tier;
  return `<span class="tier-label tier-${cls}">${tier}</span>`;
}

function sprite(p, cls = 'sprite') {
  if (!p || !p.image_url) return '';
  return `<img class="${cls}" src="${p.image_url}" alt="${tName(p.name)}" loading="lazy">`;
}

function movePill(m) {
  const ty = m.type || '';
  const bg = ty ? `style="background:var(--${ty})"` : '';
  const cat = m.category
    ? `<span class="move-cat cat-${m.category}">${catAbbr(m.category)}</span>` : '';
  return `<span class="move-pill type-text-${ty}" ${bg} data-type="${ty}">${tMove(m.name)}${cat}</span>`;
}

function moveList(build) {
  if (!build || !build.moves) return '';
  return `<div class="move-pills">${build.moves.map(movePill).join('')}</div>`;
}

function itemTag(build) {
  if (!build || !build.held_item) return '';
  const icon = build.held_item_image
    ? `<img class="item-img" src="${build.held_item_image}" alt="" loading="lazy">` : '🎒';
  return `<div class="card-item">${icon}<span>${tItem(build.held_item)}</span></div>`;
}

// Any element with data-poke opens the detail modal (event delegation).
// The canonical English name is always carried here, never the translation.
function pokeRef(name) {
  return `data-poke="${encodeURIComponent(name)}"`;
}

function pokeCard(p, build = null, role = null) {
  const types = (p.types || []).map(typeBadge).join('');
  const nat   = build
    ? `<div class="card-nature">${tNature(build.nature)} | ${tAbility(build.ability)}</div>` : '';
  const roleHtml = role ? `<div class="card-role">${roleLabel(role)}</div>` : '';
  return `
    <div class="poke-card clickable" ${pokeRef(p.name)}>
      <div class="card-head">
        ${sprite(p, 'sprite sm')}
        <div class="card-name">${tName(p.name)} ${tierBadge(p.tier || '')}</div>
      </div>
      ${roleHtml}
      <div style="margin-bottom:8px">${types}</div>
      ${nat}
      ${itemTag(build)}
      ${moveList(build)}
    </div>`;
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
$$('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    $$('.tab-btn').forEach(b => b.classList.remove('active'));
    $$('.tab-content').forEach(s => s.classList.remove('active'));
    btn.classList.add('active');
    $('#' + btn.dataset.tab).classList.add('active');
  });
});

// ── Load data ─────────────────────────────────────────────────────────────────
async function init() {
  await initLang();
  ALL_POKEMON = await fetch('/api/pokemon').then(r => r.json());
  loadTierList();
  loadMetaTeams();
}

// Re-render every dynamic view in the active language (called by i18n.setLang).
function rerenderAll() {
  renderTierList(tierQuery);
  renderMetaTeams();
  CHIP_RENDERERS.forEach(fn => fn());
  renderBox();
  if (lastSuggest) renderSuggest(lastSuggest);
  if (lastBuild) renderBuild(lastBuild);
  if (lastMatchup) renderMatchup(lastMatchup);
  if (currentModalName && !modal.classList.contains('hidden')) {
    openPokemonModal(currentModalName);
  }
}

// ── TIER LIST ─────────────────────────────────────────────────────────────────
const TIER_ORDER = ['S', 'A+', 'A', 'B', 'C', 'D'];
const BADGE_CLS  = { 'S':'S', 'A+':'Ap', 'A':'A', 'B':'B', 'C':'C', 'D':'D' };

async function loadTierList() {
  TIER_DATA = await fetch('/api/tier-list').then(r => r.json());
  renderTierList('');
}

function renderTierList(query) {
  tierQuery = query;
  const q = query.trim().toLowerCase();
  const container = $('#tier-list-container');

  const html = TIER_ORDER.map(tier => {
    const list = (TIER_DATA[tier] || []).filter(p => searchMatch(p, q));
    if (!list.length) return '';
    const chips = list.map(p => {
      const types = (p.types || []).map(typeBadge).join('');
      const title = (p.types || []).map(tType).join('/');
      return `<div class="poke-chip clickable" ${pokeRef(p.name)} title="${title}">
        ${sprite(p, 'sprite tl')}<strong>${tName(p.name)}</strong> ${types}
      </div>`;
    }).join('');
    return `
      <div class="tier-section">
        <div class="tier-header">
          <div class="tier-badge ${BADGE_CLS[tier]}">${tier}</div>
          <span class="muted">${t('tier.count', { n: list.length })}</span>
        </div>
        <div class="tier-pokemon-row">${chips}</div>
      </div>`;
  }).join('');

  container.innerHTML = html || `<p class="muted">${t('tier.nomatch')}</p>`;
}

const tierSearch = $('#tier-search');
const tierClear = $('#tier-search-clear');
tierSearch.addEventListener('input', e => {
  renderTierList(e.target.value);
  tierClear.classList.toggle('hidden', !e.target.value);
});
tierClear.addEventListener('click', () => {
  tierSearch.value = '';
  renderTierList('');
  tierClear.classList.add('hidden');
  tierSearch.focus();
});

// ── POKÉMON DETAIL MODAL ──────────────────────────────────────────────────────
const modal     = $('#poke-modal');
const modalBody = $('#modal-body');

function closeModal() { modal.classList.add('hidden'); currentModalName = null; }
function openModal()  { modal.classList.remove('hidden'); }

$('#modal-close').addEventListener('click', closeModal);
modal.addEventListener('click', e => { if (e.target === modal) closeModal(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// Delegate clicks on anything carrying data-poke.
document.addEventListener('click', e => {
  const el = e.target.closest('[data-poke]');
  if (el) openPokemonModal(decodeURIComponent(el.dataset.poke));
});

function matchupRow(label, entries, cls) {
  if (!entries.length) return '';
  const badges = entries.map(en =>
    `<span class="type-badge type-${en.type}">${tType(en.type)}${en.mult && en.mult !== 0 ? ` ${en.mult}×` : ''}</span>`
  ).join('');
  return `<div class="matchup-line"><span class="matchup-label ${cls}">${label}</span>${badges}</div>`;
}

async function openPokemonModal(name) {
  currentModalName = name;
  openModal();
  modalBody.innerHTML = `<p class="muted">${t('common.loading')}</p>`;
  let d;
  try {
    const res = await fetch('/api/pokemon/' + encodeURIComponent(name));
    if (!res.ok) throw new Error('not found');
    d = await res.json();
  } catch {
    modalBody.innerHTML = `<p class="warn">${t('modal.notfound', { name: tName(name) })}</p>`;
    return;
  }

  const types = (d.types || []).map(typeBadge).join(' ');
  const stats = d.base_stats || {};
  const statRows = ['hp','atk','def','spa','spd','spe']
    .filter(k => stats[k] != null)
    .map(k => {
      const v = stats[k];
      const pct = Math.min(100, Math.round((v / 200) * 100));
      return `<div class="stat-row">
        <span class="stat-key">${statLabel(k)}</span>
        <span class="stat-bar"><span class="stat-fill" style="width:${pct}%"></span></span>
        <span class="stat-val">${v}</span>
      </div>`;
    }).join('');

  const moves = (d.best_moves || []).map(movePill).join('');

  const builds = (d.builds || []).map((b, i) => `
    <div class="build-block">
      <div class="build-title">${t('modal.build', { n: i + 1 })} — ${tNature(b.nature) || ''} ${b.ability ? '| ' + tAbility(b.ability) : ''}</div>
      ${itemTag(b)}
      ${moveList(b)}
    </div>`).join('');

  const sources = (d.sources || []).length
    ? `<div class="sources">${t('modal.data', { sources: d.sources.join(' · ') })}</div>` : '';

  const teammates = (d.best_teammates || []).map(n =>
    `<span class="poke-chip clickable inline" ${pokeRef(n)}>${tName(n)}</span>`).join('');
  const counters = (d.counters || []).map(n =>
    `<span class="poke-chip clickable inline" ${pokeRef(n)}>${tName(n)}</span>`).join('');

  modalBody.innerHTML = `
    <div class="modal-header">
      ${d.image_url ? `<img class="sprite lg" src="${d.image_url}" alt="${tName(d.name)}">` : ''}
      <div>
        <h2 class="modal-name">${tName(d.name)} ${d.tier ? tierBadge(d.tier) : ''}</h2>
        <div class="modal-types">${types}</div>
        ${d.build_url ? `<a class="muted source-link" href="${d.build_url}" target="_blank" rel="noopener">${t('modal.game8')}</a>` : ''}
        ${sources}
      </div>
    </div>

    ${d.description ? `<p class="modal-desc">${d.description}</p>` : ''}

    <div class="modal-grid">
      <div class="modal-col">
        ${statRows ? `<h4 class="modal-sub">${t('modal.stats')}</h4><div class="stats">${statRows}</div>` : ''}
        <h4 class="modal-sub">${t('modal.matchups')}</h4>
        ${matchupRow(t('modal.weak'), d.weak_to || [], 'bad')}
        ${matchupRow(t('modal.resists'), d.resists || [], 'good')}
        ${matchupRow(t('modal.immune'), d.immune_to || [], 'good')}
      </div>
      <div class="modal-col">
        ${moves ? `<h4 class="modal-sub">${t('modal.moves')}</h4><div class="move-list">${moves}</div>` : ''}
        ${teammates ? `<h4 class="modal-sub">${t('modal.teammates')}</h4><div class="chip-wrap">${teammates}</div>` : ''}
        ${counters ? `<h4 class="modal-sub">${t('modal.counters')}</h4><div class="chip-wrap">${counters}</div>` : ''}
      </div>
    </div>

    ${builds ? `<h4 class="modal-sub">${t('modal.builds')}</h4><div class="build-grid">${builds}</div>` : ''}
  `;
}

// ── SEARCH AUTOCOMPLETE ───────────────────────────────────────────────────────
function makeSearch(inputId, sugId, pool, chipListId, btnToEnable, onChange = null) {
  const input = $('#' + inputId);
  const sug   = $('#' + sugId);
  const chips = $('#' + chipListId);

  function addPoke(poke) {
    if (pool.find(p => p.name.toLowerCase() === poke.name.toLowerCase())) return;
    pool.push(poke);
    renderChips();
    input.value = '';
    sug.classList.remove('open');
    sug.innerHTML = '';
    if (btnToEnable) $('#' + btnToEnable).disabled = pool.length === 0;
    if (onChange) onChange();
  }

  function renderChips() {
    chips.innerHTML = pool.map((p, i) => {
      const types = (p.types || []).map(typeBadge).join('');
      return `<div class="chip">
        ${sprite(p, 'sprite xs')}${types} <span class="clickable" ${pokeRef(p.name)}>${tName(p.name)}</span>
        <span class="remove" data-i="${i}">✕</span>
      </div>`;
    }).join('');
    chips.querySelectorAll('.remove').forEach(el => {
      el.addEventListener('click', () => {
        pool.splice(+el.dataset.i, 1);
        renderChips();
        if (btnToEnable) $('#' + btnToEnable).disabled = pool.length === 0;
        if (onChange) onChange();
      });
    });
  }
  CHIP_RENDERERS.push(renderChips);

  // Expose addPoke so suggestion clicks can push into the pool.
  makeSearch._pools = makeSearch._pools || {};
  makeSearch._pools[inputId] = addPoke;

  // Expose a clear so toolbar buttons can empty the pool with full side effects.
  makeSearch._clear = makeSearch._clear || {};
  makeSearch._clear[inputId] = () => {
    pool.length = 0;
    renderChips();
    if (btnToEnable) $('#' + btnToEnable).disabled = true;
    if (onChange) onChange();
  };

  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    if (!q) { sug.classList.remove('open'); return; }
    const matches = ALL_POKEMON.filter(p => searchMatch(p, q)).slice(0, 12);
    if (!matches.length) { sug.classList.remove('open'); return; }
    sug.innerHTML = matches.map(p => {
      const types = (p.types || []).map(typeBadge).join('');
      return `<div class="suggestion-item" data-name="${encodeURIComponent(p.name)}">
        ${sprite(p, 'sprite xs')}${tierBadge(p.tier)} <strong>${tName(p.name)}</strong> ${types}
      </div>`;
    }).join('');
    sug.classList.add('open');
    sug.querySelectorAll('.suggestion-item').forEach(el => {
      el.addEventListener('click', () => {
        const name = decodeURIComponent(el.dataset.name);
        const poke = ALL_POKEMON.find(p => p.name === name);
        if (poke) addPoke(poke);
      });
    });
  });

  document.addEventListener('click', e => {
    if (!input.contains(e.target) && !sug.contains(e.target)) sug.classList.remove('open');
  });
}

// ── TEAM BUILDER ──────────────────────────────────────────────────────────────
makeSearch('tb-search', 'tb-suggestions', tbPool, 'tb-pool', 'tb-build-btn', refreshTbSuggest);

function typeBadgeList(types) { return (types || []).map(typeBadge).join(' '); }

async function refreshTbSuggest() {
  const panel = $('#tb-suggest');
  if (!tbPool.length) { panel.classList.add('hidden'); panel.innerHTML = ''; lastSuggest = null; return; }

  const res = await fetch('/api/team/suggest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pokemon: tbPool.map(p => p.name) }),
  }).then(r => r.json()).catch(() => null);
  if (!res) return;
  renderSuggest(res);
}

function renderSuggest(res) {
  lastSuggest = res;
  const panel = $('#tb-suggest');
  const attack = res.attack_types_needed || [];
  const weak   = res.weak_spots || [];
  const def    = res.defensive_types_needed || [];

  const cards = (res.suggestions || []).map(s => `
    <div class="suggest-card" data-add="${encodeURIComponent(s.name)}">
      ${sprite(s, 'sprite sm')}
      <div class="suggest-card-body">
        <div class="suggest-name">${tName(s.name)} ${tierBadge(s.tier)}</div>
        <div>${typeBadgeList(s.types)}</div>
        <div class="suggest-role">${roleLabel(s.role)} · +${s.gain}</div>
      </div>
      <span class="suggest-add">+</span>
    </div>`).join('');

  panel.innerHTML = `
    <h3>${t('tb.suggest.title')}</h3>
    <div class="suggest-types">
      ${attack.length ? `<div class="suggest-line"><span class="suggest-label good">${t('tb.suggest.attack')}</span>${typeBadgeList(attack)}</div>` : `<div class="suggest-line good">${t('tb.suggest.fullcover')}</div>`}
      ${weak.length ? `<div class="suggest-line"><span class="suggest-label bad">${t('tb.suggest.stacked')}</span>${typeBadgeList(weak)}</div>` : ''}
      ${def.length ? `<div class="suggest-line"><span class="suggest-label">${t('tb.suggest.addtype')}</span>${typeBadgeList(def)}</div>` : ''}
    </div>
    <div class="suggest-grid">${cards}</div>
    <p class="muted suggest-hint">${t('tb.suggest.hint')}</p>`;
  panel.classList.remove('hidden');
}

// Add suggested Pokemon to the pool on click (name still opens modal via its own ref).
$('#tb-suggest').addEventListener('click', e => {
  const card = e.target.closest('[data-add]');
  if (!card) return;
  const name = decodeURIComponent(card.dataset.add);
  const poke = ALL_POKEMON.find(p => p.name === name);
  const add = makeSearch._pools && makeSearch._pools['tb-search'];
  if (poke && add) add(poke);
});

// Pull owned Pokémon (base forms) from My Box into the builder pool.
$('#tb-load-box').addEventListener('click', () => {
  if (!BOX.length) { alert(t('tb.box.empty')); return; }
  const add = makeSearch._pools && makeSearch._pools['tb-search'];
  BOX.forEach(b => {
    const poke = ALL_POKEMON.find(p => p.name.toLowerCase() === b.name.toLowerCase()) || b;
    if (add) add(poke);
  });
});
$('#tb-clear').addEventListener('click', () => makeSearch._clear['tb-search']());

$('#tb-build-btn').addEventListener('click', async () => {
  const btn = $('#tb-build-btn');
  btn.textContent = t('tb.building');
  btn.disabled = true;

  const res = await fetch('/api/team/build', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pokemon: tbPool.map(p => p.name) }),
  }).then(r => r.json());

  btn.textContent = t('tb.build');
  btn.disabled = tbPool.length === 0;

  if (res.error) { alert(res.error); return; }
  lastBuild = res;
  buildTbState(res);    // fresh team → reset movesets/editor
  renderBuild(res);
});

// Seed the editable team state from a /api/team/build response.
function buildTbState(res) {
  tbEditing = -1;
  tbTeam = res.team.map(p => {
    const build = p.best_build || {};
    const selected = (build.moves || []).map(m => ({ ...m }));
    return {
      name: p.name, tier: p.tier, types: p.types || [],
      image_url: p.image_url, role: p.role, build,
      movePool: p.move_pool || [],
      bestNames: new Set(selected.map(m => m.name)),  // the source-recommended four
      selected,
    };
  });
  const a = res.analysis;
  tbCoverage = { covered_types: a.covered_types, uncovered_types: a.uncovered_types };
  tbShared = a.shared_weaknesses || {};
  tbScore = a.score;
}

// Re-render the team result (language switch reuses existing state + edits).
function renderBuild(res) {
  lastBuild = res;
  if (!tbTeam.length) buildTbState(res);
  renderTbCards();
  renderTbAnalysis();
  $('#tb-result').classList.remove('hidden');
}

// One editable move pill. `best` = recommended by sources, `selected` = in the
// current moveset, `editable` = clickable inside the editor.
function tbMovePill(m, { best, selected, editable }) {
  const ty  = m.type || '';
  const bg  = ty ? `style="background:var(--${ty})"` : '';
  const cat = m.category ? `<span class="move-cat cat-${m.category}">${catAbbr(m.category)}</span>` : '';
  const cls = ['move-pill', `type-text-${ty}`];
  if (best) cls.push('move-best');
  if (editable) { cls.push('move-edit'); cls.push(selected ? 'move-sel' : 'move-off'); }
  const data = editable ? `data-tbmove="${encodeURIComponent(m.name)}"` : '';
  return `<span class="${cls.join(' ')}" ${bg} data-type="${ty}" ${data}>${tMove(m.name)}${cat}</span>`;
}

function tbCard(m, idx) {
  const types = m.types.map(typeBadge).join('');
  const nat   = m.build && m.build.nature
    ? `<div class="card-nature">${tNature(m.build.nature)} | ${tAbility(m.build.ability)}</div>` : '';
  const role  = m.role ? `<div class="card-role">${roleLabel(m.role)}</div>` : '';
  const moves = m.selected
    .map(mv => tbMovePill(mv, { best: m.bestNames.has(mv.name), selected: true, editable: false }))
    .join('');

  const editing = tbEditing === idx;
  let editor = '';
  if (editing && m.movePool.length) {
    const pool = m.movePool
      .map(mv => tbMovePill(mv, {
        best: m.bestNames.has(mv.name),
        selected: m.selected.some(s => s.name === mv.name),
        editable: true,
      }))
      .join('');
    editor = `<div class="tb-move-editor">
        <p class="tb-edit-hint">${t('tb.moves.hint')}</p>
        <div class="move-pills">${pool}</div>
      </div>`;
  }
  const editBtn = m.movePool.length > 1
    ? `<button class="ghost-btn tb-edit-btn" type="button" data-tb-edit="${idx}">${editing ? t('tb.moves.done') : t('tb.moves.edit')}</button>`
    : '';

  return `
    <div class="poke-card tb-card" data-tb-idx="${idx}">
      <div class="card-head clickable" ${pokeRef(m.name)}>
        ${sprite(m, 'sprite sm')}
        <div class="card-name">${tName(m.name)} ${tierBadge(m.tier || '')}</div>
      </div>
      ${role}
      <div style="margin-bottom:8px">${types}</div>
      ${nat}
      ${itemTag(m.build)}
      <div class="move-pills">${moves}</div>
      ${editBtn}
      ${editor}
    </div>`;
}

function renderTbCards() {
  $('#tb-team-cards').innerHTML = tbTeam.map(tbCard).join('');
}

function renderTbAnalysis() {
  const weakHtml = Object.entries(tbShared)
    .map(([ty, members]) => {
      const ms = members.map(m => {
        const ix = m.lastIndexOf(' (');
        return ix > 0 ? tName(m.slice(0, ix)) + m.slice(ix) : tName(m);
      }).join(', ');
      return `<span class="warn">${tType(ty)}: ${ms}</span>`;
    })
    .join('<br>');

  $('#tb-analysis').innerHTML = `
    <h4>${t('tb.analysis.title', { score: tbScore })}</h4>
    <p class="good">${t('tb.analysis.covers')} ${tbCoverage.covered_types.map(typeBadge).join(' ')}</p>
    ${tbCoverage.uncovered_types.length ? `<p class="warn">${t('tb.analysis.nocover')} ${tbCoverage.uncovered_types.map(typeBadge).join(' ')}</p>` : ''}
    ${weakHtml ? `<p style="margin-top:8px"><strong>${t('tb.analysis.shared')}</strong><br>${weakHtml}</p>` : ''}
  `;
}

// Toggle a move in/out of a slot's moveset (max 4; adding a 5th drops the oldest).
function toggleMove(idx, name) {
  const slot = tbTeam[idx];
  const inSet = slot.selected.some(s => s.name === name);
  let selected;
  if (inSet) {
    selected = slot.selected.filter(s => s.name !== name);
  } else {
    const move = slot.movePool.find(s => s.name === name);
    if (!move) return;
    selected = [...slot.selected, { ...move }];
    if (selected.length > 4) selected = selected.slice(selected.length - 4);
  }
  tbTeam = tbTeam.map((s, i) => (i === idx ? { ...s, selected } : s));
  renderTbCards();
  updateTbCoverage();
}

// Recompute offensive coverage from the edited movesets (server keeps the type
// chart as the single source of truth) and re-render the analysis box.
async function updateTbCoverage() {
  const members = tbTeam.map(s => ({
    name: s.name,
    types: s.types,
    move_types: s.selected.map(mv => mv.type).filter(Boolean),
  }));
  const res = await fetch('/api/team/coverage', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ members }),
  }).then(r => r.json()).catch(() => null);
  if (!res) return;
  tbCoverage = res;
  renderTbAnalysis();
}

// Delegated clicks for the editable team cards (edit toggle + move selection).
$('#tb-team-cards').addEventListener('click', e => {
  const editBtn = e.target.closest('[data-tb-edit]');
  if (editBtn) {
    const i = Number(editBtn.dataset.tbEdit);
    tbEditing = tbEditing === i ? -1 : i;
    renderTbCards();
    return;
  }
  const pill = e.target.closest('[data-tbmove]');
  if (pill) {
    const card = pill.closest('[data-tb-idx]');
    if (!card) return;
    toggleMove(Number(card.dataset.tbIdx), decodeURIComponent(pill.dataset.tbmove));
  }
});

// ── MATCHUP ADVISOR ───────────────────────────────────────────────────────────
makeSearch('my-search',  'my-suggestions',  myPool,  'my-pool',  null);
makeSearch('opp-search', 'opp-suggestions', oppPool, 'opp-pool', null);

$('#matchup-btn').addEventListener('click', async () => {
  if (!myPool.length) { alert(t('mu.needteam')); return; }

  const btn = $('#matchup-btn');
  btn.textContent = t('mu.analysing');
  btn.disabled = true;

  const res = await fetch('/api/matchup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      my_team: myPool.map(p => p.name),
      opponent_team: oppPool.map(p => p.name),
    }),
  }).then(r => r.json());

  btn.textContent = t('mu.analyse');
  btn.disabled = false;

  if (res.error) { alert(res.error); return; }
  renderMatchup(res);
});

function renderMatchup(res) {
  lastMatchup = res;
  $('#bring-cards').innerHTML = res.bring.map(p => pokeCard(p, p.best_build)).join('');

  if (res.lead) {
    const lead = res.bring.find(p => p.name === res.lead.name) || res.lead;
    $('#lead-card').innerHTML = pokeCard(lead, lead.best_build);
    const target = res.lead_target || (res.lead_reasoning || '');
    $('#lead-reason').textContent = res.lead_target
      ? t('mu.lead.reason', { name: tName(res.lead_target) })
      : res.lead_reasoning;
  }

  if (res.full_scores.length) {
    const thead = `<tr><th>${t('mu.col.pokemon')}</th><th>${t('mu.col.tier')}</th><th>${t('mu.col.score')}</th>
      ${(res.full_scores[0].per_opponent || []).map(o => `<th>${t('mu.col.vs', { name: tName(o.name) })}</th>`).join('')}
    </tr>`;
    const rows = res.full_scores.map(s => {
      const isBring = res.bring.some(p => p.name === s.name);
      const oppCells = (s.per_opponent || []).map(o =>
        `<td style="color:${o.offensive_mult >= 2 ? '#4caf50' : o.offensive_mult <= 0.5 ? '#f44336' : 'inherit'}">
          ${o.offensive_mult}x${o.survives ? '' : ' ⚠️'}
        </td>`
      ).join('');
      return `<tr ${isBring ? 'style="font-weight:600"' : ''}>
        <td class="clickable" ${pokeRef(s.name)}>${isBring ? '✅ ' : ''}${tName(s.name)}</td>
        <td>${tierBadge(s.tier)}</td>
        <td>${s.total_score}</td>
        ${oppCells}
      </tr>`;
    }).join('');
    $('#score-table').innerHTML = `<table class="score-table"><thead>${thead}</thead><tbody>${rows}</tbody></table>`;
  }

  $('#matchup-result').classList.remove('hidden');
}

// ── META TEAMS ────────────────────────────────────────────────────────────────
async function loadMetaTeams() {
  META_TEAMS = await fetch('/api/teams').then(r => r.json());
  renderMetaTeams();
}

function renderMetaTeams() {
  const container = $('#meta-teams-container');
  if (!META_TEAMS.length) { container.textContent = t('meta.none'); return; }

  container.innerHTML = META_TEAMS.map(team => {
    const members = team.members.map(m => `
      <div class="team-member clickable" ${pokeRef(m.pokemon)}>
        ${sprite(m, 'sprite md')}
        <div class="team-member-name">${tName(m.pokemon)}</div>
        <div class="team-member-types">${(m.types || []).map(typeBadge).join('')}</div>
        ${m.held_item ? `<div class="team-member-item">${m.held_item_image ? `<img class="item-img" src="${m.held_item_image}" alt="" loading="lazy">` : '🎒'}${tItem(m.held_item)}</div>` : ''}
      </div>`).join('');
    return `
      <div class="team-card">
        <div class="team-card-head">
          <h4>${team.name}</h4>
          ${team.source_url ? `<a class="muted source-link" href="${team.source_url}" target="_blank" rel="noopener">${t('meta.guide')}</a>` : ''}
        </div>
        ${team.strategy ? `<p class="team-strategy">${team.strategy}</p>` : ''}
        <div class="team-member-grid">${members}</div>
      </div>`;
  }).join('');
}

// ── MY BOX ────────────────────────────────────────────────────────────────────
const BOX_KEY = 'pokeBox.v1';
let BOX = [];
let boxFilter = 'all';

let _boxSeq = 0;
function boxId() { return 'b' + Date.now().toString(36) + (_boxSeq++); }

function loadBox() {
  try { BOX = JSON.parse(localStorage.getItem(BOX_KEY)) || []; }
  catch { BOX = []; }
  BOX.forEach(b => { if (!b.id) b.id = boxId(); });  // backfill legacy entries
}
function saveBox() { localStorage.setItem(BOX_KEY, JSON.stringify(BOX)); }

function boxAdd(p) {
  if (p.is_mega) return;  // Megas are battle forms (a stone), not owned Pokémon
  BOX.push({ id: boxId(), name: p.name, types: p.types || [], image_url: p.image_url,
             tier: p.tier, kind: 'permanent', daysLeft: 7 });
  saveBox(); renderBox();
}
function boxRemove(id) { BOX = BOX.filter(b => b.id !== id); saveBox(); renderBox(); }
function boxSetKind(id, kind) {
  const b = BOX.find(x => x.id === id);
  if (!b) return;
  b.kind = kind;
  if (kind === 'trial' && !(b.daysLeft > 0)) b.daysLeft = 7;
  saveBox(); renderBox();
}
function boxSetDays(id, days) {
  const b = BOX.find(x => x.id === id);
  if (b) b.daysLeft = Math.max(0, Math.min(7, days | 0));
  saveBox(); renderBox();
}

function renderBox() {
  const grid = $('#box-grid');
  const perm = BOX.filter(b => b.kind === 'permanent').length;
  const trial = BOX.length - perm;
  $('#box-count').textContent = BOX.length
    ? t('box.count', { n: BOX.length, perm, trial }) : '';
  $('#box-empty').classList.toggle('hidden', BOX.length > 0);

  const items = BOX.filter(b => boxFilter === 'all' || b.kind === boxFilter);
  grid.innerHTML = items.map(b => {
    const types = (b.types || []).map(typeBadge).join('');
    const isTrial = b.kind === 'trial';
    const expired = isTrial && b.daysLeft <= 0;
    const dayWord = b.daysLeft === 1 ? t('box.day') : t('box.days');
    const trialCtrls = isTrial ? `
      <div class="box-trial ${expired ? 'expired' : ''}">
        <label class="box-days-label">${t('box.daysleft')}
          <input type="number" min="0" max="7" value="${b.daysLeft}" class="box-days" data-id="${b.id}">
        </label>
        ${expired ? `<span class="warn">${t('box.expired')}</span>`
                  : `<span class="muted">${t('box.clock', { n: b.daysLeft, dayWord })}</span>`}
        <button class="mini-btn promote" data-id="${b.id}">${t('box.makeperm')}</button>
      </div>` : '';
    return `
      <div class="poke-card box-card ${b.kind} ${expired ? 'expired' : ''}">
        <div class="card-head">
          ${sprite(b, 'sprite sm')}
          <div class="card-name clickable" ${pokeRef(b.name)}>${tName(b.name)} ${b.tier ? tierBadge(b.tier) : ''}</div>
          <button class="box-remove" data-id="${b.id}" title="${t('box.remove')}">✕</button>
        </div>
        <div style="margin-bottom:8px">${types}</div>
        <div class="box-kind">
          <button class="kind-btn ${!isTrial ? 'active' : ''}" data-id="${b.id}" data-kind="permanent">${t('box.kind.permanent')}</button>
          <button class="kind-btn ${isTrial ? 'active' : ''}" data-id="${b.id}" data-kind="trial">${t('box.kind.trial')}</button>
        </div>
        ${trialCtrls}
      </div>`;
  }).join('');
}

// Box grid event delegation
$('#box-grid').addEventListener('click', e => {
  const kindBtn = e.target.closest('.kind-btn');
  if (kindBtn) { boxSetKind(kindBtn.dataset.id, kindBtn.dataset.kind); return; }
  const promote = e.target.closest('.promote');
  if (promote) { boxSetKind(promote.dataset.id, 'permanent'); return; }
  const rm = e.target.closest('.box-remove');
  if (rm) { boxRemove(rm.dataset.id); return; }
});
$('#box-grid').addEventListener('change', e => {
  const days = e.target.closest('.box-days');
  if (days) boxSetDays(days.dataset.id, +days.value);
});

// Box filters
$$('.box-filter').forEach(btn => btn.addEventListener('click', () => {
  $$('.box-filter').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  boxFilter = btn.dataset.filter;
  renderBox();
}));

// Box search (adds to box instead of a team pool)
(function boxSearch() {
  const input = $('#box-search');
  const sug = $('#box-suggestions');
  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    if (!q) { sug.classList.remove('open'); return; }
    const matches = ALL_POKEMON
      .filter(p => !p.is_mega && searchMatch(p, q)).slice(0, 12);
    if (!matches.length) { sug.classList.remove('open'); return; }
    sug.innerHTML = matches.map(p =>
      `<div class="suggestion-item" data-name="${encodeURIComponent(p.name)}">
        ${sprite(p, 'sprite xs')}${tierBadge(p.tier)} <strong>${tName(p.name)}</strong>
        ${(p.types || []).map(typeBadge).join('')}
      </div>`).join('');
    sug.classList.add('open');
    sug.querySelectorAll('.suggestion-item').forEach(el => el.addEventListener('click', () => {
      const poke = ALL_POKEMON.find(p => p.name === decodeURIComponent(el.dataset.name));
      if (poke) boxAdd(poke);
      input.value = ''; sug.classList.remove('open');
    }));
  });
  document.addEventListener('click', e => {
    if (!input.contains(e.target) && !sug.contains(e.target)) sug.classList.remove('open');
  });
})();

loadBox();
renderBox();
init();
