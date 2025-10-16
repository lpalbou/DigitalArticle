#!/usr/bin/env node
/**
 * Startup script for the Reverse Analytics Notebook frontend.
 * 
 * This script starts the Vite development server.
 */

const { spawn } = require('child_process')
const path = require('path')
const fs = require('fs')

const frontendDir = path.join(__dirname, 'frontend')

console.log('🚀 Starting Reverse Analytics Notebook Frontend...')
console.log(`📁 Working directory: ${frontendDir}`)

// Check if node_modules exists
const nodeModulesPath = path.join(frontendDir, 'node_modules')
if (!fs.existsSync(nodeModulesPath)) {
  console.log('📦 Installing dependencies...')
  
  const npmInstall = spawn('npm', ['install'], { 
    cwd: frontendDir,
    stdio: 'inherit',
    shell: true 
  })
  
  npmInstall.on('close', (code) => {
    if (code === 0) {
      startDevServer()
    } else {
      console.error('❌ Failed to install dependencies')
      process.exit(1)
    }
  })
} else {
  startDevServer()
}

function startDevServer() {
  console.log('🌐 Starting development server...')
  console.log('📱 Frontend will be available at: http://localhost:3000')
  console.log('\n' + '='.repeat(60))
  
  const devServer = spawn('npm', ['run', 'dev'], {
    cwd: frontendDir,
    stdio: 'inherit',
    shell: true
  })
  
  devServer.on('close', (code) => {
    if (code === 0) {
      console.log('\n🛑 Development server stopped')
    } else {
      console.error('\n❌ Development server exited with error')
      process.exit(code)
    }
  })
  
  // Handle CTRL+C gracefully
  process.on('SIGINT', () => {
    console.log('\n🛑 Stopping development server...')
    devServer.kill('SIGINT')
  })
}
