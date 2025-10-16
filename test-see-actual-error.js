const { chromium } = require('playwright');

async function testSeeActualError() {
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 1000
  });
  const page = await browser.newPage();

  try {
    console.log('🔍 EXAMINING THE ACTUAL ERROR BEING SHOWN');
    console.log('=========================================\n');
    
    // Enable console logging from the page
    page.on('console', msg => {
      console.log(`🌐 BROWSER: ${msg.text()}`);
    });
    
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    
    console.log('✅ Application loaded');
    
    // Test the case that shows numbers but also shows error
    console.log('\n🎲 TESTING: "generate 20 random numbers and show them"');
    console.log('===================================================');
    
    const textarea = page.locator('textarea').first();
    await textarea.fill('generate 20 random numbers and show them');
    
    const executeButton = page.locator('button[title*="Execute"]').first();
    await executeButton.click();
    console.log('⚡ Executing and watching for errors...');
    
    // Wait for execution
    await page.waitForTimeout(12000);
    
    const bodyText = await page.textContent('body');
    
    console.log('\n📊 DETAILED ANALYSIS:');
    console.log('=====================');
    
    // Check what we can see
    const hasNumbers = bodyText.includes('0.') || bodyText.includes('[') || bodyText.includes('array');
    const hasErrorMessage = bodyText.includes('Internal Server Error') || bodyText.includes('APIError') || bodyText.includes('Failed to execute');
    const hasExecutionFailed = bodyText.includes('Execution Failed');
    const hasExecutionSuccessful = bodyText.includes('Execution Successful');
    const hasRedErrorBox = bodyText.includes('EXECUTION ERROR') || bodyText.includes('🚨');
    
    console.log(`   🎲 Shows random numbers: ${hasNumbers ? '✅ YES' : '❌ NO'}`);
    console.log(`   🚨 Shows error message: ${hasErrorMessage ? '❌ YES' : '✅ NO'}`);
    console.log(`   ❌ Shows "Execution Failed": ${hasExecutionFailed ? '❌ YES' : '✅ NO'}`);
    console.log(`   ✅ Shows "Execution Successful": ${hasExecutionSuccessful ? '✅ YES' : '❌ NO'}`);
    console.log(`   🔴 Shows red error box: ${hasRedErrorBox ? '❌ YES' : '✅ NO'}`);
    
    // Try to extract the actual error text being shown
    if (hasErrorMessage || hasExecutionFailed) {
      console.log('\n📜 ACTUAL ERROR TEXT BEING SHOWN:');
      console.log('=================================');
      
      // Look for specific error patterns
      const errorPatterns = [
        /APIError[:\s]([^\n]+)/,
        /Internal Server Error[:\s]([^\n]+)/,
        /Failed to execute[:\s]([^\n]+)/,
        /Execution Failed[:\s]([^\n]+)/,
        /Error[:\s]([^\n]+)/
      ];
      
      for (const pattern of errorPatterns) {
        const match = bodyText.match(pattern);
        if (match) {
          console.log(`FOUND ERROR: ${match[0]}`);
        }
      }
      
      // Also check for any text around "Error" or "Failed"
      const errorContext = bodyText.split(/Error|Failed/);
      if (errorContext.length > 1) {
        console.log('ERROR CONTEXT:');
        console.log(errorContext[1].substring(0, 200));
      }
    }
    
    // The key insight: if we have numbers AND errors, something is wrong with error handling
    if (hasNumbers && hasErrorMessage) {
      console.log('\n🚨 CRITICAL BUG IDENTIFIED:');
      console.log('===========================');
      console.log('❌ Code execution is SUCCESSFUL (generates numbers)');
      console.log('❌ But UI is showing ERRORS anyway');
      console.log('❌ This means the error handling logic is broken');
      console.log('❌ Success responses are being treated as errors');
      console.log('');
      console.log('🔧 FIX NEEDED: Check how frontend handles API responses');
      console.log('🔧 FIX NEEDED: Success responses might be in wrong format');
      console.log('🔧 FIX NEEDED: Error detection logic is too broad');
      
    } else if (hasNumbers && !hasErrorMessage) {
      console.log('\n🎉 WORKING CORRECTLY:');
      console.log('====================');
      console.log('✅ Shows results');
      console.log('✅ No error messages');
      
    } else if (!hasNumbers && hasErrorMessage) {
      console.log('\n🔧 GENUINE ERROR:');
      console.log('=================');
      console.log('❌ No results generated');
      console.log('❌ Error message shown');
      console.log('🔧 Need to debug the actual execution failure');
      
    } else {
      console.log('\n❓ UNCLEAR STATE:');
      console.log('================');
      console.log('❓ No results and no error messages');
      console.log('❓ Something else is wrong');
    }
    
  } catch (error) {
    console.error('💥 Test failed:', error);
  }
  
  await page.screenshot({ 
    path: 'see-actual-error.png', 
    fullPage: true 
  });
  
  console.log('\n⏳ Keeping browser open to examine the UI...');
  await page.waitForTimeout(20000);
  
  await browser.close();
}

testSeeActualError();
