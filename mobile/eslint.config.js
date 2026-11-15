const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');

module.exports = defineConfig([
  { ignores: ['.qa/**', '.cache/**', '.expo/**', 'dist/**'] },
  expoConfig,
]);
