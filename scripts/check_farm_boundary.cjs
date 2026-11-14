// Exercise actual Leaflet drawing, profile export and profile import in a local app.
const {chromium}=require('playwright-core');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_PATH,headless:true});
 const output=path.resolve(process.env.QA_OUTPUT||'artifacts/farm-platform-browser');
 fs.mkdirSync(output,{recursive:true});
 let p;
 try {
  p=await browser.newPage({viewport:{width:1366,height:1000},acceptDownloads:true});
  p.setDefaultTimeout(30000);
  await p.goto(process.env.AGROSHIFT_URL||'http://127.0.0.1:8501');
  const button=s=>p.getByRole('button',{name:s,exact:true});
  await button('Try an example farm').click();
  await p.getByRole('heading',{name:'Explore your crop options',exact:true}).waitFor();
  await button('My Farm').click();
  await p.getByRole('heading',{name:'My Farm',exact:true}).waitFor();
  await p.getByText('Field boundary (optional)',{exact:true}).click();
  await p.getByText('Draw or edit on a map',{exact:true}).click();
  const frame=p.frameLocator('iframe[title="streamlit_folium.st_folium"]');
  await frame.getByTitle('Draw a polygon',{exact:true}).click();
  const map=frame.locator('.leaflet-container');
  const box=await map.boundingBox();
  const x=box.width/2,y=box.height/2;
  for(const [dx,dy] of [[-60,-60],[60,-60],[60,60],[-60,60],[-60,-60]]){
   await map.click({position:{x:x+dx,y:y+dy}});
   await p.waitForTimeout(250);
  }
  await button('Use drawn boundary').click();
  await p.getByText('Boundary ready. Save farm to keep it.',{exact:true}).waitFor();
  const input=p.getByRole('textbox',{name:'Farm name',exact:true});
  await input.fill('Boundary test farm');
  await input.press('Tab');
  await button('Save farm').click();
  await p.getByText('Farm and assessment saved.',{exact:true}).waitFor();
  const download=p.waitForEvent('download');
  await button('Export farm').click();
  const file=await download;
  const filename=path.join(output,'boundary-farm.json');
  await file.saveAs(filename);
  const value=JSON.parse(fs.readFileSync(filename,'utf8'));
  assert(value.boundary.type==='Polygon' && value.boundary.coordinates[0].length===5);
  await p.getByText('Import a farm',{exact:true}).click();
  await p.getByText('AgroShift farm file',{exact:true}).waitFor();
  await p.locator('input[type="file"]').setInputFiles(filename);
  await p.getByText('boundary-farm.json',{exact:true}).waitFor();
  await button('Open imported farm').click();
  await p.getByRole('heading',{name:'Explore your crop options',exact:true}).waitFor();
  await button('My Farm').click();
  await p.getByText('Field boundary (optional)',{exact:true}).click();
  await p.getByText('A field boundary is attached.',{exact:true}).waitFor();
  assert.equal(await p.getByTestId('stException').count(),0);
  await p.screenshot({path:path.join(output,'boundary-import.png')});
  console.log('Boundary drawing, saved polygon export and farm import passed');
 } catch(e){if(p){console.log((await p.locator('body').innerText()).slice(-5000));await p.screenshot({path:path.join(output,'boundary-failure.png')});}throw e;} finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
