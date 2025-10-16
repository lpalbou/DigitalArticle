const { chromium } = require('playwright');

async function testTrigger500AndLog() {
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 500
  });
  const page = await browser.newPage();

  try {
    console.log('🚨 TRIGGERING 500 ERROR TO CAPTURE BACKEND LOGS');
    console.log('===============================================\n');
    
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    
    console.log('✅ Application loaded');
    
    console.log('\n🎲 TRIGGERING THE 500 ERROR...');
    console.log('==============================');
    
    const textarea = page.locator('textarea').first();
    await textarea.fill('generate 20 random numbers and show them');
    
    const executeButton = page.locator('button[title*="Execute"]').first();
    await executeButton.click();
    console.log('⚡ Executing to trigger 500 error...');
    
    // Wait for execution and error
    await page.waitForTimeout(8000);
    
    console.log('\n✅ 500 error should be triggered');
    console.log('📋 Check backend.log for the actual stack trace');
    
  } catch (error) {
    console.error('💥 Test failed:', error);
  }
  
  await browser.close();
}

testTrigger500AndLog();
