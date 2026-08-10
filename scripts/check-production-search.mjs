#!/usr/bin/env node
// Upstream: portfolio-search-indexing-audit contract v2.
// Release-triggered HTTP validation. Exit 2 means infrastructure is unavailable.
'use strict';

import fs from 'node:fs';
import path from 'node:path';

const CONFIG_ARG = process.argv.find(value => value.startsWith('--config='));
const BASE_ARG = process.argv.find(value => value.startsWith('--base='));
const JSON_OUTPUT = process.argv.includes('--json');
const ROOT = process.cwd();
let defects = 0;
let infrastructure = 0;

function report(kind, message) {
    if (kind === 'defect') defects++;
    else infrastructure++;
    console.error(`${kind === 'defect' ? 'LIVE' : 'NETWORK'}  ${message}`);
}

function loadConfig() {
    const configPath = path.resolve(ROOT, CONFIG_ARG ? CONFIG_ARG.slice(9) : 'search-audit.config.json');
    try {
        const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        if (config.contractVersion !== 2) throw new Error('contractVersion must be 2');
        const canonical = new URL(config.canonicalOrigin);
        if (canonical.protocol !== 'https:' || canonical.pathname !== '/' || canonical.hostname.startsWith('www.')) {
            throw new Error('canonicalOrigin must be a bare HTTPS origin with trailing slash');
        }
        return { ...config, canonicalOrigin: canonical.href };
    } catch (error) {
        report('infrastructure', `configuration failed: ${error.message}`);
        return null;
    }
}

const config = loadConfig();
if (!config) process.exit(2);
const canonicalOrigin = new URL(config.canonicalOrigin);
const base = new URL(BASE_ARG ? BASE_ARG.slice(7) : canonicalOrigin.href);
if (!base.pathname.endsWith('/')) base.pathname += '/';
const production = base.href === canonicalOrigin.href;

async function request(url) {
    let lastError;
    for (let attempt = 1; attempt <= 3; attempt++) {
        try {
            return await fetch(url, {
                redirect: 'follow',
                headers: { 'user-agent': 'portfolio-search-contract/2' },
                signal: AbortSignal.timeout(15000)
            });
        } catch (error) {
            lastError = error;
            if (attempt < 3) await new Promise(resolve => setTimeout(resolve, attempt * 150));
        }
    }
    report('infrastructure', `${url}: fetch failed after 3 attempts: ${lastError?.cause?.message || lastError?.message || 'unknown error'}`);
    return null;
}

function deployedUrl(canonical) {
    return production ? canonical : new URL(new URL(canonical).pathname.replace(/^\//, ''), base).href;
}

function false404(body, url) {
    for (const pattern of config.hosted404Patterns || []) {
        if (body.toLowerCase().includes(String(pattern).toLowerCase())) {
            report('defect', `${url}: response contains hosted 404 marker ${JSON.stringify(pattern)}`);
            return true;
        }
    }
    return false;
}

async function fetchText(url, rule = {}) {
    const response = await request(url);
    if (!response) return null;
    const body = await response.text();
    if (!response.ok) report('defect', `${url}: HTTP ${response.status}`);
    const type = response.headers.get('content-type') || '';
    if (rule.contentTypes?.length && !rule.contentTypes.some(expected => type.toLowerCase().includes(expected.toLowerCase()))) {
        report('defect', `${url}: unexpected content-type ${type || '(missing)'}`);
    }
    for (const required of rule.contains || []) {
        if (!body.includes(required)) report('defect', `${url}: missing required text ${JSON.stringify(required)}`);
    }
    false404(body, url);
    return { response, body, type };
}

const sitemapBodies = new Map();

async function fetchSitemap(canonical, seen = new Set()) {
    if (seen.has(canonical)) return;
    seen.add(canonical);
    const target = deployedUrl(canonical);
    const result = await fetchText(target, { contentTypes: ['xml'] });
    if (!result) return;
    sitemapBodies.set(canonical, result.body);
    if (/<sitemapindex\b/i.test(result.body)) {
        for (const match of result.body.matchAll(/<sitemap>[\s\S]*?<loc>([^<]+)<\/loc>[\s\S]*?<\/sitemap>/gi)) {
            let child;
            try { child = new URL(match[1].replace(/&amp;/g, '&')); }
            catch { report('defect', `${canonical}: invalid child sitemap URL ${match[1]}`); continue; }
            if (child.origin !== canonicalOrigin.origin) {
                report('defect', `${canonical}: child sitemap uses noncanonical origin ${child.href}`);
                continue;
            }
            await fetchSitemap(child.href, seen);
        }
    }
}

for (const rule of config.requiredFiles || []) {
    await fetchText(new URL(rule.path.replace(/^\//, ''), base).href, rule);
}

for (const sitemap of config.sitemaps || []) {
    await fetchSitemap(new URL(sitemap.replace(/^\//, ''), canonicalOrigin).href);
}

const canonicals = [];
for (const [sitemap, body] of sitemapBodies) {
    for (const match of body.matchAll(/<url>[\s\S]*?<loc>([^<]+)<\/loc>[\s\S]*?<\/url>/gi)) {
        const canonical = match[1].replace(/&amp;/g, '&');
        let url;
        try { url = new URL(canonical); }
        catch { report('defect', `${sitemap}: invalid page location ${canonical}`); continue; }
        if (url.origin !== canonicalOrigin.origin || url.href !== canonical) {
            report('defect', `${sitemap}: noncanonical page location ${canonical}`);
        }
        canonicals.push(canonical);
    }
}
if (!canonicals.length) report('infrastructure', 'live sitemaps contain no page locations');

function jsonLd(html, url) {
    const blocks = [...html.matchAll(/<script\b[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi)];
    if (!blocks.length && config.requireJsonLd !== false) report('defect', `${url}: missing JSON-LD`);
    for (const block of blocks) {
        try { JSON.parse(block[1]); }
        catch (error) { report('defect', `${url}: invalid JSON-LD: ${error.message}`); }
    }
}

async function checkPage(canonical) {
    const target = deployedUrl(canonical);
    const result = await fetchText(target, { contentTypes: ['text/html'] });
    if (!result) return;
    if (result.response.url !== target) report('defect', `${target}: final URL is ${result.response.url}`);
    const html = result.body;
    const pageCanonical = html.match(/<link\b[^>]*rel=["']canonical["'][^>]*href=["']([^"']+)["']/i)?.[1]
        || html.match(/<link\b[^>]*href=["']([^"']+)["'][^>]*rel=["']canonical["']/i)?.[1];
    if (pageCanonical !== canonical) report('defect', `${target}: canonical ${pageCanonical || '(missing)'} does not equal ${canonical}`);
    if (/<meta\b[^>]*name=["']robots["'][^>]*content=["'][^"']*noindex/i.test(html)) {
        report('defect', `${target}: sitemap page is noindex`);
    }
    jsonLd(html, target);
}

async function mapLimit(items, limit, fn) {
    let index = 0;
    await Promise.all(Array.from({ length: Math.min(limit, items.length) }, async () => {
        while (index < items.length) await fn(items[index++]);
    }));
}

await mapLimit([...new Set(canonicals)], 8, checkPage);

if (production) {
    for (const redirect of config.redirects || []) {
        const response = await request(redirect.from);
        if (response && response.url !== redirect.to) {
            report('defect', `${redirect.from}: final URL is ${response.url}, expected ${redirect.to}`);
        }
    }
}

const summary = {
    contractVersion: 2,
    base: base.href,
    pages: new Set(canonicals).size,
    defects,
    infrastructure
};
if (JSON_OUTPUT) console.log(JSON.stringify(summary));
else console.log(`check-production-search: ${summary.pages} sitemap pages at ${base.href}, ${defects} defects, ${infrastructure} infrastructure failures`);
process.exit(infrastructure ? 2 : defects ? 1 : 0);
