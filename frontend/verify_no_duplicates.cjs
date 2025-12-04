const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('Navigating to notebook...');
  await page.goto('http://localhost:3000/notebook/5e883fa9-be53-4498-8e86-ec600291bd26', {
    waitUntil: 'networkidle',
    timeout: 30000
  });

  await page.waitForTimeout(2000);

  console.log('\n=== CHECKING FOR DUPLICATE PLOTS ===\n');

  // Find all occurrences of the UMAP label
  const umapLabels = await page.locator('text=3D UMAP of Feature Space').all();
  console.log(`"3D UMAP" label occurrences: ${umapLabels.length}`);

  if (umapLabels.length > 1) {
    console.log('❌ PROBLEM: Label appears multiple times (duplicate rendering)');
  } else if (umapLabels.length === 1) {
    console.log('✅ Label appears exactly once');
  }

  // Find all plotly divs
  const plotlyDivs = await page.locator('div[class*="plotly"]').all();
  console.log(`\nPlotly divs found: ${plotlyDivs.length}`);

  // Check each result panel
  const resultPanels = await page.locator('.result-panel').all();
  console.log(`\nTotal result panels: ${resultPanels.length}\n`);

  for (let i = 0; i < resultPanels.length; i++) {
    const panel = resultPanels[i];
    const plotlyInPanel = await panel.locator('div[class*="plotly"]').count();

    if (plotlyInPanel > 0) {
      console.log(`Panel ${i + 1}:`);
      console.log(`  Plotly plots: ${plotlyInPanel}`);

      // Check for UMAP label in this panel
      const hasUmapLabel = await panel.locator('text=3D UMAP').count() > 0;
      if (hasUmapLabel) {
        console.log(`  ✅ Has UMAP label`);
      }

      // Count cards in this panel
      const cards = await panel.locator('> div.bg-white.rounded-lg').count();
      console.log(`  Cards: ${cards}`);

      // Check if any cards have empty content with labels
      const emptyCards = await panel.locator('> div:has(.prose:empty), > div:has(div:empty)').count();
      if (emptyCards > 0) {
        console.log(`  ⚠️ Empty cards: ${emptyCards}`);
      }
    }
  }

  // Check for any HTML content containing plotly that's being rendered
  const plotlyHtmlDivs = await page.locator('div.prose:has-text("plotly")').all();
  if (plotlyHtmlDivs.length > 0) {
    console.log(`\n❌ PROBLEM: Found ${plotlyHtmlDivs.length} plotly HTML div(s) being rendered`);
  } else {
    console.log('\n✅ No plotly HTML divs being rendered (good - using React component instead)');
  }

  await browser.close();
  console.log('\n✅ Verification complete');
})();
