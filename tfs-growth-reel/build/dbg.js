const { chromium } = require('/opt/node-tools/node_modules/playwright');const path=require('path');
(async()=>{const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium',args:['--no-sandbox']});const p=await b.newPage({viewport:{width:1080,height:1920}});
await p.goto('file://'+path.join(__dirname,'reel2.html'));await p.evaluate(()=>document.fonts.ready);await p.evaluate(t=>render(t),10.4);
console.log(await p.evaluate(()=>{const od=document.querySelector('#cnt .od');const cs=getComputedStyle(od);const inn=od.firstChild;return {odH:cs.height,odOv:cs.overflow,odDisp:cs.display,odPos:cs.position,odW:cs.width,innH:getComputedStyle(inn).height,innTr:inn.style.transform,odoH:getComputedStyle(document.querySelector('#cnt')).height,html:document.querySelector('#cnt').outerHTML.slice(0,300),cnt:document.querySelectorAll('#cnt .od').length}}));
await b.close()})();
