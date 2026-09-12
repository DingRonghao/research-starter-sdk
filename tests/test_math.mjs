// Exercise the actual Markdown/KaTeX parser independently of the browser sanitizer.
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
let source=await readFile(new URL('../web/static/markdown.js',import.meta.url),'utf8');
source=source.replace(/'\/vendor\/marked\/marked\.esm\.js[^']*'/,JSON.stringify(new URL('../node_modules/marked/lib/marked.esm.js',import.meta.url).href))
 .replace(/'\/vendor\/katex\/katex\.mjs[^']*'/,JSON.stringify(new URL('../node_modules/katex/dist/katex.mjs',import.meta.url).href))
 .replace(/import DOMPurify from '\/vendor\/dompurify\/purify\.es\.mjs[^']*';/,'');
const {markdownHTML}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
for(const input of [String.raw`能量 $E=mc^2$。`,String.raw`\(\frac{a}{b}\)`,String.raw`$$\int_0^1 x^2 dx$$`,String.raw`\[\sum_{i=1}^n i\]`]){
 assert.match(markdownHTML(input),/class="katex/);
 assert.doesNotMatch(markdownHTML(input),/katex-error/);
}
assert.doesNotMatch(markdownHTML('```tex\n$E=mc^2$\n```'),/class="katex/);
assert.doesNotMatch(markdownHTML('`$E=mc^2$`'),/class="katex/);
assert.doesNotMatch(markdownHTML(String.raw`\$20`),/class="katex/);
assert.match(markdownHTML(String.raw`$\notARealCommand$`),/notARealCommand/);
console.log('8 Markdown math parser checks passed');
