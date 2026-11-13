/**
 * ============================================================================
 * TERRAFORGE AGRO | MASTER CROP DATABASE & EXTENSION REGISTRY
 * File: crop.js
 * ============================================================================
 * 
 * HOW TO ADD NEW CROPS:
 * ----------------------------------------------------------------------------
 * 1. STATIC ADDITION (Codebase):
 *    Simply add a new crop object to the `CROPS_DATABASE` array below.
 *    Any crop added to this array is automatically populated across:
 *      • Step 03: Standing Crop Selection & Search Chips
 *      • Step 04: Multi-Season Crop Rotation Grid & Calibration Cards
 *      • Step 06: Agronomic Yield Simulation & Pareto Synthesis Engine
 *      • Backend User Data Payload Generation (input.js / userData.js)
 * 
 * 2. RUNTIME ADDITION (Programmatic API / Backend Sync):
 *    window.CropDB.addCrop({
 *      id: 'coffee',
 *      name: 'Highland Arabica Coffee',
 *      category: 'Perennial',
 *      emoji: '☕',
 *      baseYieldHa: 1.8,
 *      baseRevenueHa: 5200,
 *      waterReq: 0.65,
 *      soilBenefit: 0.85,
 *      growingDurationDays: 240,
 *      suitableSeasons: ['perennial', 'maha']
 *    });
 * ============================================================================
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.CropDB = factory();
    // Expose global aliases for convenience
    root.TerraforgeCrops = root.CropDB;
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /**
   * Primary Crop Catalog (Pre-calibrated for Sri Lanka Agro-Climatic Zones)
   * To add a crop later, simply insert a new object in this list!
   */
  const CROPS_DATABASE = [
    {
      id: 'rice',
      name: 'Paddy Rice (Maha / Yala)',
      category: 'Cereals',
      emoji: '🌾',
      baseYieldHa: 5.2,
      baseRevenueHa: 2200,
      waterReq: 0.85,
      soilBenefit: 0.65,
      erosionMitigation: 0.60,
      growingDurationDays: 120,
      suitableSeasons: ['maha', 'yala'],
      description: 'Staple wetland cereal cultivated across Sri Lanka dry and intermediate zone river basins.'
    },
    {
      id: 'tea',
      name: 'Ceylon Estate Tea',
      category: 'Perennial',
      emoji: '🍃',
      baseYieldHa: 2.4,
      baseRevenueHa: 4800,
      waterReq: 0.60,
      soilBenefit: 0.85,
      erosionMitigation: 0.90,
      growingDurationDays: 365,
      suitableSeasons: ['perennial'],
      description: 'High-elevation montane perennial camellia sinensis for premium export processing.'
    },
    {
      id: 'coconut',
      name: 'Coconut Plantation',
      category: 'Oilseeds',
      emoji: '🥥',
      baseYieldHa: 6.8,
      baseRevenueHa: 3400,
      waterReq: 0.50,
      soilBenefit: 0.80,
      erosionMitigation: 0.75,
      growingDurationDays: 365,
      suitableSeasons: ['perennial'],
      description: 'Coconut triangle commercial monoculture and agroforestry canopy cover.'
    },
    {
      id: 'corn',
      name: 'Industrial Maize',
      category: 'Cereals',
      emoji: '🌽',
      baseYieldHa: 7.5,
      baseRevenueHa: 2600,
      waterReq: 0.65,
      soilBenefit: 0.55,
      erosionMitigation: 0.50,
      growingDurationDays: 110,
      suitableSeasons: ['maha', 'yala'],
      description: 'Commercial feed maize cultivated extensively in Anuradhapura, Monaragala, and Vavuniya.'
    },
    {
      id: 'sugarcane',
      name: 'Commercial Sugarcane',
      category: 'Industrial',
      emoji: '🎋',
      baseYieldHa: 62.0,
      baseRevenueHa: 3800,
      waterReq: 0.80,
      soilBenefit: 0.50,
      erosionMitigation: 0.70,
      growingDurationDays: 330,
      suitableSeasons: ['maha', 'perennial'],
      description: 'High-biomass sucrose cane for regional distilleries and sugar processing.'
    },
    {
      id: 'rubber',
      name: 'Natural Latex Rubber',
      category: 'Industrial',
      emoji: '🌳',
      baseYieldHa: 1.8,
      baseRevenueHa: 3100,
      waterReq: 0.55,
      soilBenefit: 0.75,
      erosionMitigation: 0.85,
      growingDurationDays: 365,
      suitableSeasons: ['perennial'],
      description: 'Hevea brasiliensis latex tapping in wet and intermediate lowlands.'
    },
    {
      id: 'cinnamon',
      name: 'Ceylon Pure Cinnamon',
      category: 'Spices',
      emoji: '🪵',
      baseYieldHa: 1.2,
      baseRevenueHa: 5600,
      waterReq: 0.45,
      soilBenefit: 0.80,
      erosionMitigation: 0.80,
      growingDurationDays: 365,
      suitableSeasons: ['perennial'],
      description: 'True Ceylon Cinnamon (Cinnamomum verum) quill harvesting for luxury export markets.'
    },
    {
      id: 'cassava',
      name: 'Industrial Cassava',
      category: 'Tubers',
      emoji: '🥔',
      baseYieldHa: 28.0,
      baseRevenueHa: 2400,
      waterReq: 0.40,
      soilBenefit: 0.60,
      erosionMitigation: 0.65,
      growingDurationDays: 210,
      suitableSeasons: ['maha', 'yala'],
      description: 'Drought-tolerant starchy root crop with high processing starch yield.'
    },
    {
      id: 'soybeans',
      name: 'High-Protein Soybeans',
      category: 'Legumes',
      emoji: '🫘',
      baseYieldHa: 3.2,
      baseRevenueHa: 2500,
      waterReq: 0.50,
      soilBenefit: 0.90,
      erosionMitigation: 0.75,
      growingDurationDays: 95,
      suitableSeasons: ['yala'],
      description: 'Nitrogen-fixing rotation legume, perfect as a soil restorative companion crop.'
    },
    {
      id: 'forage',
      name: 'Hybrid Napier Forage',
      category: 'Forage',
      emoji: '🌿',
      baseYieldHa: 45.0,
      baseRevenueHa: 2100,
      waterReq: 0.60,
      soilBenefit: 0.70,
      erosionMitigation: 0.90,
      growingDurationDays: 70,
      suitableSeasons: ['maha', 'yala', 'perennial'],
      description: 'High-density ruminant biomass for commercial dairy and livestock feed rotation.'
    },
    {
      id: 'black_pepper',
      name: 'Ceylon Black Pepper',
      category: 'Spices',
      emoji: '🌶️',
      baseYieldHa: 1.6,
      baseRevenueHa: 4900,
      waterReq: 0.50,
      soilBenefit: 0.80,
      erosionMitigation: 0.85,
      growingDurationDays: 365,
      suitableSeasons: ['perennial'],
      description: 'High-piperine spice vine intercropped with gliricidia and coconut timber.'
    },
    {
      id: 'coffee',
      name: 'Highland Arabica Coffee',
      category: 'Perennial',
      emoji: '☕',
      baseYieldHa: 1.5,
      baseRevenueHa: 5200,
      waterReq: 0.60,
      soilBenefit: 0.85,
      erosionMitigation: 0.88,
      growingDurationDays: 365,
      suitableSeasons: ['perennial'],
      description: 'Shade-grown specialty coffee cultivated across Kotmale and central highlands.'
    }
  ];

  // Active runtime registry initialized with deep copy of database
  let registry = JSON.parse(JSON.stringify(CROPS_DATABASE));

  // Event subscribers array
  const subscribers = [];

  /**
   * Validates crop entity attributes
   * @param {Object} crop 
   * @returns {{ valid: boolean, errors: string[] }}
   */
  function validateCrop(crop) {
    const errors = [];
    if (!crop) {
      errors.push('Crop object is null or undefined');
      return { valid: false, errors };
    }
    if (!crop.id || typeof crop.id !== 'string' || !crop.id.trim()) {
      errors.push('Crop "id" is required (string)');
    }
    if (!crop.name || typeof crop.name !== 'string' || !crop.name.trim()) {
      errors.push('Crop "name" is required (string)');
    }
    if (typeof crop.baseYieldHa !== 'number' || crop.baseYieldHa < 0) {
      errors.push('"baseYieldHa" must be a positive number');
    }
    if (typeof crop.baseRevenueHa !== 'number' || crop.baseRevenueHa < 0) {
      errors.push('"baseRevenueHa" must be a positive number');
    }
    if (typeof crop.waterReq !== 'number' || crop.waterReq < 0 || crop.waterReq > 1) {
      errors.push('"waterReq" must be a number between 0.0 and 1.0');
    }
    if (typeof crop.soilBenefit !== 'number' || crop.soilBenefit < 0 || crop.soilBenefit > 1) {
      errors.push('"soilBenefit" must be a number between 0.0 and 1.0');
    }

    return { valid: errors.length === 0, errors };
  }

  /**
   * Broadcasts registry changes to all active subscribers
   */
  function notifySubscribers() {
    const cropsCopy = JSON.parse(JSON.stringify(registry));
    subscribers.forEach(cb => {
      try {
        cb(cropsCopy);
      } catch (err) {
        console.error('[CropDB] Subscriber callback error:', err);
      }
    });

    // Also dispatch a browser DOM event so loosely coupled scripts can listen
    if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
      try {
        const evt = new CustomEvent('cropdb:change', { detail: { crops: cropsCopy } });
        window.dispatchEvent(evt);
      } catch (e) {
        // Fallback for older browsers
      }
    }
  }

  // =========================================================================
  // Public CropDB API
  // =========================================================================
  const CropDB = {
    /**
     * Retrieve all currently registered crops
     * @returns {Array<Object>}
     */
    getAll() {
      return JSON.parse(JSON.stringify(registry));
    },

    /**
     * Retrieve a specific crop by unique ID
     * @param {string} id 
     * @returns {Object|null}
     */
    getById(id) {
      if (!id) return null;
      const found = registry.find(c => c.id === id);
      return found ? JSON.parse(JSON.stringify(found)) : null;
    },

    /**
     * Filter crops by agricultural category
     * @param {string} category 
     * @returns {Array<Object>}
     */
    getByCategory(category) {
      if (!category) return this.getAll();
      const cat = category.toLowerCase().trim();
      return registry
        .filter(c => (c.category || '').toLowerCase() === cat)
        .map(c => JSON.parse(JSON.stringify(c)));
    },

    /**
     * Filter crops by suitable monsoon season (e.g. 'maha', 'yala', 'perennial')
     * @param {string} season 
     * @returns {Array<Object>}
     */
    getBySeason(season) {
      if (!season) return this.getAll();
      const s = season.toLowerCase().trim();
      return registry
        .filter(c => Array.isArray(c.suitableSeasons) && c.suitableSeasons.includes(s))
        .map(c => JSON.parse(JSON.stringify(c)));
    },

    /**
     * Get unique categories across all registered crops
     * @returns {string[]}
     */
    getCategories() {
      const set = new Set(registry.map(c => c.category).filter(Boolean));
      return Array.from(set);
    },

    /**
     * Dynamically add a new crop to the registry
     * @param {Object} cropData 
     * @returns {{ success: boolean, crop?: Object, error?: string }}
     */
    addCrop(cropData) {
      const validation = validateCrop(cropData);
      if (!validation.valid) {
        console.warn('[CropDB] Cannot add crop - validation failed:', validation.errors);
        return { success: false, error: validation.errors.join('; ') };
      }

      // Check if ID already exists
      const existingIdx = registry.findIndex(c => c.id === cropData.id);
      const cleanCrop = {
        id: String(cropData.id).trim(),
        name: String(cropData.name).trim(),
        category: cropData.category || 'General Agriculture',
        emoji: cropData.emoji || '🌱',
        baseYieldHa: Number(cropData.baseYieldHa),
        baseRevenueHa: Number(cropData.baseRevenueHa),
        waterReq: Number(cropData.waterReq),
        soilBenefit: Number(cropData.soilBenefit),
        erosionMitigation: typeof cropData.erosionMitigation === 'number' ? cropData.erosionMitigation : 0.65,
        growingDurationDays: Number(cropData.growingDurationDays) || 120,
        suitableSeasons: Array.isArray(cropData.suitableSeasons) ? cropData.suitableSeasons : ['maha', 'yala'],
        description: cropData.description || 'Custom registered agronomic variety.'
      };

      if (existingIdx > -1) {
        // Update existing crop
        registry[existingIdx] = cleanCrop;
      } else {
        // Append new crop
        registry.push(cleanCrop);
      }

      notifySubscribers();
      return { success: true, crop: JSON.parse(JSON.stringify(cleanCrop)) };
    },

    /**
     * Remove a crop by ID
     * @param {string} id 
     * @returns {boolean}
     */
    removeCrop(id) {
      const idx = registry.findIndex(c => c.id === id);
      if (idx > -1) {
        registry.splice(idx, 1);
        notifySubscribers();
        return true;
      }
      return false;
    },

    /**
     * Reset registry back to the original default database
     */
    resetToDefault() {
      registry = JSON.parse(JSON.stringify(CROPS_DATABASE));
      notifySubscribers();
    },

    /**
     * Subscribe to crop catalog changes
     * @param {Function} callback Function receiving updated crops array
     * @returns {Function} Unsubscribe function
     */
    subscribe(callback) {
      if (typeof callback === 'function') {
        subscribers.push(callback);
        // Immediately trigger once with current state
        try {
          callback(this.getAll());
        } catch (e) {
          console.error('[CropDB] Error on initial subscription callback:', e);
        }
      }
      return () => {
        const idx = subscribers.indexOf(callback);
        if (idx > -1) subscribers.splice(idx, 1);
      };
    }
  };

  return CropDB;
}));
