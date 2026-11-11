'use strict';
// OmniRouteLite CLI — gestion sécurisée des clés providers (zéro dépendance, Node >= 18)
//
//   node cli.js providers --list
//   node cli.js providers --connect mistral [--key-file chemin]
//   node cli.js providers --verify mistral
//
// Règles de sécurité :
// - la clé n'est JAMAIS affichée, journalisée ni poussée sur GitHub (secrets/ est gitignoré) ;
// - la clé est stockée dans OmniRouteLite/secrets/<name>.key avec chmod 600 ;
// - --verify n'appelle que GET /v1/models (gratuit) : aucune inférence payante.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { readProviderKey, resolveProviderKey, storeProviderKey, isSafeProviderEndpoint } = require('./provider-keys');

const cfgPath = path.join(__dirname, process.env.OMNILITE_CONFIG || 'config.json');
const examplePath = path.join(__dirname, 'config.example.json');

function loadCfg() {
  if (fs.existsSync(cfgPath)) return JSON.parse(fs.readFileSync(cfgPath, 'utf8'));
  if (fs.existsSync(examplePath)) return JSON.parse(fs.readFileSync(examplePath, 'utf8'));
  return { providers: [] };
}
function saveCfg(cfg) { fs.writeFileSync(cfgPath, JSON.stringify(cfg, null, 2) + '\n'); }
function findProvider(cfg, name) {
  return (cfg.providers || []).find(p => String(p.name).toLowerCase() === String(name).toLowerCase()) || null;
}
function fingerprint(key) { return crypto.createHash('sha256').update(key).digest('hex').slice(0, 12); }
// Résolution centralisée avec refus du path traversal, des liens symboliques
// et des permissions trop larges sur le fichier de secret.
function resolveKey(p) {
  return resolveProviderKey(p, __dirname, process.env);
}
function keySource(p) {
  if (p.apiKeyEnv && process.env[p.apiKeyEnv] && process.env[p.apiKeyEnv].trim()) return 'env:' + p.apiKeyEnv;
  if (p.apiKeyFile) {
    try {
      return readProviderKey(__dirname, p.name) ? 'file:' + p.apiKeyFile : null;
    } catch {
      return null;
    }
  }
  if (p.apiKey) return 'inline (déconseillé — migrez via --connect)';
  return null;
}
function readImportedKeyFile(filePath) {
  const resolved = path.resolve(filePath);
  const info = fs.lstatSync(resolved);
  if (info.isSymbolicLink() || !info.isFile()) {
    throw new Error('imported key source must be a regular non-symlink file');
  }
  return fs.readFileSync(resolved, 'utf8').trim();
}
function readSecretStdin() {
  return new Promise((resolve, reject) => {
    const isTTY = Boolean(process.stdin.isTTY && typeof process.stdin.setRawMode === 'function');
    let buf = '';
    let finished = false;
    if (isTTY) {
      process.stdout.write('Collez la clé API (saisie masquée) puis Entrée : ');
      process.stdin.setRawMode(true);
    }
    process.stdin.setEncoding('utf8');
    const cleanup = () => {
      process.stdin.removeListener('data', onData);
      process.stdin.removeListener('end', onEnd);
      process.stdin.removeListener('error', onErr);
      if (isTTY) {
        process.stdin.setRawMode(false);
        process.stdout.write('\n');
      }
    };
    const done = value => {
      if (finished) return;
      finished = true;
      cleanup();
      resolve(value.trim());
    };
    const fail = error => {
      if (finished) return;
      finished = true;
      cleanup();
      reject(error);
    };
    const onData = chunk => {
      if (!isTTY) {
        buf += chunk;
        return;
      }
      for (const char of chunk) {
        if (char === '\r' || char === '\n') return done(buf);
        if (char === '\u0003') return fail(new Error('saisie annulée'));
        if (char === '\u007f' || char === '\b') buf = buf.slice(0, -1);
        else if (char >= ' ') buf += char;
      }
    };
    const onEnd = () => done(buf);
    const onErr = error => fail(error);
    process.stdin.on('data', onData);
    process.stdin.on('end', onEnd);
    process.stdin.on('error', onErr);
  });
}

async function cmdList() {
  const cfg = loadCfg();
  console.log('Providers (config: ' + (fs.existsSync(cfgPath) ? 'config.json' : 'config.example.json') + ') :');
  for (const p of cfg.providers || []) {
    const src = keySource(p);
    const key = src ? resolveKey(p) : '';
    const state = src ? 'CONFIGURE [' + src + (key ? ' sha256:' + fingerprint(key) : '') + ']' : 'PREPARE (aucune clé)';
    console.log('  - ' + p.name + ' (' + (p.type || 'openai') + ') ' + (p.baseUrl || '') + ' — ' + state + (p.enabled === false ? ' [désactivé]' : ''));
  }
  console.log('Astuce : node cli.js providers --connect <nom> puis --verify <nom>.');
}
async function cmdConnect(name, keyFileArg) {
  const cfg = loadCfg();
  const p = findProvider(cfg, name);
  if (!p) { console.error('Provider "' + name + '" introuvable. Connus : ' + (cfg.providers || []).map(x => x.name).join(', ')); process.exit(1); }
  let key = '';
  let src = '';
  if (keyFileArg) { key = readImportedKeyFile(keyFileArg); src = 'fichier fourni ' + keyFileArg; }
  else if (p.apiKeyEnv && process.env[p.apiKeyEnv]) { key = process.env[p.apiKeyEnv].trim(); src = 'variable d environnement ' + p.apiKeyEnv; }
  else if (process.env.MISTRAL_API_KEY_FILE) { key = readImportedKeyFile(process.env.MISTRAL_API_KEY_FILE); src = 'MISTRAL_API_KEY_FILE'; }
  else { key = await readSecretStdin(); src = 'saisie stdin'; }
  if (!key || /\s/.test(key)) { console.error('Clé invalide (vide ou contenant des espaces). Aucune écriture effectuée.'); process.exit(1); }
  let keyFile;
  try {
    keyFile = storeProviderKey(__dirname, p.name, key);
  } catch (error) {
    console.error('Stockage refusé : ' + String(error.message || error));
    process.exit(1);
  }
  const rel = 'secrets/' + p.name + '.key';
  delete p.apiKey;
  p.apiKeyFile = rel;
  if (!p.apiKeyEnv && p.name === 'mistral') p.apiKeyEnv = 'MISTRAL_API_KEY';
  saveCfg(cfg);
  const st = fs.statSync(keyFile);
  console.log('OK CONFIGURE — clé ' + p.name + ' enregistrée localement (' + src + ').');
  console.log('   Fichier : ' + keyFile + ' — permissions ' + (st.mode & 0o777).toString(8) + ' (600 attendu).');
  console.log('   Empreinte sha256:' + fingerprint(key) + ' (la clé elle-même n est jamais affichée).');
  console.log('   config.json pointe maintenant sur ' + rel + ' — aucun secret dans le dépôt (secrets/ est gitignoré).');
  console.log('Prochaine étape (gratuite) : node cli.js providers --verify ' + p.name);
}
async function cmdVerify(name) {
  const cfg = loadCfg();
  const p = findProvider(cfg, name);
  if (!p) { console.error('Provider "' + name + '" introuvable.'); process.exit(1); }
  const base = String(p.baseUrl || '').replace(/\/$/, '');
  if (!base || !isSafeProviderEndpoint(base)) {
    console.error('Endpoint refusé : une URL HTTPS valide sans identifiants, query string ou fragment est obligatoire.');
    process.exit(1);
  }
  const key = resolveKey(p);
  const src = keySource(p);
  if (!key) { console.log('PREPARE (aucune clé sûre enregistrée pour ' + name + ') — lancez --connect ' + name + ' d abord.'); process.exit(1); }
  const url = base + '/v1/models';
  console.log('Vérification (gratuite, aucune inférence) : GET ' + url + ' — clé via ' + src + ', sha256:' + fingerprint(key));
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 30_000);
  try {
    const headers = { authorization: 'Bearer ' + key };
    if (p.type === 'anthropic') { headers['x-api-key'] = key; headers['anthropic-version'] = '2023-06-01'; delete headers.authorization; }
    const r = await fetch(url, { headers, signal: ctrl.signal });
    if (r.status === 200) {
      const data = await r.json();
      const models = (data.data || []).map(m => m.id).sort();
      console.log('OK CONNECTE — authentification OK (' + models.length + ' modèles disponibles) :');
      for (const m of models) console.log('   - ' + m);
      console.log('Statut : CONNECTE. TESTE le sera après une première complétion réelle (payante, autorisation explicite uniquement).');
    } else if (r.status === 401 || r.status === 403) {
      console.log('Clé refusée (HTTP ' + r.status + ') — invalide, révoquée ou sans accès. Régénérez-la puis relancez --connect.');
      process.exit(2);
    } else {
      console.log('HTTP ' + r.status + ' — ni succès ni refus de clé (maintenance, quota…). La clé n est ni validée ni invalidée.');
      process.exit(3);
    }
  } catch (e) {
    console.log('Erreur réseau : ' + String(e.message || e) + ' — vérifiez la connexion. Aucune conclusion sur la clé.');
    process.exit(3);
  } finally { clearTimeout(t); }
}
(async () => {
  const [, , cmd, sub, ...rest] = process.argv;
  const keyFileIdx = rest.indexOf('--key-file');
  const keyFileArg = keyFileIdx >= 0 ? rest[keyFileIdx + 1] : null;
  if (cmd === 'providers') {
    if (sub === '--list') return cmdList();
    if (sub === '--connect' && rest[0]) return cmdConnect(rest[0], keyFileArg);
    if (sub === '--verify' && rest[0]) return cmdVerify(rest[0]);
  }
  console.log('Usage : node cli.js providers --list | --connect <nom> [--key-file f] | --verify <nom>');
  process.exit(1);
})().catch(e => { console.error('ERREUR ' + String(e.message || e)); process.exit(1); });
