'use strict';

const fs = require('fs');
const path = require('path');

const PROVIDER_NAME = /^[a-z0-9][a-z0-9_-]{0,63}$/i;
const O_NOFOLLOW = fs.constants.O_NOFOLLOW || 0;

function validateProviderName(name) {
  if (typeof name !== 'string' || !PROVIDER_NAME.test(name)) {
    throw new Error('invalid provider name');
  }
  return name;
}

function secretsDirectory(rootDir, create = false) {
  const root = path.resolve(rootDir);
  const dir = path.join(root, 'secrets');
  if (create && !fs.existsSync(dir)) {
    try {
      fs.mkdirSync(dir, { mode: 0o700 });
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
    }
  }
  const info = fs.lstatSync(dir);
  if (info.isSymbolicLink() || !info.isDirectory()) {
    throw new Error('secrets directory must be a real directory');
  }
  if (process.platform !== 'win32') {
    fs.chmodSync(dir, 0o700);
    if ((fs.statSync(dir).mode & 0o777) !== 0o700) {
      throw new Error('secrets directory permissions must be 700');
    }
  }
  return dir;
}

function keyPath(rootDir, name, createDirectory = false) {
  validateProviderName(name);
  return path.join(secretsDirectory(rootDir, createDirectory), name + '.key');
}

function storeProviderKey(rootDir, name, key) {
  if (typeof key !== 'string' || !key || /\\s/.test(key)) {
    throw new Error('API key must be non-empty and contain no whitespace');
  }
  const target = keyPath(rootDir, name, true);
  const flags = fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_TRUNC | O_NOFOLLOW;
  let fd;
  try {
    fd = fs.openSync(target, flags, 0o600);
    const info = fs.fstatSync(fd);
    if (!info.isFile()) throw new Error('secret target must be a regular file');
    if (process.platform !== 'win32') fs.fchmodSync(fd, 0o600);
    fs.writeFileSync(fd, key + '\\n', { encoding: 'utf8' });
    fs.fsyncSync(fd);
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
  }
  if (process.platform !== 'win32' && (fs.statSync(target).mode & 0o777) !== 0o600) {
    throw new Error('secret file permissions must be 600');
  }
  return target;
}

function readProviderKey(rootDir, name) {
  const target = keyPath(rootDir, name, false);
  const info = fs.lstatSync(target);
  if (info.isSymbolicLink() || !info.isFile()) {
    throw new Error('secret file must be a regular non-symlink file');
  }
  if (process.platform !== 'win32' && (info.mode & 0o077) !== 0) {
    throw new Error('secret file permissions are too broad; use chmod 600');
  }
  const fd = fs.openSync(target, fs.constants.O_RDONLY | O_NOFOLLOW);
  try {
    const opened = fs.fstatSync(fd);
    if (!opened.isFile()) throw new Error('secret file must be a regular file');
    if (process.platform !== 'win32' && (opened.mode & 0o077) !== 0) {
      throw new Error('secret file permissions are too broad; use chmod 600');
    }
    return fs.readFileSync(fd, 'utf8').trim();
  } finally {
    fs.closeSync(fd);
  }
}

function resolveProviderKey(provider, rootDir, env = process.env) {
  if (!provider || typeof provider !== 'object') return '';
  if (typeof provider.apiKeyEnv === 'string' && provider.apiKeyEnv) {
    const value = env[provider.apiKeyEnv];
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  if (provider.apiKeyFile) {
    const expected = 'secrets/' + validateProviderName(provider.name) + '.key';
    if (provider.apiKeyFile !== expected) return '';
    try {
      return readProviderKey(rootDir, provider.name);
    } catch {
      // A configured secret file is authoritative: do not fall back to a
      // lower-priority inline value when the protected file is unsafe/unreadable.
      return '';
    }
  }
  return typeof provider.apiKey === 'string' ? provider.apiKey.trim() : '';
}

function isSafeProviderEndpoint(baseUrl) {
  try {
    const url = new URL(baseUrl);
    return url.protocol === 'https:'
      && Boolean(url.hostname)
      && !url.username
      && !url.password
      && !url.search
      && !url.hash;
  } catch {
    return false;
  }
}

module.exports = {
  isSafeProviderEndpoint,
  keyPath,
  readProviderKey,
  resolveProviderKey,
  storeProviderKey,
  validateProviderName,
};
