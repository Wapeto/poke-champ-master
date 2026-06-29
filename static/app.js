"use strict";

// ── State ─────────────────────────────────────────────────────────────────────
let ALL_POKEMON = [];   // [{name, tier, types, image_url}]
let TIER_DATA   = {};   // grouped tier list, cached for filtering
const tbPool   = [];    // team-builder pool
const myPool   = [];    // matchup my team
const oppPool  = [];    // matchup opponent team

// ── Helpers ───────────────────────────────────────────────────────────────────
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

function typeBadge(type) {
  return `<span class="type-badge type-${type}">${type}</span>`;
}

function tierBadge(tier) {
  const cls = tier === 'A+' ? 'Ap' : tier;
  return `<span class="tier-label tier-${cls}">${tier}</span>`;
}

function sprite(p, cls = 'sprite') {
  if (!p || !p.image_url) return '';
  return `<img class="${cls}" src="${p.image_url}" alt="${p.name}" loading="lazy">`;
}

const CAT_ABBR = { Physical: 'PHY', Special: 'SPE', Status: 'STA' };

function movePill(m) {
  const t = m.type || '';
  const bg = t ? `style="background:var(--${t})"` : '';
  const cat = m.category
    ? `<span class="move-cat cat-${m.category}">${CAT_ABBR[m.category] || ''}</span>` : '';
  return `<span class="move-pill type-text-${t}" ${bg} data-type="${t}">${m.name}${cat}</span>`;
}

function moveList(build) {
  if (!build || !build.moves) return '';
  return `<div class="move-pills">${build.moves.map(movePill).join('')}</div>`;
}

function itemTag(build) {
  if (!build || !build.held_item) return '';
  const icon = build.held_item_image
    ? `<img class="item-img" src="${build.held_item_image}" alt="" loading="lazy">` : '🎒';
  return `<div class="card-item">${icon}<span>${build.held_item}</span></div>`;
}

// Any element with data-poke opens the detail modal (event delegation).
function pokeRef(name) {
  return `data-poke="${encodeURIComponent(name)}"`;
}

function pokeCard(p, build = null, role = null) {
  const types = (p.types || []).map(typeBadge).join('');
  const nat   = build ? `<div class="card-nature">${build.nature} | ${build.ability}</div>` : '';
  const roleHtml = role ? `<div class="card-role">${role}</div>` : '';
  return `
    <div class="poke-card clickable" ${pokeRef(p.name)}>
      <div class="card-head">
        ${sprite(p, 'sprite sm')}
        <div class="card-name">${p.name} ${tierBadge(p.tier || '')}</div>
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
  ALL_POKEMON = await fetch('/api/pokemon').then(r => r.json());
  loadTierList();
  loadMetaTeams();
}

// ── TIER LIST ─────────────────────────────────────────────────────────────────
const TIER_ORDER = ['S', 'A+', 'A', 'B', 'C', 'D'];
const BADGE_CLS  = { 'S':'S', 'A+':'Ap', 'A':'A', 'B':'B', 'C':'C', 'D':'D' };

async function loadTierList() {
  TIER_DATA = await fetch('/api/tier-list').then(r => r.json());
  renderTierList('');
}

function renderTierList(query) {
  const q = query.trim().toLowerCase();
  const container = $('#tier-list-container');

  const html = TIER_ORDER.map(tier => {
    const list = (TIER_DATA[tier] || []).filter(p =>
      !q || p.name.toLowerCase().includes(q) ||
      (p.types || []).some(t => t.toLowerCase().includes(q))
    );
    if (!list.length) return '';
    const chips = list.map(p => {
      const types = (p.types || []).map(typeBadge).join('');
      return `<div class="poke-chip clickable" ${pokeRef(p.name)} title="${(p.types||[]).join('/')}">
        ${sprite(p, 'sprite xs')}<strong>${p.name}</strong> ${types}
      </div>`;
    }).join('');
    return `
      <div class="tier-section">
        <div class="tier-header">
          <div class="tier-badge ${BADGE_CLS[tier]}">${tier}</div>
          <span class="muted">${list.length} Pokémon</span>
        </div>
        <div class="tier-pokemon-row">${chips}</div>
      </div>`;
  }).join('');

  container.innerHTML = html || '<p class="muted">No Pokémon match that filter.</p>';
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

function closeModal() { modal.classList.add('hidden'); }
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
    `<span class="type-badge type-${en.type}">${en.type}${en.mult && en.mult !== 0 ? ` ${en.mult}×` : ''}</span>`
  ).join('');
  return `<div class="matchup-line"><span class="matchup-label ${cls}">${label}</span>${badges}</div>`;
}

async function openPokemonModal(name) {
  openModal();
  modalBody.innerHTML = '<p class="muted">Loading…</p>';
  let d;
  try {
    const res = await fetch('/api/pokemon/' + encodeURIComponent(name));
    if (!res.ok) throw new Error('not found');
    d = await res.json();
  } catch {
    modalBody.innerHTML = `<p class="warn">Could not load ${name}.</p>`;
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
        <span class="stat-key">${k.toUpperCase()}</span>
        <span class="stat-bar"><span class="stat-fill" style="width:${pct}%"></span></span>
        <span class="stat-val">${v}</span>
      </div>`;
    }).join('');

  const moves = (d.best_moves || []).map(movePill).join('');

  const builds = (d.builds || []).map((b, i) => `
    <div class="build-block">
      <div class="build-title">Build ${i + 1} — ${b.nature || ''} ${b.ability ? '| ' + b.ability : ''}</div>
      ${itemTag(b)}
      ${moveList(b)}
    </div>`).join('');

  const sources = (d.sources || []).length
    ? `<div class="sources">Data: ${d.sources.join(' · ')}</div>` : '';

  const teammates = (d.best_teammates || []).map(n =>
    `<span class="poke-chip clickable inline" ${pokeRef(n)}>${n}</span>`).join('');
  const counters = (d.counters || []).map(n =>
    `<span class="poke-chip clickable inline" ${pokeRef(n)}>${n}</span>`).join('');

  modalBody.innerHTML = `
    <div class="modal-header">
      ${d.image_url ? `<img class="sprite lg" src="${d.image_url}" alt="${d.name}">` : ''}
      <div>
        <h2 class="modal-name">${d.name} ${d.tier ? tierBadge(d.tier) : ''}</h2>
        <div class="modal-types">${types}</div>
        ${d.build_url ? `<a class="muted source-link" href="${d.build_url}" target="_blank" rel="noopener">Game8 build ↗</a>` : ''}
        ${sources}
      </div>
    </div>

    ${d.description ? `<p class="modal-desc">${d.description}</p>` : ''}

    <div class="modal-grid">
      <div class="modal-col">
        ${statRows ? `<h4 class="modal-sub">Base Stats</h4><div class="stats">${statRows}</div>` : ''}
        <h4 class="modal-sub">Type Matchups</h4>
        ${matchupRow('Weak to', d.weak_to || [], 'bad')}
        ${matchupRow('Resists', d.resists || [], 'good')}
        ${matchupRow('Immune', d.immune_to || [], 'good')}
      </div>
      <div class="modal-col">
        ${moves ? `<h4 class="modal-sub">Best Moves</h4><div class="move-list">${moves}</div>` : ''}
        ${teammates ? `<h4 class="modal-sub">Best Teammates</h4><div class="chip-wrap">${teammates}</div>` : ''}
        ${counters ? `<h4 class="modal-sub">Countered By</h4><div class="chip-wrap">${counters}</div>` : ''}
      </div>
    </div>

    ${builds ? `<h4 class="modal-sub">Recommended Builds</h4><div class="build-grid">${builds}</div>` : ''}
  `;
}

// ── SEARCH AUTOCOMPLETE ───────────────────────────────────────────────────────
function makeSearch(inputId, sugId, pool, chipListId, btnToEnable) {
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
  }

  function renderChips() {
    chips.innerHTML = pool.map((p, i) => {
      const types = (p.types || []).map(typeBadge).join('');
      return `<div class="chip">
        ${sprite(p, 'sprite xs')}${types} <span class="clickable" ${pokeRef(p.name)}>${p.name}</span>
        <span class="remove" data-i="${i}">✕</span>
      </div>`;
    }).join('');
    chips.querySelectorAll('.remove').forEach(el => {
      el.addEventListener('click', () => {
        pool.splice(+el.dataset.i, 1);
        renderChips();
        if (btnToEnable) $('#' + btnToEnable).disabled = pool.length === 0;
      });
    });
  }

  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    if (!q) { sug.classList.remove('open'); return; }
    const matches = ALL_POKEMON.filter(p => p.name.toLowerCase().includes(q)).slice(0, 12);
    if (!matches.length) { sug.classList.remove('open'); return; }
    sug.innerHTML = matches.map(p => {
      const types = (p.types || []).map(typeBadge).join('');
      return `<div class="suggestion-item" data-name="${p.name}">
        ${sprite(p, 'sprite xs')}${tierBadge(p.tier)} <strong>${p.name}</strong> ${types}
      </div>`;
    }).join('');
    sug.classList.add('open');
    sug.querySelectorAll('.suggestion-item').forEach(el => {
      el.addEventListener('click', () => {
        const poke = ALL_POKEMON.find(p => p.name === el.dataset.name);
        if (poke) addPoke(poke);
      });
    });
  });

  document.addEventListener('click', e => {
    if (!input.contains(e.target) && !sug.contains(e.target)) sug.classList.remove('open');
  });
}

// ── TEAM BUILDER ──────────────────────────────────────────────────────────────
makeSearch('tb-search', 'tb-suggestions', tbPool, 'tb-pool', 'tb-build-btn');

$('#tb-build-btn').addEventListener('click', async () => {
  const btn = $('#tb-build-btn');
  btn.textContent = 'Building…';
  btn.disabled = true;

  const res = await fetch('/api/team/build', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pokemon: tbPool.map(p => p.name) }),
  }).then(r => r.json());

  btn.textContent = 'Build Best Team';
  btn.disabled = tbPool.length === 0;

  if (res.error) { alert(res.error); return; }

  $('#tb-team-cards').innerHTML = res.team.map(p => pokeCard(p, p.best_build, p.role)).join('');

  const a = res.analysis;
  const weakHtml = Object.entries(a.shared_weaknesses)
    .map(([t, members]) => `<span class="warn">${t}: ${members.join(', ')}</span>`)
    .join('<br>');

  $('#tb-analysis').innerHTML = `
    <h4>Team Analysis  (score: ${a.score})</h4>
    <p class="good">✅ Covers: ${a.covered_types.map(typeBadge).join(' ')}</p>
    ${a.uncovered_types.length ? `<p class="warn">⚠️ No coverage vs: ${a.uncovered_types.map(typeBadge).join(' ')}</p>` : ''}
    ${weakHtml ? `<p style="margin-top:8px"><strong>Shared weaknesses:</strong><br>${weakHtml}</p>` : ''}
  `;

  $('#tb-result').classList.remove('hidden');
});

// ── MATCHUP ADVISOR ───────────────────────────────────────────────────────────
makeSearch('my-search',  'my-suggestions',  myPool,  'my-pool',  null);
makeSearch('opp-search', 'opp-suggestions', oppPool, 'opp-pool', null);

$('#matchup-btn').addEventListener('click', async () => {
  if (!myPool.length) { alert('Add at least one Pokémon to your team.'); return; }

  const btn = $('#matchup-btn');
  btn.textContent = 'Analysing…';
  btn.disabled = true;

  const res = await fetch('/api/matchup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      my_team: myPool.map(p => p.name),
      opponent_team: oppPool.map(p => p.name),
    }),
  }).then(r => r.json());

  btn.textContent = 'Analyse Matchup';
  btn.disabled = false;

  if (res.error) { alert(res.error); return; }

  $('#bring-cards').innerHTML = res.bring.map(p => pokeCard(p, p.best_build)).join('');

  if (res.lead) {
    const lead = res.bring.find(p => p.name === res.lead.name) || res.lead;
    $('#lead-card').innerHTML = pokeCard(lead, lead.best_build);
    $('#lead-reason').textContent = res.lead_reasoning;
  }

  if (res.full_scores.length) {
    const thead = `<tr><th>Pokémon</th><th>Tier</th><th>Score</th>
      ${(res.full_scores[0].per_opponent || []).map(o => `<th>vs ${o.name}</th>`).join('')}
    </tr>`;
    const rows = res.full_scores.map(s => {
      const isBring = res.bring.some(p => p.name === s.name);
      const oppCells = (s.per_opponent || []).map(o =>
        `<td style="color:${o.offensive_mult >= 2 ? '#4caf50' : o.offensive_mult <= 0.5 ? '#f44336' : 'inherit'}">
          ${o.offensive_mult}x${o.survives ? '' : ' ⚠️'}
        </td>`
      ).join('');
      return `<tr ${isBring ? 'style="font-weight:600"' : ''}>
        <td class="clickable" ${pokeRef(s.name)}>${isBring ? '✅ ' : ''}${s.name}</td>
        <td>${tierBadge(s.tier)}</td>
        <td>${s.total_score}</td>
        ${oppCells}
      </tr>`;
    }).join('');
    $('#score-table').innerHTML = `<table class="score-table"><thead>${thead}</thead><tbody>${rows}</tbody></table>`;
  }

  $('#matchup-result').classList.remove('hidden');
});

// ── META TEAMS ────────────────────────────────────────────────────────────────
async function loadMetaTeams() {
  const teams = await fetch('/api/teams').then(r => r.json());
  const container = $('#meta-teams-container');
  if (!teams.length) { container.textContent = 'No teams available.'; return; }

  container.innerHTML = teams.map(team => {
    const members = team.members.map(m => `
      <div class="team-member clickable" ${pokeRef(m.pokemon)}>
        ${sprite(m, 'sprite md')}
        <div class="team-member-name">${m.pokemon}</div>
        <div class="team-member-types">${(m.types || []).map(typeBadge).join('')}</div>
        ${m.held_item ? `<div class="team-member-item">${m.held_item_image ? `<img class="item-img" src="${m.held_item_image}" alt="" loading="lazy">` : '🎒'}${m.held_item}</div>` : ''}
      </div>`).join('');
    return `
      <div class="team-card">
        <div class="team-card-head">
          <h4>${team.name}</h4>
          ${team.source_url ? `<a class="muted source-link" href="${team.source_url}" target="_blank" rel="noopener">guide ↗</a>` : ''}
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

function loadBox() {
  try { BOX = JSON.parse(localStorage.getItem(BOX_KEY)) || []; }
  catch { BOX = []; }
}
function saveBox() { localStorage.setItem(BOX_KEY, JSON.stringify(BOX)); }

function boxAdd(p) {
  if (BOX.find(b => b.name.toLowerCase() === p.name.toLowerCase())) return;
  BOX.push({ name: p.name, types: p.types || [], image_url: p.image_url, tier: p.tier,
             kind: 'permanent', daysLeft: 7 });
  saveBox(); renderBox();
}
function boxRemove(name) { BOX = BOX.filter(b => b.name !== name); saveBox(); renderBox(); }
function boxSetKind(name, kind) {
  const b = BOX.find(x => x.name === name);
  if (!b) return;
  b.kind = kind;
  if (kind === 'trial' && !(b.daysLeft > 0)) b.daysLeft = 7;
  saveBox(); renderBox();
}
function boxSetDays(name, days) {
  const b = BOX.find(x => x.name === name);
  if (b) b.daysLeft = Math.max(0, Math.min(7, days | 0));
  saveBox(); renderBox();
}

function renderBox() {
  const grid = $('#box-grid');
  const perm = BOX.filter(b => b.kind === 'permanent').length;
  const trial = BOX.length - perm;
  $('#box-count').textContent = BOX.length
    ? `${BOX.length} in box · ${perm} permanent · ${trial} trial` : '';
  $('#box-empty').classList.toggle('hidden', BOX.length > 0);

  const items = BOX.filter(b => boxFilter === 'all' || b.kind === boxFilter);
  grid.innerHTML = items.map(b => {
    const enc = encodeURIComponent(b.name);
    const types = (b.types || []).map(typeBadge).join('');
    const isTrial = b.kind === 'trial';
    const expired = isTrial && b.daysLeft <= 0;
    const trialCtrls = isTrial ? `
      <div class="box-trial ${expired ? 'expired' : ''}">
        <label class="box-days-label">Days left
          <input type="number" min="0" max="7" value="${b.daysLeft}" class="box-days" data-name="${enc}">
        </label>
        ${expired ? '<span class="warn">⚠ expired</span>'
                  : `<span class="muted">${b.daysLeft} day${b.daysLeft === 1 ? '' : 's'} on the 7-day clock</span>`}
        <button class="mini-btn promote" data-name="${enc}">Make Permanent</button>
      </div>` : '';
    return `
      <div class="poke-card box-card ${b.kind} ${expired ? 'expired' : ''}">
        <div class="card-head">
          ${sprite(b, 'sprite sm')}
          <div class="card-name clickable" ${pokeRef(b.name)}>${b.name} ${b.tier ? tierBadge(b.tier) : ''}</div>
          <button class="box-remove" data-name="${enc}" title="Remove">✕</button>
        </div>
        <div style="margin-bottom:8px">${types}</div>
        <div class="box-kind">
          <button class="kind-btn ${!isTrial ? 'active' : ''}" data-name="${enc}" data-kind="permanent">Permanent</button>
          <button class="kind-btn ${isTrial ? 'active' : ''}" data-name="${enc}" data-kind="trial">Trial</button>
        </div>
        ${trialCtrls}
      </div>`;
  }).join('');
}

// Box grid event delegation
$('#box-grid').addEventListener('click', e => {
  const kindBtn = e.target.closest('.kind-btn');
  if (kindBtn) { boxSetKind(decodeURIComponent(kindBtn.dataset.name), kindBtn.dataset.kind); return; }
  const promote = e.target.closest('.promote');
  if (promote) { boxSetKind(decodeURIComponent(promote.dataset.name), 'permanent'); return; }
  const rm = e.target.closest('.box-remove');
  if (rm) { boxRemove(decodeURIComponent(rm.dataset.name)); return; }
});
$('#box-grid').addEventListener('change', e => {
  const days = e.target.closest('.box-days');
  if (days) boxSetDays(decodeURIComponent(days.dataset.name), +days.value);
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
    const matches = ALL_POKEMON.filter(p => p.name.toLowerCase().includes(q)).slice(0, 12);
    if (!matches.length) { sug.classList.remove('open'); return; }
    sug.innerHTML = matches.map(p =>
      `<div class="suggestion-item" data-name="${p.name}">
        ${sprite(p, 'sprite xs')}${tierBadge(p.tier)} <strong>${p.name}</strong>
        ${(p.types || []).map(typeBadge).join('')}
      </div>`).join('');
    sug.classList.add('open');
    sug.querySelectorAll('.suggestion-item').forEach(el => el.addEventListener('click', () => {
      const poke = ALL_POKEMON.find(p => p.name === el.dataset.name);
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
