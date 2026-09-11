async (page) => {
  const results=[];
  const check=(ok,name)=>{if(!ok)throw new Error(name);results.push(name);};
  await page.getByText('Schedule & preferences',{exact:true}).click();
  await page.getByRole('button',{name:'Resume Smart',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#pause').textContent==='Pause 1 hour');
  check(await page.locator('[name="mode"][value="smart"]').isChecked(),'native resume response');
  await page.getByRole('button',{name:'Pause 1 hour',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#status-title').textContent==='Taking a break');
  results.push('native pause response');
  await page.getByRole('button',{name:'Resume Smart',exact:true}).click();
  await page.locator('[name="mode"][value="manual"]').check({force:true});
  await page.waitForFunction(()=>document.querySelector('#status-meta').textContent.startsWith('Manual'));
  results.push('native manual mode');
  await page.getByText('Appearance & presets',{exact:true}).first().click();
  await page.getByText('Appearance & presets',{exact:true}).nth(1).click();
  for(const theme of ['dark','light']) {
    await page.locator(`[name="theme"][value="${theme}"]`).check({force:true});
    for(const style of ['liquid','frosted','ceramic','solid']) {
      await page.locator(`[name="material"][value="${style}"]`).check({force:true});
      check(await page.locator('body').getAttribute('data-material')===style,theme+' '+style);
      await page.locator('.desktop-shell').evaluate(e=>e.scrollTop=0);
      await page.screenshot({path:`C:/Users/Owner/Desktop/HassTech/Products/night-light-by-ht/audit/premium-qa/${theme}-${style}.png`});
    }
  }
  await page.getByText('Customize colors',{exact:true}).click();
  for(const field of ['accent','panel','background']) {
    await page.getByRole('button',{name:'Ocean '+field,exact:true}).click();
    check(await page.getByRole('button',{name:'Ocean '+field,exact:true}).getAttribute('aria-pressed')==='true',field+' preset filled and selected');
  }
  const stored=await page.evaluate(()=>localStorage.getItem('night-light-desktop-appearance-v1'));
  check(!!JSON.parse(stored).light.background,'appearance persisted');
  const overflow=await page.evaluate(()=>({doc:document.documentElement.scrollWidth<=innerWidth,shell:document.querySelector('.desktop-shell').scrollWidth<=innerWidth}));
  check(overflow.doc&&overflow.shell,'no horizontal overflow');
  await page.reload();
  await page.waitForFunction(()=>document.querySelector('#status-meta').textContent.startsWith('Manual'));
  check(await page.locator('.flyout').getAttribute('data-theme')==='light','theme survives renderer reload');
  await page.getByText('Quick guide & safety',{exact:true}).click();
  check(await page.getByRole('button',{name:'Quit Night Light',exact:true}).isVisible(),'quit is reachable');
  console.log(JSON.stringify({passed:results},null,2));
}
