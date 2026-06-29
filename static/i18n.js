"use strict";

// ── i18n layer ──────────────────────────────────────────────────────────────
// Canonical data (Pokémon/move/item/ability/type names, localStorage keys, API
// payloads) is ALWAYS English. This module only translates what gets *displayed*.
//
//   t(key[, params])  → UI string for the active language
//   tName/tType/tMove/tItem/tAbility/tNature(en) → translated data label
//
// Data-label translations are loaded on demand from /api/i18n/<lang>; UI strings
// are baked in below. When LANG === 'en' every helper is an identity passthrough.

const LANG_KEY = "pokeLang";
let LANG = "en";
try { LANG = localStorage.getItem(LANG_KEY) || "en"; } catch { LANG = "en"; }

// Loaded data dictionaries per language: { fr: { pokemon:{}, types:{}, ... } }
const DATA_T = {};

const UI = {
  en: {
    "app.title": "Pokémon Champions Advisor",
    "app.heading": "⚔️ Pokémon Champions Advisor",

    "tab.tier-list": "Tier List",
    "tab.team-builder": "Team Builder",
    "tab.matchup": "Matchup Advisor",
    "tab.meta-teams": "Meta Teams",
    "tab.my-box": "My Box",
    "lang.toggle": "FR",
    "lang.label": "Language",

    "tier.title": "Singles Tier List",
    "tier.filter.ph": "Filter the tier list…",
    "tier.clear.aria": "Clear filter",
    "common.loading": "Loading…",
    "tier.count": "{n} Pokémon",
    "tier.nomatch": "No Pokémon match that filter.",

    "tb.title": "Team Builder",
    "tb.subtitle": "Pull in the Pokémon from My Box (or add more below), then generate the best team of 6. Megas are picked automatically when they're the strongest form of a Pokémon you own.",
    "tb.search.ph": "Search Pokémon…",
    "tb.loadbox": "Load My Box",
    "tb.clear": "Clear",
    "tb.build": "Build Best Team",
    "tb.building": "Building…",
    "tb.result.title": "Recommended Team",
    "tb.box.empty": "Your box is empty. Add Pokémon in the My Box tab first.",

    "tb.suggest.title": "Suggested Additions",
    "tb.suggest.attack": "Attack types missing",
    "tb.suggest.fullcover": "✅ Full offensive type coverage",
    "tb.suggest.stacked": "Stacked weakness",
    "tb.suggest.addtype": "Add a Pokémon of type",
    "tb.suggest.hint": "Click a suggestion to add it to your pool.",

    "tb.analysis.title": "Team Analysis  (score: {score})",
    "tb.analysis.covers": "✅ Covers:",
    "tb.analysis.nocover": "⚠️ No coverage vs:",
    "tb.analysis.shared": "Shared weaknesses:",
    "tb.moves.edit": "✎ Edit moveset",
    "tb.moves.done": "✓ Done",
    "tb.moves.hint": "Pick up to 4. Outlined moves are the source-recommended best.",

    "mu.title": "Matchup Advisor",
    "mu.subtitle": "Enter your team and the opponent's team to find out which 3 to bring and who to lead.",
    "mu.myteam": "My Team",
    "mu.my.ph": "Add my Pokémon…",
    "mu.oppteam": "Opponent's Team",
    "mu.opp.ph": "Add opponent's Pokémon…",
    "mu.analyse": "Analyse Matchup",
    "mu.analysing": "Analysing…",
    "mu.bring": "Bring These 3",
    "mu.lead": "Lead With",
    "mu.scores": "Full Scores",
    "mu.needteam": "Add at least one Pokémon to your team.",
    "mu.lead.reason": "Best matchup vs {name} (opponent's strongest)",
    "mu.col.pokemon": "Pokémon",
    "mu.col.tier": "Tier",
    "mu.col.score": "Score",
    "mu.col.vs": "vs {name}",

    "meta.title": "Meta Team Compositions",
    "meta.none": "No teams available.",
    "meta.guide": "guide ↗",

    "box.title": "My Box",
    "box.subtitle": "Track the Pokémon you've recruited. Mark Permanent keeps, or Trial rentals with the days left on the 7-day clock — and promote a trial to permanent before it expires.",
    "box.search.ph": "Add a Pokémon to your box…",
    "box.filter.all": "All",
    "box.filter.permanent": "Permanent",
    "box.filter.trial": "Trial",
    "box.empty": "Your box is empty. Search above to add Pokémon.",
    "box.count": "{n} in box · {perm} permanent · {trial} trial",
    "box.daysleft": "Days left",
    "box.expired": "⚠ expired",
    "box.clock": "{n} {dayWord} on the 7-day clock",
    "box.day": "day",
    "box.days": "days",
    "box.makeperm": "Make Permanent",
    "box.kind.permanent": "Permanent",
    "box.kind.trial": "Trial",
    "box.remove": "Remove",

    "modal.close": "Close",
    "modal.notfound": "Could not load {name}.",
    "modal.stats": "Base Stats",
    "modal.matchups": "Type Matchups",
    "modal.weak": "Weak to",
    "modal.resists": "Resists",
    "modal.immune": "Immune",
    "modal.moves": "Best Moves",
    "modal.teammates": "Best Teammates",
    "modal.counters": "Countered By",
    "modal.builds": "Recommended Builds",
    "modal.build": "Build {n}",
    "modal.game8": "Game8 build ↗",
    "modal.data": "Data: {sources}",
  },
  fr: {
    "app.title": "Conseiller Pokémon Champions",
    "app.heading": "⚔️ Conseiller Pokémon Champions",

    "tab.tier-list": "Tier List",
    "tab.team-builder": "Constructeur",
    "tab.matchup": "Analyse de Match",
    "tab.meta-teams": "Équipes Méta",
    "tab.my-box": "Ma Boîte",
    "lang.toggle": "EN",
    "lang.label": "Langue",

    "tier.title": "Tier List Simple",
    "tier.filter.ph": "Filtrer la tier list…",
    "tier.clear.aria": "Effacer le filtre",
    "common.loading": "Chargement…",
    "tier.count": "{n} Pokémon",
    "tier.nomatch": "Aucun Pokémon ne correspond à ce filtre.",

    "tb.title": "Constructeur d'Équipe",
    "tb.subtitle": "Importez les Pokémon de Ma Boîte (ou ajoutez-en ci-dessous), puis générez la meilleure équipe de 6. Les Méga sont choisis automatiquement quand ils sont la meilleure forme d'un Pokémon que vous possédez.",
    "tb.search.ph": "Rechercher un Pokémon…",
    "tb.loadbox": "Charger Ma Boîte",
    "tb.clear": "Vider",
    "tb.build": "Construire l'Équipe",
    "tb.building": "Construction…",
    "tb.result.title": "Équipe Recommandée",
    "tb.box.empty": "Votre boîte est vide. Ajoutez d'abord des Pokémon dans l'onglet Ma Boîte.",

    "tb.suggest.title": "Ajouts Suggérés",
    "tb.suggest.attack": "Types d'attaque manquants",
    "tb.suggest.fullcover": "✅ Couverture offensive complète",
    "tb.suggest.stacked": "Faiblesse cumulée",
    "tb.suggest.addtype": "Ajoutez un Pokémon de type",
    "tb.suggest.hint": "Cliquez sur une suggestion pour l'ajouter à votre sélection.",

    "tb.analysis.title": "Analyse de l'Équipe  (score : {score})",
    "tb.analysis.covers": "✅ Couvre :",
    "tb.analysis.nocover": "⚠️ Aucune couverture contre :",
    "tb.analysis.shared": "Faiblesses communes :",
    "tb.moves.edit": "✎ Modifier les attaques",
    "tb.moves.done": "✓ Terminé",
    "tb.moves.hint": "Choisissez jusqu'à 4. Les attaques encadrées sont les meilleures (sources).",

    "mu.title": "Analyse de Match",
    "mu.subtitle": "Entrez votre équipe et celle de l'adversaire pour savoir lesquels emmener (3) et qui envoyer en premier.",
    "mu.myteam": "Mon Équipe",
    "mu.my.ph": "Ajouter mon Pokémon…",
    "mu.oppteam": "Équipe Adverse",
    "mu.opp.ph": "Ajouter le Pokémon adverse…",
    "mu.analyse": "Analyser le Match",
    "mu.analysing": "Analyse…",
    "mu.bring": "Emmenez ces 3",
    "mu.lead": "Envoyez en Premier",
    "mu.scores": "Scores Complets",
    "mu.needteam": "Ajoutez au moins un Pokémon à votre équipe.",
    "mu.lead.reason": "Meilleur match contre {name} (le plus fort de l'adversaire)",
    "mu.col.pokemon": "Pokémon",
    "mu.col.tier": "Tier",
    "mu.col.score": "Score",
    "mu.col.vs": "vs {name}",

    "meta.title": "Compositions d'Équipes Méta",
    "meta.none": "Aucune équipe disponible.",
    "meta.guide": "guide ↗",

    "box.title": "Ma Boîte",
    "box.subtitle": "Suivez les Pokémon que vous avez recrutés. Marquez Permanent pour les gardés, ou À l'essai pour les locations avec les jours restants sur le compteur de 7 jours — et promouvez un essai en permanent avant qu'il n'expire.",
    "box.search.ph": "Ajouter un Pokémon à votre boîte…",
    "box.filter.all": "Tous",
    "box.filter.permanent": "Permanents",
    "box.filter.trial": "À l'essai",
    "box.empty": "Votre boîte est vide. Recherchez ci-dessus pour ajouter des Pokémon.",
    "box.count": "{n} dans la boîte · {perm} permanents · {trial} à l'essai",
    "box.daysleft": "Jours restants",
    "box.expired": "⚠ expiré",
    "box.clock": "{n} {dayWord} sur le compteur de 7 jours",
    "box.day": "jour",
    "box.days": "jours",
    "box.makeperm": "Rendre Permanent",
    "box.kind.permanent": "Permanent",
    "box.kind.trial": "À l'essai",
    "box.remove": "Retirer",

    "modal.close": "Fermer",
    "modal.notfound": "Impossible de charger {name}.",
    "modal.stats": "Statistiques de Base",
    "modal.matchups": "Affinités de Type",
    "modal.weak": "Faible contre",
    "modal.resists": "Résiste à",
    "modal.immune": "Immunisé",
    "modal.moves": "Meilleures Attaques",
    "modal.teammates": "Meilleurs Coéquipiers",
    "modal.counters": "Contré Par",
    "modal.builds": "Builds Recommandés",
    "modal.build": "Build {n}",
    "modal.game8": "Build Game8 ↗",
    "modal.data": "Données : {sources}",
  },
};

const STAT_LABELS = {
  en: { hp: "HP", atk: "ATK", def: "DEF", spa: "SPA", spd: "SPD", spe: "SPE" },
  fr: { hp: "PV", atk: "ATQ", def: "DÉF", spa: "ATS", spd: "DÉS", spe: "VIT" },
};

const CAT_ABBR_L = {
  en: { Physical: "PHY", Special: "SPE", Status: "STA" },
  fr: { Physical: "PHY", Special: "SPÉ", Status: "STA" },
};

const ROLE_LABELS = {
  en: { attacker: "Attacker", wall: "Wall", setup: "Setup", support: "Support" },
  fr: { attacker: "Attaquant", wall: "Mur", setup: "Renforçateur", support: "Soutien" },
};

// ── Lookups ─────────────────────────────────────────────────────────────────
function _interp(str, params) {
  if (!params) return str;
  return str.replace(/\{(\w+)\}/g, (m, k) => (k in params ? params[k] : m));
}

function t(key, params) {
  const table = UI[LANG] || UI.en;
  const str = table[key] != null ? table[key] : (UI.en[key] != null ? UI.en[key] : key);
  return _interp(str, params);
}

function _dataDict(cat) {
  if (LANG === "en") return null;
  const d = DATA_T[LANG];
  return d ? d[cat] : null;
}
function _tData(cat, en) {
  if (en == null) return en;
  const dict = _dataDict(cat);
  return (dict && dict[en]) || en;
}

const tName    = (en) => _tData("pokemon", en);
const tType    = (en) => _tData("types", en);
const tMove    = (en) => _tData("moves", en);
const tItem    = (en) => _tData("items", en);
const tAbility = (en) => _tData("abilities", en);
const tNature  = (en) => _tData("natures", en);

function statLabel(k) { return (STAT_LABELS[LANG] || STAT_LABELS.en)[k] || k.toUpperCase(); }
function catAbbr(cat) { return ((CAT_ABBR_L[LANG] || CAT_ABBR_L.en)[cat]) || ""; }
function roleLabel(r) { return (ROLE_LABELS[LANG] || ROLE_LABELS.en)[r] || r; }

// True if the query matches a Pokémon by EN name, FR name, or either type label.
function searchMatch(p, q) {
  if (!q) return true;
  if (p.name.toLowerCase().includes(q)) return true;
  if (tName(p.name).toLowerCase().includes(q)) return true;
  return (p.types || []).some(ty =>
    ty.toLowerCase().includes(q) || tType(ty).toLowerCase().includes(q));
}

// ── Apply language to the page ────────────────────────────────────────────────
async function ensureDataDict(lang) {
  if (lang === "en" || DATA_T[lang]) return;
  try {
    DATA_T[lang] = await fetch("/api/i18n/" + lang).then(r => r.json());
  } catch {
    DATA_T[lang] = { pokemon: {}, types: {}, moves: {}, items: {}, abilities: {}, natures: {} };
  }
}

// Swap all static DOM strings tagged with data-i18n / data-i18n-ph / data-i18n-aria.
function applyStaticStrings() {
  document.documentElement.lang = LANG;
  document.title = t("app.title");
  document.querySelectorAll("[data-i18n]").forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-ph]").forEach(el => {
    el.placeholder = t(el.dataset.i18nPh);
  });
  document.querySelectorAll("[data-i18n-aria]").forEach(el => {
    el.setAttribute("aria-label", t(el.dataset.i18nAria));
  });
  const toggle = document.querySelector("#lang-toggle");
  if (toggle) {
    toggle.textContent = t("lang.toggle");
    toggle.setAttribute("aria-label", t("lang.label"));
  }
}

async function setLang(lang) {
  LANG = lang;
  try { localStorage.setItem(LANG_KEY, lang); } catch { /* ignore */ }
  await ensureDataDict(lang);
  applyStaticStrings();
  if (typeof rerenderAll === "function") rerenderAll();
}

// Called once on load (app.js init awaits this before first render).
async function initLang() {
  await ensureDataDict(LANG);
  applyStaticStrings();
  const toggle = document.querySelector("#lang-toggle");
  if (toggle) {
    toggle.addEventListener("click", () => setLang(LANG === "en" ? "fr" : "en"));
  }
}
