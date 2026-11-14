// Actual local UI verification. Requires playwright-core and axe-core outside the repository.
const { chromium } = require('playwright-core');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const sizes = {small:[320,740], mobile:[390,844], tablet:[768,1024], laptop:[1024,768], desktop:[1440,900]};
async function run() {
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});
 const output=path.resolve(process.env.QA_OUTPUT||'artifacts/ui-redesign');
 fs.mkdirSync(output,{recursive:true});
 const audits=[];
 try {
  for(const [name,[width,height]] of Object.entries(sizes)){
   const p=await browser.newPage({viewport:{width,height},acceptDownloads:true,reducedMotion:'reduce'});
   p.setDefaultTimeout(30000);
   const button=s=>p.getByRole('button',{name:s,exact:true});
   const heading=s=>p.getByRole('heading',{name:s,exact:true});
   const choose=async(label,value)=>{await p.getByRole('combobox',{name:label,exact:true}).click();if(['Country or territory','Last crop grown here'].includes(label))await p.keyboard.type(value);await p.getByRole('option',{name:value,exact:true}).click();};
   const verify=async(screen)=>{
    await p.waitForTimeout(300);
    assert.equal(await p.getByTestId('stException').count(),0,name+' '+screen+' exception');
    assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),name+' '+screen+' document overflow');
    const overflow=await p.locator('[data-testid="stMain"]').evaluate(e=>e.scrollWidth>e.clientWidth+1);
    assert(!overflow,name+' '+screen+' main overflow');
    await p.screenshot({path:path.join(output,name+'-'+screen+'.png'),fullPage:true});
    await p.addScriptTag({path:require.resolve('axe-core/axe.min.js')});
    const axe=await p.evaluate(()=>axe.run(document.querySelector('.st-key-app_shell'),{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}}));
    audits.push({viewport:name,screen,violations:axe.violations.map(v=>({id:v.id,impact:v.impact,description:v.description,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))})),incomplete:axe.incomplete.map(v=>v.id)});
    console.log(name,screen,'axe',axe.violations.map(v=>v.id).join(',')||'pass');
   };
   await p.goto(process.env.AGROSHIFT_URL||'http://127.0.0.1:8501',{waitUntil:'domcontentloaded'});
   await button('Analyze my farm').waitFor();
   await verify('home');
   let found=false;
   for(let i=0;i<30;i++){await p.keyboard.press('Tab');if(await button('Analyze my farm').evaluate(e=>e===document.activeElement)){found=true;break;}}
   assert(found,name+' primary action keyboard path');
   assert((await button('Analyze my farm').boundingBox()).height>=44);
   await p.keyboard.press('Enter');
   await heading('Where is your farm?').waitFor();
   await choose('Country or territory','Kenya');
   await p.getByRole('textbox',{name:'Town or village',exact:true}).waitFor();
   await choose('Find your field','Saved locations');
   await choose('Location','Nairobi');
   await verify('location');
   await button('Use this location').click();
   await heading('Tell us about your field').waitFor();
   const field=p.getByRole('textbox',{name:'Farm name (optional)',exact:true});
   await field.fill('North field');await field.press('Tab');
   await p.waitForTimeout(350);
   await button('Dashboard').click();
   await button('Continue farm setup').click();
   await p.waitForFunction(()=>document.querySelector('input[aria-label="Farm name (optional)"]')?.value==='North field');
   assert.equal(await field.inputValue(),'North field');
   await verify('field');
   await button('Continue').click();
   await heading('When do you plan to grow?').waitFor();
   await choose('Planting month','March');
   await choose('Last growing month','July');
   await choose('Last crop grown here','Wheat');
   await verify('season');
   await button('Find crop options').click();
   await heading('Explore your crop options').waitFor();
   const detail=button('View details');
   await detail.first().waitFor();
   assert((await detail.count())<=4);
   // Grid uses the real two-column layout above mobile width.
   const cards=await p.locator('.st-key-crop_grid > div').evaluateAll(es=>es.map(e=>({x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y})));
   assert(cards.length>=2);
   assert(width>760 ? Math.abs(cards[0].y-cards[1].y)<2 : cards[1].y>cards[0].y,name+' card columns');
   await verify('results');
   await p.locator('.as-card').first().scrollIntoViewIfNeeded();
   await p.screenshot({path:path.join(output,name+'-crop-cards.png')});
   await button('Compare').nth(0).click();
   await button('Compare selected (1)').waitFor();
   await button('Compare').nth(0).click();
   await button('Compare selected (2)').click();
   await heading('Compare crops').waitFor();
   await verify('compare');
   await button('View details').first().click();
   await p.getByText('Scientific evidence',{exact:true}).click();
   await verify('details');
   await button('Back to comparison').click();
   await button('View details').nth(1).waitFor();
   assert.equal(await button('View details').count(),2);
   await button('Dashboard').click();
   await button('Recommendations').click();
   await button('Compare selected (2)').waitFor();
   await verify('results-selected');
   const download=p.waitForEvent('download');
   await button('Download report').click();
   const item=await download;
   await item.saveAs(path.join(output,name+'-report.html'));
   const report=fs.readFileSync(path.join(output,name+'-report.html'),'utf8');
   assert(report.includes('NASA') && report.includes('Still unknown:'));
   if(name==='mobile'){
    await p.getByText('More download formats',{exact:true}).click();
    const event=p.waitForEvent('download');await button('Assessment data (JSON)').click();
    await (await event).saveAs(path.join(output,'mobile-report.json'));
    const data=JSON.parse(fs.readFileSync(path.join(output,'mobile-report.json'),'utf8'));
    assert.equal(data.farm.country,'KE');assert.equal(data.farm.ph,null);assert.equal(data.farm.irrigation_mm,null);
   }
   await button('Save this farm').click();
   await heading('My Farm').waitFor();
   await button('Save farm').click();
   await p.getByText('Farm and assessment saved.',{exact:true}).waitFor();
   await verify('my-farm');
   await p.getByText('Assessment history',{exact:true}).click();
   await button('Download saved report').waitFor();
   await button('Dashboard').click();
   await heading('North field').waitFor();
   await verify('dashboard');
   await button('Explore').click();
   await p.getByLabel('Find a crop',{exact:true}).fill('maize');
   await p.getByText('1 matching crops',{exact:false}).waitFor();
   await verify('catalogue');
   await choose('Explore topic','Climate history');
   await p.getByTestId('stPlotlyChart').waitFor();
   await verify('climate');
   await choose('Explore topic','Soil information');
   await verify('soil');
   await p.close();
  }
 }finally{fs.writeFileSync(path.join(output,'accessibility.json'),JSON.stringify(audits,null,2));await browser.close();}
 assert.equal(audits.flatMap(a=>a.violations).length,0,'accessibility violations; inspect accessibility.json');
}
run().catch(e=>{console.error(e);process.exitCode=1;});
