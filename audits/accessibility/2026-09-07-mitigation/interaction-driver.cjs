const fs = require('node:fs');
const assert = require('node:assert/strict');
const puppeteer = require('/Users/snap/Git/skill-a11y-audit/a11y-audit/deps/node_modules/puppeteer');
(async () => {
 const [base,out,baseline] = process.argv.slice(2);
 const browser = await puppeteer.launch({headless:true});
 const results={browser:await browser.version(),keyboard:[],gradient:[],decoration:[]};
 try {
  const page=await browser.newPage();
  const targets=[['quickstart.html','pre:nth-child(19)'],['agent-file-ownership.html','pre:nth-child(24)'],['ringer.html','pre:nth-child(14)'],['threat-model.html','.table-wrap']];
  for(const width of [1280,375]) for(const [route,target] of targets){
   await page.setViewport({width,height:800});await page.goto(base+'/'+route,{waitUntil:'networkidle0'});
   let tabs=0,reached=false;
   while(tabs<180){await page.keyboard.press('Tab');tabs++;reached=await page.evaluate(sel=>document.activeElement.matches(sel),target);if(reached)break;}
   assert(reached,`${route} ${width}: Tab did not reach target`);
   const before=await page.$eval(target,el=>({scroll:el.scrollLeft,overflow:el.scrollWidth-el.clientWidth,outline:getComputedStyle(el).outlineStyle,outlineWidth:getComputedStyle(el).outlineWidth,text:el.textContent,tabindex:el.tabIndex}));
   assert(before.overflow>0,`${route} ${width}: fixture must overflow`);assert(before.outline==='solid' && parseFloat(before.outlineWidth)>=2);
   await page.keyboard.down('ArrowRight');await new Promise(r=>setTimeout(r,400));await page.keyboard.up('ArrowRight');await new Promise(r=>setTimeout(r,150));
   const after=await page.$eval(target,el=>({scroll:el.scrollLeft,text:el.textContent}));assert(after.scroll>before.scroll,`${route} ${width}: ArrowRight did not scroll`);assert.equal(after.text,before.text);
   await page.keyboard.press('Tab');const tabExited=await page.evaluate(sel=>!document.activeElement.matches(sel),target);assert(tabExited);
   await page.keyboard.down('Shift');await page.keyboard.press('Tab');await page.keyboard.up('Shift');assert(await page.evaluate(sel=>document.activeElement.matches(sel),target));
   await page.keyboard.down('Shift');await page.keyboard.press('Tab');await page.keyboard.up('Shift');const reverseExited=await page.evaluate(sel=>!document.activeElement.matches(sel),target);assert(reverseExited);
   results.keyboard.push({route,width,target,tabs,overflow:before.overflow,scrollBefore:before.scroll,scrollAfter:after.scroll,visibleFocus:true,tabExited,reverseExited,textPreserved:true});
  }
  await page.setViewport({width:1280,height:800});await page.goto(base+'/',{waitUntil:'networkidle0'});
  const scan=JSON.parse(fs.readFileSync(baseline));
  for(const node of scan.results[0].axe.incomplete.find(v=>v.id==='color-contrast').nodes){
   const key=node.any[0].data.messageKey;const selector=node.target[0];
   if(key==='bgGradient'){
    const observed=await page.$eval(selector,el=>{const c=getComputedStyle(el);let ancestor=el;let bg=null;while(ancestor){const a=getComputedStyle(ancestor);if(a.backgroundImage!=='none')throw Error('Unexpected gradient');if(a.backgroundColor!=='rgba(0, 0, 0, 0)'){bg=a.backgroundColor;break;}ancestor=ancestor.parentElement;}return {text:el.textContent.trim(),color:c.color,background:bg,fontSize:c.fontSize,fontWeight:c.fontWeight};});
    const lum=color=>{const rgb=color.match(/[\d.]+/g).slice(0,3).map(Number).map(c=>{const x=c/255;return x<=0.04045?x/12.92:((x+0.055)/1.055)**2.4;});return .2126*rgb[0]+.7152*rgb[1]+.0722*rgb[2];};
    const a=lum(observed.color),b=lum(observed.background),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);const px=parseFloat(observed.fontSize);const min=px>=24 || (px>=18.6667 && Number(observed.fontWeight)>=700)?3:4.5;assert(ratio>=min,`${selector}: ${ratio} < ${min}`);results.gradient.push({selector,...observed,ratio,minimum:min});
   }else if(key==='nonBmp'){
    const observed=await page.$eval(selector,el=>({hidden:el.getAttribute('aria-hidden'),text:el.textContent,context:el.classList.contains('pl-arrow')?el.parentElement.textContent.trim():el.parentElement.textContent.trim()}));assert.equal(observed.hidden,'true');assert.equal(observed.text,'');assert(observed.context.length>0);results.decoration.push({selector,...observed});
   }
  }
  assert.equal(results.gradient.length,7);assert.equal(results.decoration.length,15);
  assert.equal(await page.$eval('.terminal .body > div:first-child .g',el=>el.textContent),'$');
  await page.screenshot({path:out+'/homepage-desktop.png',fullPage:true});
  await page.setViewport({width:375,height:800});await page.screenshot({path:out+'/homepage-narrow.png',fullPage:true});
  await page.goto(base+'/threat-model.html',{waitUntil:'networkidle0'});await page.focus('.table-wrap');await page.screenshot({path:out+'/table-focus-narrow.png'});
  fs.writeFileSync(out+'/interaction-checks.json',JSON.stringify(results,null,2)+'\n');console.log('PASS: eight keyboard cases, seven measured contrast targets, fifteen decorative equivalence checks');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
