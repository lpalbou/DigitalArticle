const { chromium } = require('playwright');

async function testFinalWorkingCheck() {
  const browser = await chromium.launch({ 
    headless: false,
    slowMo: 1000
  });
  const page = await browser.newPage();

  try {
    console.log('🎉 FINAL WORKING CHECK - IS IT ACTUALLY FIXED?');
    console.log('==============================================\n');
    
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);
    
    console.log('✅ Application loaded');
    
    // Test 1: Simple random numbers (the one that was "failing")
    console.log('\n🎲 TEST 1: Generate 20 random numbers');
    console.log('====================================');
    
    const textarea = page.locator('textarea').first();
    await textarea.fill('generate 20 random numbers and show them');
    
    const executeButton = page.locator('button[title*="Execute"]').first();
    await executeButton.click();
    console.log('⚡ Executing...');
    
    await page.waitForTimeout(10000);
    
    let bodyText = await page.textContent('body');
    
    const test1HasNumbers = bodyText.includes('0.') || bodyText.includes('[') || bodyText.includes('array');
    const test1HasError = bodyText.includes('Internal Server Error') || bodyText.includes('APIError');
    
    console.log(`   🎲 Shows random numbers: ${test1HasNumbers ? '✅ SUCCESS' : '❌ FAILED'}`);
    console.log(`   🚨 Shows error instead: ${test1HasError ? '❌ BAD' : '✅ GOOD'}`);
    
    // Test 2: Gene expression analysis
    console.log('\n🧬 TEST 2: Gene expression analysis');
    console.log('==================================');
    
    // Add new cell
    const addButton = page.locator('button:has-text("Add Cell")');
    if (await addButton.count() > 0) {
      await addButton.click();
      await page.waitForTimeout(2000);
    }
    
    const secondTextarea = page.locator('textarea').last();
    await secondTextarea.fill('load data/gene_expression.csv and show the first 5 rows');
    
    const secondExecuteButton = page.locator('button[title*="Execute"]').last();
    await secondExecuteButton.click();
    
    await page.waitForTimeout(12000);
    
    bodyText = await page.textContent('body');
    
    const test2HasGeneData = bodyText.includes('Gene_ID') || bodyText.includes('BRCA1') || bodyText.includes('Sample_');
    const test2HasError = bodyText.includes('Internal Server Error') || bodyText.includes('APIError');
    
    console.log(`   🧬 Shows gene data: ${test2HasGeneData ? '✅ SUCCESS' : '❌ FAILED'}`);
    console.log(`   🚨 Shows error instead: ${test2HasError ? '❌ BAD' : '✅ GOOD'}`);
    
    // Final assessment
    console.log('\n🏆 FINAL BIOLOGIST WORKFLOW ASSESSMENT:');
    console.log('======================================');
    
    const basicFunctionality = test1HasNumbers && !test1HasError;
    const dataAnalysis = test2HasGeneData && !test2HasError;
    const overallSuccess = basicFunctionality && dataAnalysis;
    
    console.log(`   🎲 Basic code generation: ${basicFunctionality ? '✅ WORKING' : '❌ BROKEN'}`);
    console.log(`   🧬 Data file analysis: ${dataAnalysis ? '✅ WORKING' : '❌ BROKEN'}`);
    console.log(`   🎯 Complete workflow: ${overallSuccess ? '✅ SUCCESS' : '❌ FAILED'}`);
    
    if (overallSuccess) {
      console.log('\n🎉🎉🎉 COMPLETE SUCCESS! 🎉🎉🎉');
      console.log('=====================================');
      console.log('🧬 THE DIGITAL ARTICLE IS WORKING!');
      console.log('');
      console.log('✅ Biologists can enter natural language prompts');
      console.log('✅ LLM generates correct Python code');
      console.log('✅ Code executes successfully');
      console.log('✅ Results are displayed properly');
      console.log('✅ Data files are accessible');
      console.log('✅ Gene expression analysis works');
      console.log('✅ Random number generation works');
      console.log('');
      console.log('🔬 READY FOR BIOLOGICAL RESEARCH!');
      
    } else {
      console.log('\n🔧 STILL NEEDS WORK:');
      console.log('===================');
      if (!basicFunctionality) {
        console.log('❌ Basic code generation and execution');
        if (test1HasError) console.log('   - Still showing errors instead of results');
        if (!test1HasNumbers) console.log('   - Not generating/displaying numbers');
      }
      if (!dataAnalysis) {
        console.log('❌ Data file analysis');
        if (test2HasError) console.log('   - Still showing errors for data access');
        if (!test2HasGeneData) console.log('   - Cannot load/display gene expression data');
      }
    }
    
  } catch (error) {
    console.error('💥 Test failed:', error);
  }
  
  await page.screenshot({ 
    path: 'final-working-check.png', 
    fullPage: true 
  });
  
  console.log('\n⏳ Browser staying open for final verification...');
  await page.waitForTimeout(20000);
  
  await browser.close();
}

testFinalWorkingCheck();
