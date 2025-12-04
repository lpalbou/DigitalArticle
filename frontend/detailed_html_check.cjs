const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  console.log('Navigating to notebook...');
  await page.goto('http://localhost:3000/notebook/5e883fa9-be53-4498-8e86-ec600291bd26', {
    waitUntil: 'networkidle',
    timeout: 30000
  });

  // Wait for result panels to render
  await page.waitForSelector('.result-panel', { timeout: 10000 });

  console.log('\n=== CAPTURING FULL HTML OF RESULT PANELS ===\n');

  // Get all result panel HTML
  const resultPanels = await page.locator('.result-panel').all();

  for (let i = 0; i < resultPanels.length; i++) {
    console.log(`\n========== RESULT PANEL ${i + 1} ==========`);

    // Get full HTML with proper formatting
    const html = await resultPanels[i].evaluate(el => {
      // Get pretty-printed HTML
      const cloned = el.cloneNode(true);

      // Remove base64 data to make it readable
      const imgs = cloned.querySelectorAll('img[src^="data:image"]');
      imgs.forEach(img => {
        img.setAttribute('src', 'data:image/...[BASE64_TRUNCATED]');
      });

      // Return outer HTML
      return cloned.outerHTML;
    });

    // Pretty print
    let indent = 0;
    const lines = html.split('>').map(line => {
      const trimmed = line.trim();
      if (!trimmed) return '';

      // Closing tag
      if (trimmed.startsWith('</')) {
        indent = Math.max(0, indent - 2);
      }

      const indented = ' '.repeat(indent) + trimmed + '>';

      // Opening tag (not self-closing)
      if (!trimmed.startsWith('</') && !trimmed.endsWith('/>') && !trimmed.match(/<(img|input|br|hr)/)) {
        indent += 2;
      }

      return indented;
    });

    const formatted = lines.filter(l => l.trim()).join('\n');
    console.log(formatted);

    // Also save to file
    fs.writeFileSync(`/tmp/result_panel_${i + 1}.html`, formatted);
    console.log(`\n→ Saved to /tmp/result_panel_${i + 1}.html`);
  }

  console.log('\n\n=== ANALYZING STRUCTURE PROBLEMS ===\n');

  // Check for the specific dashboard figure
  const dashboardLabel = page.locator('text=Figure 1: TNBC Patient Dashboard');
  const dashboardExists = await dashboardLabel.count() > 0;

  if (dashboardExists) {
    console.log('✅ Found "Figure 1: TNBC Patient Dashboard" label');

    // Find its parent structure
    const labelElement = await dashboardLabel.first();
    const parentChain = await labelElement.evaluate(el => {
      const chain = [];
      let current = el;
      let depth = 0;

      while (current && depth < 10) {
        const classes = current.className || '';
        const tag = current.tagName?.toLowerCase() || 'unknown';
        chain.push(`${tag}.${classes.split(' ').join('.')}`);
        current = current.parentElement;
        depth++;

        // Stop at result-panel
        if (classes.includes('result-panel')) break;
      }

      return chain;
    });

    console.log('\nParent chain from label to result-panel:');
    parentChain.forEach((item, idx) => {
      console.log(`  ${' '.repeat(idx * 2)}↑ ${item}`);
    });

    // Check if the actual dashboard image/plot is in the same card
    const dashboardCard = page.locator('text=Figure 1: TNBC Patient Dashboard').locator('..').locator('..');
    const hasPlotlyInSameCard = await dashboardCard.locator('div[class*="plotly"]').count() > 0;
    const hasImageInSameCard = await dashboardCard.locator('img').count() > 0;

    console.log(`\n✅ Plotly plot in same card as label: ${hasPlotlyInSameCard ? 'YES' : 'NO'}`);
    console.log(`✅ Image in same card as label: ${hasImageInSameCard ? 'YES' : 'NO'}`);

    if (!hasPlotlyInSameCard && !hasImageInSameCard) {
      console.log('\n❌ PROBLEM FOUND: Label exists but no plot/image in same card!');
      console.log('   The figure must be rendering somewhere else');
    }
  } else {
    console.log('❌ "Figure 1: TNBC Patient Dashboard" label not found');
  }

  await browser.close();
  console.log('\n✅ Detailed HTML check complete');
})();
