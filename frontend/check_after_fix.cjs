const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('Navigating to notebook with cache refresh...');
  await page.goto('http://localhost:3000/notebook/5e883fa9-be53-4498-8e86-ec600291bd26', {
    waitUntil: 'networkidle',
    timeout: 30000
  });

  // Force a hard refresh
  console.log('Forcing page reload...');
  await page.reload({ waitUntil: 'networkidle' });

  await page.waitForTimeout(2000);

  console.log('\n=== CHECKING PANEL 2 (Dashboard) ===\n');

  const resultPanels = await page.locator('.result-panel').all();

  if (resultPanels.length >= 2) {
    const panel2 = resultPanels[1];

    // Count direct children
    const directChildren = await panel2.locator('> div').all();
    console.log(`Panel 2 direct children: ${directChildren.length}`);

    // Check for the problematic empty card
    const emptyCards = await panel2.locator('> div:has(.prose.max-w-none:empty)').all();
    console.log(`Empty prose cards: ${emptyCards.length}`);

    if (emptyCards.length > 0) {
      console.log('❌ PROBLEM: Empty card with label still exists');
    } else {
      console.log('✅ No empty cards found');
    }

    // Check for dashboard label
    const dashboardLabel = await panel2.locator('text=Figure 1: TNBC Patient Dashboard').count();
    console.log(`Dashboard label count: ${dashboardLabel}`);

    // Check for dashboard image
    const images = await panel2.locator('img').all();
    console.log(`Images in panel: ${images.length}`);

    // Structure check
    for (let i = 0; i < directChildren.length; i++) {
      const hasLabel = await directChildren[i].locator('.bg-blue-50').count() > 0;
      let labelText = '';
      if (hasLabel) {
        labelText = await directChildren[i].locator('.bg-blue-50 h4').textContent();
      }

      const hasImage = await directChildren[i].locator('img').count() > 0;
      const isEmpty = await directChildren[i].locator('.prose:empty, .prose.max-w-none:empty').count() > 0;

      console.log(`\nCard ${i + 1}:`);
      console.log(`  Label: ${hasLabel ? labelText : 'NO LABEL'}`);
      console.log(`  Has image: ${hasImage}`);
      console.log(`  Is empty: ${isEmpty}`);

      if (hasLabel && !hasImage && isEmpty) {
        console.log(`  ❌ BROKEN: Has label but no content`);
      } else if (hasImage) {
        console.log(`  ✅ Valid figure card`);
      }
    }
  }

  await browser.close();
  console.log('\n✅ Check complete');
})();
