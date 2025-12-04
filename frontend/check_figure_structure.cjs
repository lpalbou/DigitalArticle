const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('Navigating to notebook...');
  await page.goto('http://localhost:3000/notebook/5e883fa9-be53-4498-8e86-ec600291bd26', {
    waitUntil: 'networkidle',
    timeout: 30000
  });

  console.log('\n=== CHECKING RESULT PANEL STRUCTURE ===\n');

  // Find result-panel divs
  const resultPanels = await page.locator('.result-panel').all();
  console.log(`Found ${resultPanels.length} result-panel div(s)`);

  for (let i = 0; i < resultPanels.length; i++) {
    console.log(`\n--- Result Panel ${i + 1} ---`);

    // Get direct children
    const directChildren = await resultPanels[i].locator('> *').all();
    console.log(`Direct children count: ${directChildren.length}`);

    // Check for wrapper divs
    const spaceYWrappers = await resultPanels[i].locator('> div.space-y-4').all();
    const mb4SpaceYWrappers = await resultPanels[i].locator('> div.mb-4.space-y-4').all();

    console.log(`Wrapper divs with "space-y-4" class: ${spaceYWrappers.length}`);
    console.log(`Wrapper divs with "mb-4 space-y-4" classes: ${mb4SpaceYWrappers.length}`);

    // Check structure of first few children
    for (let j = 0; j < Math.min(3, directChildren.length); j++) {
      const classList = await directChildren[j].evaluate(el => el.className);
      const tagName = await directChildren[j].evaluate(el => el.tagName);
      console.log(`  Child ${j + 1}: <${tagName.toLowerCase()}> with classes: "${classList}"`);

      // Check if it's a figure card
      if (classList.includes('bg-white') && classList.includes('rounded-lg')) {
        const hasLabel = await directChildren[j].locator('.bg-blue-50').count() > 0;
        const hasImage = await directChildren[j].locator('img').count() > 0;
        const hasPlot = await directChildren[j].locator('div[class*="plotly"]').count() > 0;
        console.log(`    → Figure card: label=${hasLabel}, image=${hasImage}, plotly=${hasPlot}`);
      }
    }
  }

  console.log('\n=== CHECKING FOR PROBLEM PATTERNS ===\n');

  // Check for nested structure that shouldn't exist
  const nestedWrappers = await page.locator('.result-panel > div.space-y-4 > div').all();
  if (nestedWrappers.length > 0) {
    console.log(`❌ PROBLEM: Found ${nestedWrappers.length} divs nested under space-y-4 wrapper`);
  } else {
    console.log('✅ No nested space-y-4 wrappers found');
  }

  // Check if figures are direct children
  const directFigureCards = await page.locator('.result-panel > div.bg-white.rounded-lg').all();
  console.log(`Figure cards as direct children: ${directFigureCards.length}`);

  if (directFigureCards.length > 0) {
    console.log('✅ Figure cards are direct children of result-panel');
  } else {
    console.log('❌ PROBLEM: No figure cards found as direct children');
  }

  console.log('\n=== DOM SNAPSHOT ===\n');

  // Get HTML structure of first result panel
  if (resultPanels.length > 0) {
    const html = await resultPanels[0].evaluate(el => {
      // Simplified HTML showing structure
      let output = el.outerHTML;
      // Truncate long base64 strings
      output = output.replace(/data:image\/[^"]{200,}/g, 'data:image/...[truncated]');
      // Truncate long classes
      output = output.replace(/class="([^"]{100,})"/g, 'class="$1..."'.substring(0, 110) + '"');
      return output.substring(0, 2000);
    });
    console.log('First 2000 chars of result-panel HTML:');
    console.log(html);
  }

  await browser.close();
  console.log('\n✅ Playwright check complete');
})();
