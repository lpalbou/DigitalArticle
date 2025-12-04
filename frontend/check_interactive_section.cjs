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

  console.log('\n=== CHECKING INTERACTIVE PLOT LOCATION ===\n');

  // Find the interactive plot label
  const umapLabel = page.locator('text=3D UMAP of Feature Space');
  const umapExists = await umapLabel.count() > 0;

  if (umapExists) {
    console.log('✅ Found interactive plot label');

    // Get parent chain to see where it's rendered
    const parentChain = await umapLabel.first().evaluate(el => {
      const chain = [];
      let current = el;
      let depth = 0;

      while (current && depth < 15) {
        const classes = current.className || '';
        const tag = current.tagName?.toLowerCase() || 'unknown';
        const id = current.id || '';

        let info = tag;
        if (classes) info += `.${classes.split(' ').slice(0, 3).join('.')}`;
        if (id) info += `#${id}`;

        chain.push(info);
        current = current.parentElement;
        depth++;

        // Stop at body
        if (tag === 'body') break;
      }

      return chain;
    });

    console.log('\nParent chain from label to body:');
    parentChain.forEach((item, idx) => {
      console.log(`  ${'  '.repeat(idx)}↑ ${item}`);
    });

    // Check if it's inside a result-panel
    const isInResultPanel = await umapLabel.first().evaluate(el => {
      let current = el;
      while (current) {
        if (current.className && current.className.includes('result-panel')) {
          return true;
        }
        current = current.parentElement;
      }
      return false;
    });

    console.log(`\n${isInResultPanel ? '✅' : '❌'} Is inside result-panel: ${isInResultPanel}`);

    // Check if there's a separate section/container for interactive plots
    const separateSection = await page.locator('div:has-text("Interactive Plots")').count();
    if (separateSection > 0) {
      console.log('❌ Found separate "Interactive Plots" section');
    } else {
      console.log('✅ No separate "Interactive Plots" section heading');
    }

    // Find the plotly div
    const plotlyDivs = await page.locator('div[class*="plotly"]').all();
    console.log(`\nPlotly divs found: ${plotlyDivs.length}`);

    if (plotlyDivs.length > 0) {
      // Check if plotly is in same card as label
      const labelCard = umapLabel.locator('..').locator('..');
      const hasPlotlyInSameCard = await labelCard.locator('div[class*="plotly"]').count() > 0;
      console.log(`Plotly in same card as label: ${hasPlotlyInSameCard ? 'YES ✅' : 'NO ❌'}`);

      if (!hasPlotlyInSameCard) {
        console.log('\n❌ PROBLEM: Label and plotly are in different containers');
      }
    }
  } else {
    console.log('❌ Interactive plot label not found');
  }

  await browser.close();
  console.log('\n✅ Check complete');
})();
