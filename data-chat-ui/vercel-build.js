// vercel-build.js
const fs = require('fs');
const path = require('path');

// Ensure .eslintrc.json exists with relaxed rules for the build
const eslintConfig = {
  "extends": "next/core-web-vitals",
  "rules": {
    "@typescript-eslint/no-explicit-any": "off", 
    "@typescript-eslint/no-unused-vars": "warn",
    "react/no-unescaped-entities": "off"
  }
};

console.log('Running Vercel build preparation script...');

// Create .eslintrc.json if it doesn't exist
const eslintPath = path.join(__dirname, '.eslintrc.json');
if (!fs.existsSync(eslintPath)) {
  console.log('Creating .eslintrc.json with relaxed rules...');
  fs.writeFileSync(eslintPath, JSON.stringify(eslintConfig, null, 2));
}

// Ensure any other critical configuration is in place
console.log('Verifying TypeScript configuration...');
const tsconfigPath = path.join(__dirname, 'tsconfig.json');
if (fs.existsSync(tsconfigPath)) {
  const tsconfig = JSON.parse(fs.readFileSync(tsconfigPath, 'utf8'));
  
  // Ensure baseUrl and paths are configured
  let modified = false;
  if (!tsconfig.compilerOptions.baseUrl) {
    tsconfig.compilerOptions.baseUrl = '.';
    modified = true;
  }
  
  if (!tsconfig.compilerOptions.paths) {
    tsconfig.compilerOptions.paths = { '@/*': ['./src/*'] };
    modified = true;
  }
  
  if (modified) {
    console.log('Updating tsconfig.json with proper path aliases...');
    fs.writeFileSync(tsconfigPath, JSON.stringify(tsconfig, null, 2));
  }
}

console.log('Build preparation complete!'); 