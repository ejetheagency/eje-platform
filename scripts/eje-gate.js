#!/usr/bin/env node
/**
 * EJE Upstream Quality Gate
 * ─────────────────────────────────────────────────────────────────
 * Runs BEFORE a new leads-eje.json is deployed. Enforces EJE's
 * premium quality standards at the pipeline level, not the UI level.
 *
 * Usage:
 *   node scripts/eje-gate.js public/leads-eje.json
 *
 * Exit codes:
 *   0 = batch passes (all leads send-ready or explicitly flagged)
 *   1 = batch fails (too many weak leads — fix upstream or reject)
 *
 * This script does NOT modify UnaBase data or shared pipeline logic.
 */

const fs = require('fs');
const path = require('path');

const WEAK_CLIENT_NAMES = new Set([
  'google','meta','facebook','tiktok','amazon','microsoft','apple','spotify',
  'hubspot','linkedin','twitter','instagram','youtube','salesforce'
]);

const ICP_EXCLUSIONS = /\b(sdr outsourc|appointment.?setting|cold.?call.?center|telemarketing|mass.?prospect|lead.?gen.?agency)\b/i;

const GENERIC_EMAIL = /^(info|contacto|hola|hello|team|contact|admin|comunicacion|ventas|sales|soporte|help)@/i;

// ═══ CLASSIFICATION ═══

function classifyContact(lead) {
  const name = lead.contactName;
  const email = lead.contactEmail || '';
  const generic = GENERIC_EMAIL.test(email);

  if (name && email && !generic) return { grade: 'A', label: `${name} (personal email)` };
  if (name && email && generic)  return { grade: 'B', label: `${name} (generic email)` };
  if (email)                      return { grade: 'C', label: 'No named decision-maker' };
  return { grade: 'D', label: 'No usable contact' };
}

function classifyProof(lead) {
  const nc = lead.notableClients || [];
  const hasCaseStudy = (lead.fitReasons || []).includes('case_studies');
  const weakCount = nc.filter(c => WEAK_CLIENT_NAMES.has(c.toLowerCase())).length;
  const strongCount = nc.length - weakCount;

  if (hasCaseStudy || strongCount >= 2) return { tier: 'A', label: 'Case study or 2+ verified clients' };
  if (strongCount >= 1)                  return { tier: 'B', label: `${strongCount} verified client(s)` };
  if (nc.length > 0 && weakCount === nc.length)
    return { tier: 'C', label: `Logo-only proof (${nc.join(', ')})` };
  return { tier: 'C', label: 'No verifiable proof' };
}

function classifyICP(lead) {
  const desc = ((lead.summary || '') + ' ' + (lead.companyBrief || '')).toLowerCase();
  if (ICP_EXCLUSIONS.test(desc)) return { flag: 'excluded', label: 'ICP exclusion (SDR/appointment/lead-gen)' };
  return { flag: 'ok', label: '' };
}

function classifyEmailTrust(lead, proofTier) {
  const body = (lead.pitchEmailES || lead.emailCercana || '').toLowerCase();
  if (proofTier === 'C') {
    const usesWeak = [...WEAK_CLIENT_NAMES].some(w => body.includes(w));
    if (usesWeak) return { trust: 'low', label: 'Email references unverified logos' };
  }
  return { trust: 'ok', label: '' };
}

function classifySmallCompany(lead) {
  if (lead.estimatedSize !== 'small') return { flag: 'ok' };
  const maturity = [];
  if ((lead.notableClients || []).length > 0) maturity.push('clients');
  if ((lead.fitReasons || []).includes('case_studies')) maturity.push('case_studies');
  if ((lead.fitSignals || 0) >= 4) maturity.push('strong_signals');
  if (lead.contactName) maturity.push('named_dm');
  if (maturity.length < 2) return { flag: 'weak', label: `Small company with only ${maturity.length} maturity signal(s)` };
  return { flag: 'ok' };
}

function classifyLead(lead) {
  const contact = classifyContact(lead);
  const proof = classifyProof(lead);
  const icp = classifyICP(lead);
  const email = classifyEmailTrust(lead, proof.tier);
  const small = classifySmallCompany(lead);

  const issues = [];
  if (contact.grade >= 'C') issues.push(`contact:${contact.grade} — ${contact.label}`);
  if (proof.tier === 'C') issues.push(`proof:C — ${proof.label}`);
  if (icp.flag === 'excluded') issues.push(`icp:excluded — ${icp.label}`);
  if (email.trust === 'low') issues.push(`email:low — ${email.label}`);
  if (small.flag === 'weak') issues.push(`small:weak — ${small.label}`);

  return {
    company: lead.companyName,
    contact, proof, icp, email, small,
    issues,
    sendReady: issues.length === 0,
  };
}

// ═══ MAIN ═══

const filePath = process.argv[2] || path.join(__dirname, '..', 'public', 'leads-eje.json');

if (!fs.existsSync(filePath)) {
  console.error(`File not found: ${filePath}`);
  process.exit(1);
}

const leads = JSON.parse(fs.readFileSync(filePath, 'utf8'));
console.log(`\n═══ EJE UPSTREAM QUALITY GATE ═══`);
console.log(`File: ${filePath}`);
console.log(`Leads: ${leads.length}\n`);

const results = leads.map(classifyLead);
const ready = results.filter(r => r.sendReady);
const flagged = results.filter(r => !r.sendReady);

// Print results
results.forEach(r => {
  const icon = r.sendReady ? '✓' : '✗';
  const color = r.sendReady ? '\x1b[32m' : '\x1b[33m';
  console.log(`${color}${icon}\x1b[0m ${r.company.padEnd(28)} C:${r.contact.grade} P:${r.proof.tier} ${r.sendReady ? 'SEND-READY' : 'BLOCKED'}`);
  if (r.issues.length) r.issues.forEach(issue => console.log(`    ↳ ${issue}`));
});

const yield_pct = Math.round(100 * ready.length / leads.length);
console.log(`\n═══ YIELD: ${ready.length}/${leads.length} (${yield_pct}%) ═══`);

// Gate decision
const MIN_YIELD = 60; // At least 60% must be send-ready
if (yield_pct < MIN_YIELD) {
  console.log(`\x1b[31m✗ BATCH FAILED — yield ${yield_pct}% < minimum ${MIN_YIELD}%\x1b[0m`);
  console.log(`  Fix ${flagged.length} lead(s) upstream or expand pool.`);
  console.log(`\nBlocked leads:`);
  flagged.forEach(r => console.log(`  • ${r.company}: ${r.issues.map(i => i.split(' — ')[0]).join(', ')}`));
  process.exit(1);
} else {
  console.log(`\x1b[32m✓ BATCH PASSED — ${yield_pct}% send-ready\x1b[0m`);
  if (flagged.length) {
    console.log(`  ⚠ ${flagged.length} lead(s) flagged for operator review:`);
    flagged.forEach(r => console.log(`    • ${r.company}: ${r.issues.map(i => i.split(' — ')[0]).join(', ')}`));
  }
  process.exit(0);
}
