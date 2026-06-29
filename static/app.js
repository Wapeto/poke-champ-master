"use strict";

// ── State ─────────────────────────────────────────────────────────────────────
let ALL_POKEMON = [];   // [{name, tier, types}]
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

function pokeCard(p, build = null, role = null) {
  const types = (p.types || []).map(typeBadge).join('');
  const moves = build ? build.moves.map(m => `<span>• ${m.name}</span>`).join('') : '';
  const item  = build ? `<div class="card-item">🎒 ${build.held_item}</div>` : '';
  const nat   = build ? `<div class="card-nature">${build.nature} | ${build.ability}</div>` : '';
  const roleHtml = role ? `<div class="card-role">${role}</div>` : '';
  return `
    <div class="poke-card">
      <div class="card-name">${p.name} ${tierBadge(p.tier || '')}</div>
      ${roleHtml}
      <div style="margin-bottom:8px">${types}</div>
      ${nat}
      ${item}
      <div class="card-moves">${moves}</div>
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
async function loadTierList() {
  const data = await fetch('/api/tier-list').then(r => r.json());
  const container = $('#tier-list-container');
  const tierOrder = ['S', 'A+', 'A', 'B', 'C', 'D'];
  const badgeCls  = { 'S':'S', 'A+':'Ap', 'A':'A', 'B':'B', 'C':'C', 'D':'D' };

  container.innerHTML = tierOrder.map(tier => {
    const list = data[tier] || [];
    if (!list.length) return '';
    const chips = list.map(p => {
      const types = (p.types || []).map(typeBadge).join('');
      return `<div class="poke-chip" title="${(p.types||[]).join('/')}">
        <strong>${p.name}</strong> ${types}
      </div>`;
    }).join('');
    return `
      <div class="tier-section">
        <div class="tier-header">
          <div class="tier-badge ${badgeCls[tier]}">${tier}</div>
          <span class="muted">${list.length} Pokémon</span>
        </div>
        <div class="tier-pokemon-row">${chips}</div>
      </div>`;
  }).join('');
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
    if (btnToEnable) {
      const btn = $('#' + btnToEnable);
      btn.disabled = pool.length === 0;
    }
  }

  function renderChips() {
    chips.innerHTML = pool.map((p, i) => {
      const types = (p.types || []).map(typeBadge).join('');
      return `<div class="chip">
        ${types} <span>${p.name}</span>
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
    const matches = ALL_POKEMON
      .filter(p => p.name.toLowerCase().includes(q))
      .slice(0, 12);
    if (!matches.length) { sug.classList.remove('open'); return; }
    sug.innerHTML = matches.map(p => {
      const types = (p.types || []).map(typeBadge).join('');
      return `<div class="suggestion-item" data-name="${p.name}">
        ${tierBadge(p.tier)} <strong>${p.name}</strong> ${types}
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
    if (!input.contains(e.target) && !sug.contains(e.target)) {
      sug.classList.remove('open');
    }
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

  $('#tb-team-cards').innerHTML = res.team.map(p =>
    pokeCard(p, p.best_build, p.role)
  ).join('');

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

  // Bring 3
  $('#bring-cards').innerHTML = res.bring.map(p =>
    pokeCard(p, p.best_build)
  ).join('');

  // Lead
  if (res.lead) {
    const lead = res.bring.find(p => p.name === res.lead.name) || res.lead;
    $('#lead-card').innerHTML = pokeCard(lead, lead.best_build);
    $('#lead-reason').textContent = res.lead_reasoning;
  }

  // Score table
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
        <td>${isBring ? '✅ ' : ''}${s.name}</td>
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

  container.innerHTML = teams.map(team => `
    <div class="team-card">
      <h4>${team.name}</h4>
      ${team.members.map(m => `
        <div class="member-row">
          <span class="member-name">${m.pokemon}</span>
          <span class="member-detail">
            ${m.nature ? m.nature + ' | ' : ''}
            ${m.ability || ''} |
            🎒 ${m.held_item || '?'} |
            ${(m.moves || []).join(', ')}
          </span>
        </div>`).join('')}
    </div>`).join('');
}

init();
