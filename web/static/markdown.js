import {Marked} from '/vendor/marked/marked.esm.js?v=0.2.1.3';
import DOMPurify from '/vendor/dompurify/purify.es.mjs?v=0.2.1.3';
import katex from '/vendor/katex/katex.mjs?v=0.2.1.3';

const markdown = new Marked();
const renderMath = token => katex.renderToString(token.text, {
  displayMode:token.display, throwOnError:false, trust:false, strict:'ignore', maxExpand:500, maxSize:20,
});
markdown.use({extensions:[{
  name:'mathBlock', level:'block',
  start:source=>source.search(/\$\$|\\\[/),
  tokenizer(source){const m=/^(?:\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\])(?:\n|$)/.exec(source);if(m)return {type:'mathBlock',raw:m[0],text:m[1]??m[2],display:true};},
  renderer:renderMath,
},{
  name:'mathInline', level:'inline',
  start:source=>source.search(/\$|\\[([]/),
  tokenizer(source){const m=/^(?:\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\(([\s\S]+?)\\\)|\$([^\s$](?:[^$\n]*?[^\s$])?)\$(?!\d))/.exec(source);if(m)return {type:'mathInline',raw:m[0],text:m[1]??m[2]??m[3]??m[4],display:m[1]!==undefined||m[2]!==undefined};},
  renderer:renderMath,
}]});
export function markdownHTML(source){return markdown.parse(String(source||''));}
export function renderMarkdown(element, source){element.innerHTML=DOMPurify.sanitize(markdownHTML(source));}
