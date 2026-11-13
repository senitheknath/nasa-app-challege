/**
 * ============================================================================
 * TERRAFORGE AGRO | USER DATA FILE (BACKEND COMPATIBILITY MODULE)
 * File: userData.js
 * ============================================================================
 * 
 * Re-exports and links directly to TerraforgeUserData / TerraforgeInput
 * initialized in `input.js`.
 * 
 * You can import this file or `input.js` interchangeably in Node.js or browser.
 * ============================================================================
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define(['./input.js'], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = require('./input.js');
  } else {
    root.UserData = root.TerraforgeUserData || root.TerraforgeInput;
  }
}(typeof self !== 'undefined' ? self : this, function (inputModule) {
  return inputModule || (typeof window !== 'undefined' ? window.TerraforgeUserData : null);
}));
