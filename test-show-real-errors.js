const { chromium } = require('playwright');

async function testShowRealErrors() {
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 1000
  });
  const page = await browser.newPage();

  try {
    console.log('🚨 TESTING REAL ERROR VISIBILITY');
    console.log('===============================\n');
    
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await page.waitForTimeout(5000);
    
    console.log('✅ Application loaded');
    
    // Test the exact case the user mentioned
    console.log('\n🎲 TESTING: "generate 20 random numbers and show them"');
    console.log('===================================================');
    
    const textarea = page.locator('textarea').first();
    await textarea.fill('generate 20 random numbers and show them');
    console.log('✅ Entered the exact prompt that fails');
    
    const executeButton = page.locator('button[title*="Execute"]').first();
    await executeButton.click();
    console.log('⚡ Executing...');
    
    // Wait for execution
    await page.waitForTimeout(12000);
    
    const bodyText = await page.textContent('body');
    
    console.log('\n📊 ERROR ANALYSIS:');
    console.log('==================');
    
    const hasInternalError = bodyText.includes('Internal Server Error') || bodyText.includes('APIError');
    const hasStackTrace = bodyText.includes('Traceback') || bodyText.includes('File "/') || bodyText.includes('line ');
    const hasExecutionError = bodyText.includes('EXECUTION ERROR') || bodyText.includes('FULL STACK TRACE');
    const hasSpecificError = bodyText.includes('ModuleNotFoundError') || bodyText.includes('FileNotFoundError') || bodyText.includes('AttributeError');
    const hasRandomNumbers = bodyText.includes('random') || bodyText.includes('0.') || bodyText.includes('[');
    
    console.log(`   🚨 Has Internal Server Error: ${hasInternalError ? '❌ YES' : '✅ NO'}`);
    console.log(`   📜 Has Python Stack Trace: ${hasStackTrace ? '✅ YES - CAN DEBUG!' : '❌ NO - BLIND!'}`);
    console.log(`   🔍 Has Execution Error Details: ${hasExecutionError ? '✅ YES' : '❌ NO'}`);
    console.log(`   🐛 Has Specific Error Type: ${hasSpecificError ? '✅ YES' : '❌ NO'}`);
    console.log(`   🎲 Generated Random Numbers: ${hasRandomNumbers ? '✅ YES' : '❌ NO'}`);
    
    if (hasStackTrace || hasExecutionError) {
      console.log('\n📜 ERROR DETAILS FOUND:');
      console.log('======================');
      
      // Try to extract and show the actual error
      const errorMatch = bodyText.match(/(EXECUTION ERROR[\s\S]{0,800}|Traceback[\s\S]{0,800})/);
      if (errorMatch) {
        console.log('ACTUAL ERROR CONTENT:');
        console.log('---------------------');
        console.log(errorMatch[1]);
      }
    }
    
    // Final assessment
    const errorVisibilityGood = hasStackTrace || hasExecutionError;
    const actuallyWorks = hasRandomNumbers && !hasInternalError;
    
    console.log('\n🎯 FINAL ASSESSMENT:');
    console.log('===================');
    console.log(`   🔍 Error visibility: ${errorVisibilityGood ? '✅ EXCELLENT - CAN DEBUG!' : '❌ TERRIBLE - BLIND!'}`);
    console.log(`   🎲 Actually generates numbers: ${actuallyWorks ? '✅ SUCCESS' : '❌ FAILED'}`);
    
    if (errorVisibilityGood) {
      console.log('\n🎉 SUCCESS: We can now see what\'s actually failing!');
      console.log('🔧 Developers can debug the real issue!');
    } else {
      console.log('\n💥 FAILURE: Still no visibility into what\'s breaking!');
      console.log('🔧 Need to fix error capture and display system!');
    }
    
  } catch (error) {
    console.error('💥 Test failed:', error);
  }
  
  await page.screenshot({ 
    path: 'real-errors-test.png', 
    fullPage: true 
  });
  
  console.log('\n⏳ Keeping browser open to examine errors...');
  await page.waitForTimeout(20000);
  
  await browser.close();
}

testShowRealErrors();
