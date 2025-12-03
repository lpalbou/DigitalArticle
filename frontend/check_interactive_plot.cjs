const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('Navigating to notebook...');
  await page.goto('http://localhost:3000/notebook/5e883fa9-be53-4498-8e86-ec600291bd26', {
    waitUntil: 'networkidle',
    timeout: 30000
  });

  console.log('\n=== CHECKING INTERACTIVE PLOT LOCATION ===\n');

  // Find all result panels
  const resultPanels = await page.locator('.result-panel').all();

  for (let i = 0; i < resultPanels.length; i++) {
    // Check if this panel has plotly
    const plotlyElements = await resultPanels[i].locator('div[class*="plotly"]').all();

    if (plotlyElements.length > 0) {
      console.log(`Result Panel ${i + 1} contains ${plotlyElements.length} plotly plot(s)`);

      // Get the parent card structure
      const cards = await resultPanels[i].locator('> div.bg-white.rounded-lg').all();
      console.log(`  Direct card children: ${cards.length}`);

      // Check if plotly is inside a card that's a direct child
      for (let j = 0; j < cards.length; j++) {
        const hasPlotly = await cards[j].locator('div[class*="plotly"]').count() > 0;
        if (hasPlotly) {
          const hasLabel = await cards[j].locator('.bg-blue-50').count() > 0;
          let labelText = '';
          if (hasLabel) {
            labelText = await cards[j].locator('.bg-blue-50 h4').textContent();
          }
          console.log(`  ✅ Card ${j + 1} contains plotly plot`);
          console.log(`     Label: ${labelText || 'NO LABEL'}`);
          console.log(`     Structure: Single card → [label?] → content with plotly`);

          // Verify it's a direct child
          const parentClass = await cards[j].evaluate(el => el.parentElement?.className || 'none');
          if (parentClass.includes('result-panel')) {
            console.log(`     ✅ Card is direct child of result-panel`);
          } else {
            console.log(`     ❌ Card parent: ${parentClass}`);
          }
        }
      }
    }
  }

  console.log('\n=== CHECKING FOR SEPARATE "INTERACTIVE PLOTS" SECTION ===\n');

  // Check if there's a separate section titled "Interactive Plots"
  const interactivePlotsHeading = await page.getByText('Interactive Plots', { exact: false }).all();
  if (interactivePlotsHeading.length > 0) {
    console.log(`❌ PROBLEM: Found ${interactivePlotsHeading.length} "Interactive Plots" heading(s)`);
    console.log('   This suggests plots are in a separate section, not integrated');
  } else {
    console.log('✅ No separate "Interactive Plots" section found');
    console.log('   Plots are integrated directly in result panels');
  }

  await browser.close();
  console.log('\n✅ Interactive plot check complete');
})();
