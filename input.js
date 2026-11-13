/**
 * ============================================================================
 * TERRAFORGE AGRO | USER INPUT DATA & BACKEND INTEGRATION ENGINE
 * File: input.js (Aliased as userData.js)
 * ============================================================================
 * 
 * PURPOSE:
 * ----------------------------------------------------------------------------
 * This module is the authoritative client-side data store and payload builder
 * for connecting user-selected configurations with your separate backend API.
 * 
 * PAYLOAD SCHEMA SPECIFICATION:
 * ----------------------------------------------------------------------------
 * 1. OPTION 1: ACTIVE STANDING CROP ('current')
 *    -> Stores selected crop (resolved via CropDB), crop starting date,
 *       and Step 5 Constraints & Priorities.
 * 
 * 2. OPTION 2: CROP ROTATION CYCLE ('rotation')
 *    -> Stores each rotation season's start date, harvest date, and each
 *       season's planted crops (resolved via CropDB), plus Step 5 Constraints
 *       & Priorities.
 * 
 * 3. OPTION 3: NO CROP ROTATION / FALLOW SOIL ('none')
 *    -> Stores ONLY Step 5 Constraints & Priorities (+ demarcated parcel).
 *       All rotational and standing crop fields are omitted.
 * ============================================================================
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define(['./crop.js'], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory(require('./crop.js'));
  } else {
    const cropDb = root.CropDB || root.TerraforgeCrops;
    root.TerraforgeUserData = factory(cropDb);
    // Global aliases for maximum integration flexibility
    root.TerraforgeInput = root.TerraforgeUserData;
    root.UserDataStore = root.TerraforgeUserData;
  }
}(typeof self !== 'undefined' ? self : this, function (CropDB) {
  'use strict';

  // Storage key for local browser persistence
  const STORAGE_KEY = 'terraforge_user_input_data_v1';

  // Backend endpoint configuration (override via TerraforgeUserData.setBackendUrl)
  let backendConfig = {
    endpointUrl: '/api/v1/agronomic-plan', // Default relative backend path
    timeoutMs: 10000,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    }
  };

  /**
   * Internal User Input State
   */
  const internalState = {
    // Territory Identification
    territory: {
      code: 'LK',
      name: 'Sri Lanka',
      zone: 'Tropical Agro-Climatic Grid'
    },

    // Step 02: Demarcated Parcel
    parcel: {
      areaHectares: 10.0,
      areaAcres: 24.71,
      perimeterKm: 1.28,
      center: [7.8731, 80.7718],
      coordinates: [] // Array of { lat: number, lng: number }
    },

    // Step 03: Selected Cultivation Strategy
    // Options: 'current' (Active Standing Crop) | 'rotation' (Crop Rotation Cycle) | 'none' (No Rotation / Fallow)
    selectedOption: 'rotation',

    // Step 03/04a: Active Standing Crop Configuration (used when selectedOption === 'current')
    activeCropConfig: {
      cropId: 'rice',
      startDate: '2026-10-01'
    },

    // Step 04b: Multi-Season Crop Rotation Plan (used when selectedOption === 'rotation')
    rotationPlan: {
      activeSeasonId: 'maha',
      seasons: [
        {
          seasonId: 'maha',
          seasonName: 'Maha Season (North-East Monsoon)',
          startDate: '2026-10-01',
          harvestDate: '2027-03-31',
          plantedCropIds: ['rice', 'corn']
        },
        {
          seasonId: 'yala',
          seasonName: 'Yala Season (South-West Monsoon)',
          startDate: '2027-05-01',
          harvestDate: '2027-08-31',
          plantedCropIds: ['soybeans', 'cassava']
        },
        {
          seasonId: 'perennial',
          seasonName: 'Year-Round Perennial Cycle',
          startDate: '2026-10-01',
          harvestDate: '2027-09-30',
          plantedCropIds: ['tea', 'coconut']
        }
      ]
    },

    // Step 05: Farm Constraints & Prioritization Matrix (Applied across all 3 options)
    constraintsAndPriorities: {
      irrigationAccess: 'limited', // 'none' | 'limited' | 'full'
      availableEquipment: ['tractor', 'harvester', 'pump'],
      targetMarkets: ['regional', 'export'],
      priorityWeights: {
        waterSaving: 0.80,
        soilHealth: 0.75,
        income: 0.90,
        erosionControl: 0.70,
        forage: 0.45
      },
      normalizeWeights: false
    }
  };

  // Change notification subscribers
  const subscribers = [];

  function notifySubscribers() {
    const payload = TerraforgeUserData.getBackendPayload();
    subscribers.forEach(cb => {
      try {
        cb(payload);
      } catch (err) {
        console.error('[TerraforgeUserData] Subscriber notification failed:', err);
      }
    });

    if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
      try {
        window.dispatchEvent(new CustomEvent('terraforge:userdata:update', { detail: payload }));
      } catch (e) {
        // ignore
      }
    }
  }

  // =========================================================================
  // Public Data Store & Backend Pipeline
  // =========================================================================
  const TerraforgeUserData = {

    /**
     * Set the cultivation strategy option
     * @param {'current'|'rotation'|'none'} option 
     */
    setStrategy(option) {
      if (!['current', 'rotation', 'none'].includes(option)) {
        console.warn(`[TerraforgeUserData] Invalid strategy "${option}". Expected 'current', 'rotation', or 'none'.`);
        return;
      }
      internalState.selectedOption = option;
      this.saveToStorage();
      notifySubscribers();
    },

    /**
     * Get current strategy
     * @returns {'current'|'rotation'|'none'}
     */
    getStrategy() {
      return internalState.selectedOption;
    },

    /**
     * Configure Active Standing Crop (Option 1)
     * @param {string} cropId 
     * @param {string} startDate YYYY-MM-DD
     */
    setActiveCrop(cropId, startDate) {
      if (cropId) internalState.activeCropConfig.cropId = String(cropId).trim();
      if (startDate) internalState.activeCropConfig.startDate = String(startDate).trim();
      this.saveToStorage();
      notifySubscribers();
    },

    /**
     * Configure Season Dates in Crop Rotation Cycle (Option 2)
     * @param {string} seasonId 'maha' | 'yala' | 'perennial'
     * @param {string} startDate 
     * @param {string} harvestDate 
     */
    setSeasonDates(seasonId, startDate, harvestDate) {
      const season = internalState.rotationPlan.seasons.find(s => s.seasonId === seasonId);
      if (season) {
        if (startDate) season.startDate = startDate;
        if (harvestDate) season.harvestDate = harvestDate;
        this.saveToStorage();
        notifySubscribers();
      }
    },

    /**
     * Set the active season in the rotation cycle
     * @param {string} seasonId 
     */
    setActiveSeason(seasonId) {
      if (['maha', 'yala', 'perennial'].includes(seasonId)) {
        internalState.rotationPlan.activeSeasonId = seasonId;
        this.saveToStorage();
        notifySubscribers();
      }
    },

    /**
     * Configure Planted Crops for a Season in Rotation Cycle (Option 2)
     * @param {string} seasonId 'maha' | 'yala' | 'perennial'
     * @param {string[]} cropIds Array of crop IDs from CropDB
     */
    setSeasonPlantedCrops(seasonId, cropIds) {
      const season = internalState.rotationPlan.seasons.find(s => s.seasonId === seasonId);
      if (season && Array.isArray(cropIds)) {
        season.plantedCropIds = [...cropIds];
        this.saveToStorage();
        notifySubscribers();
      }
    },

    /**
     * Configure Demarcated Parcel Geometry (Step 02)
     * @param {Object} parcelData 
     */
    setParcel(parcelData) {
      if (!parcelData) return;
      if (typeof parcelData.areaHectares === 'number') internalState.parcel.areaHectares = parcelData.areaHectares;
      if (typeof parcelData.areaAcres === 'number') internalState.parcel.areaAcres = parcelData.areaAcres;
      if (typeof parcelData.perimeterKm === 'number') internalState.parcel.perimeterKm = parcelData.perimeterKm;
      if (Array.isArray(parcelData.coordinates)) internalState.parcel.coordinates = parcelData.coordinates;
      if (parcelData.center) internalState.parcel.center = parcelData.center;
      this.saveToStorage();
      notifySubscribers();
    },

    /**
     * Configure Step 05 Constraints
     * @param {Object} constraints 
     */
    setConstraints(constraints) {
      if (!constraints) return;
      if (constraints.irrigationAccess) {
        internalState.constraintsAndPriorities.irrigationAccess = constraints.irrigationAccess;
      }
      if (Array.isArray(constraints.availableEquipment)) {
        internalState.constraintsAndPriorities.availableEquipment = [...constraints.availableEquipment];
      }
      if (Array.isArray(constraints.targetMarkets)) {
        internalState.constraintsAndPriorities.targetMarkets = [...constraints.targetMarkets];
      }
      this.saveToStorage();
      notifySubscribers();
    },

    /**
     * Configure Step 05 Priority Weights
     * @param {Object} weights 
     */
    setPriorityWeights(weights) {
      if (!weights) return;
      internalState.constraintsAndPriorities.priorityWeights = {
        ...internalState.constraintsAndPriorities.priorityWeights,
        ...weights
      };
      this.saveToStorage();
      notifySubscribers();
    },

    /**
     * Get Raw Internal State
     * @returns {Object}
     */
    getRawState() {
      return JSON.parse(JSON.stringify(internalState));
    },

    // =======================================================================
    // 3. CORE BACKEND PAYLOAD BUILDER
    // =======================================================================
    /**
     * Constructs the structured user input payload specifically tailored for backend ingestion.
     * Follows the exact conditional business logic requested:
     * 
     * • Condition 1: Active Standing Crop ('current')
     *   -> Adds selected crop data + crop starting date + Step 5 constraints & priorities.
     * 
     * • Condition 2: Crop Rotation Cycle ('rotation')
     *   -> Adds each season's starting date, harvesting date, and planted crops + Step 5 constraints & priorities.
     * 
     * • Condition 3: No Crop Rotation / Fallow ('none')
     *   -> Adds ONLY Step 5 constraints & priorities (+ parcel & territory metadata).
     * 
     * @returns {Object}
     */
    getBackendPayload() {
      const db = (typeof window !== 'undefined' && (window.CropDB || window.TerraforgeCrops)) || CropDB;

      // Base Envelope (Common across all payloads)
      const payload = {
        schemaVersion: '2.1.0',
        generatedAt: new Date().toISOString(),
        territory: {
          countryCode: internalState.territory.code,
          countryName: internalState.territory.name,
          agroGridZone: internalState.territory.zone
        },
        parcelDemarcation: {
          areaHectares: Number(internalState.parcel.areaHectares.toFixed(2)),
          areaAcres: Number(internalState.parcel.areaAcres.toFixed(2)),
          perimeterKm: Number(internalState.parcel.perimeterKm.toFixed(3)),
          polygonVertices: internalState.parcel.coordinates.map(v => ({
            lat: Number(v.lat),
            lng: Number(v.lng)
          }))
        },
        selectedStrategy: internalState.selectedOption
      };

      // =====================================================================
      // CONDITION 1: Active Standing Crop Configuration
      // =====================================================================
      if (internalState.selectedOption === 'current') {
        const cropObj = db ? db.getById(internalState.activeCropConfig.cropId) : null;
        payload.activeCropConfiguration = {
          cropId: internalState.activeCropConfig.cropId,
          cropDetails: cropObj || {
            id: internalState.activeCropConfig.cropId,
            name: 'Paddy Rice',
            category: 'Cereals',
            baseYieldHa: 5.2
          },
          sowingStartDate: internalState.activeCropConfig.startDate,
          daysSincePlanting: this._computeDaysSince(internalState.activeCropConfig.startDate),
          estimatedHarvestDate: this._computeHarvestDate(
            internalState.activeCropConfig.startDate,
            cropObj ? cropObj.growingDurationDays : 120
          )
        };
      }

      // =====================================================================
      // CONDITION 2: Multi-Season Crop Rotation Cycle
      // =====================================================================
      else if (internalState.selectedOption === 'rotation') {
        payload.cropRotationCycle = {
          activeSeason: internalState.rotationPlan.activeSeasonId,
          totalSeasonsConfigured: internalState.rotationPlan.seasons.length,
          seasons: internalState.rotationPlan.seasons.map(s => {
            // Resolve crop objects for each planted crop ID
            const resolvedCrops = s.plantedCropIds.map(cId => {
              const crop = db ? db.getById(cId) : null;
              return crop || { id: cId, name: cId };
            });

            return {
              seasonId: s.seasonId,
              seasonName: s.seasonName,
              startDate: s.startDate,
              harvestDate: s.harvestDate,
              cycleDurationDays: this._computeDurationDays(s.startDate, s.harvestDate),
              plantedCrops: resolvedCrops
            };
          })
        };
      }

      // =====================================================================
      // CONDITION 3: No Crop Rotation / Fallow Soil Baseline
      // =====================================================================
      else if (internalState.selectedOption === 'none') {
        payload.fallowSoilProfile = {
          status: 'raw_fallow_soil',
          description: 'No prior crop rotation sequencing configured. Soil modeled on virgin / rested baseline.',
          bypassedSteps: ['Step 04: Crop Calibration & Growth Windows']
        };
      }

      // =====================================================================
      // ALL OPTIONS: Step 05 Constraints & Priorities Included in All Payloads
      // =====================================================================
      payload.constraintsAndPriorities = {
        irrigationAccess: internalState.constraintsAndPriorities.irrigationAccess,
        availableEquipment: [...internalState.constraintsAndPriorities.availableEquipment],
        targetMarkets: [...internalState.constraintsAndPriorities.targetMarkets],
        priorityWeights: {
          waterSaving: internalState.constraintsAndPriorities.priorityWeights.waterSaving,
          soilHealth: internalState.constraintsAndPriorities.priorityWeights.soilHealth,
          income: internalState.constraintsAndPriorities.priorityWeights.income,
          erosionControl: internalState.constraintsAndPriorities.priorityWeights.erosionControl,
          forage: internalState.constraintsAndPriorities.priorityWeights.forage
        }
      };

      return payload;
    },

    // =======================================================================
    // 4. BACKEND TRANSMISSION & INTEGRATION HOOKS
    // =======================================================================

    /**
     * Configure backend endpoint options
     * @param {string} url 
     * @param {Object} options 
     */
    setBackendUrl(url, options = {}) {
      if (url) backendConfig.endpointUrl = url;
      if (options.headers) backendConfig.headers = { ...backendConfig.headers, ...options.headers };
      if (options.timeoutMs) backendConfig.timeoutMs = options.timeoutMs;
    },

    /**
     * Transmit user input payload to your connected backend
     * @param {string} [customEndpoint] Optional custom endpoint to override default
     * @returns {Promise<{ success: boolean, data?: any, error?: string }>}
     */
    async submitToBackend(customEndpoint) {
      const url = customEndpoint || backendConfig.endpointUrl;
      const payload = this.getBackendPayload();

      try {
        console.info(`[TerraforgeUserData] Transmitting payload to backend endpoint: ${url}`);

        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), backendConfig.timeoutMs);

        const response = await fetch(url, {
          method: 'POST',
          headers: backendConfig.headers,
          body: JSON.stringify(payload),
          signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          const errText = await response.text();
          throw new Error(`Backend responded with HTTP ${response.status}: ${errText || response.statusText}`);
        }

        const data = await response.json();
        console.info('[TerraforgeUserData] Backend successfully accepted payload:', data);
        return { success: true, data };
      } catch (err) {
        console.error('[TerraforgeUserData] Backend submission failed:', err);
        return { success: false, error: err.message, payload };
      }
    },

    /**
     * Download the structured user input payload as a formatted JSON file
     * @param {string} [filename] 
     */
    exportJson(filename = 'terraforge-user-data.json') {
      const payload = this.getBackendPayload();
      const jsonStr = JSON.stringify(payload, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/json;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      return payload;
    },

    /**
     * Save current state to browser localStorage for session persistence
     */
    saveToStorage() {
      if (typeof localStorage === 'undefined') return;
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(internalState));
      } catch (e) {
        console.warn('[TerraforgeUserData] Could not write to localStorage:', e);
      }
    },

    /**
     * Rehydrate state from browser localStorage if available
     * @returns {boolean} Whether stored state was recovered
     */
    loadFromStorage() {
      if (typeof localStorage === 'undefined') return false;
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (!raw) return false;
        const parsed = JSON.parse(raw);
        if (parsed && typeof parsed === 'object') {
          // Deep merge recovered fields
          if (parsed.selectedOption) internalState.selectedOption = parsed.selectedOption;
          if (parsed.activeCropConfig) internalState.activeCropConfig = { ...internalState.activeCropConfig, ...parsed.activeCropConfig };
          if (parsed.rotationPlan) internalState.rotationPlan = { ...internalState.rotationPlan, ...parsed.rotationPlan };
          if (parsed.constraintsAndPriorities) {
            internalState.constraintsAndPriorities = {
              ...internalState.constraintsAndPriorities,
              ...parsed.constraintsAndPriorities
            };
          }
          if (parsed.parcel) internalState.parcel = { ...internalState.parcel, ...parsed.parcel };
          notifySubscribers();
          return true;
        }
      } catch (e) {
        console.warn('[TerraforgeUserData] Could not restore from localStorage:', e);
      }
      return false;
    },

    /**
     * Reset user inputs back to baseline defaults
     */
    resetInputs() {
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem(STORAGE_KEY);
      }
      internalState.selectedOption = 'rotation';
      internalState.activeCropConfig = { cropId: 'rice', startDate: '2026-10-01' };
      notifySubscribers();
    },

    /**
     * Subscribe to user input payload changes
     * @param {Function} callback 
     * @returns {Function} Unsubscribe handle
     */
    subscribe(callback) {
      if (typeof callback === 'function') {
        subscribers.push(callback);
        try {
          callback(this.getBackendPayload());
        } catch (e) {
          console.error('[TerraforgeUserData] Error in subscriber initial callback:', e);
        }
      }
      return () => {
        const idx = subscribers.indexOf(callback);
        if (idx > -1) subscribers.splice(idx, 1);
      };
    },

    // =======================================================================
    // Internal Date Calculation Utilities
    // =======================================================================
    _computeDaysSince(dateStr) {
      if (!dateStr) return 0;
      const start = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - start.getTime();
      return Math.max(0, Math.floor(diffMs / (1000 * 60 * 60 * 24)));
    },

    _computeHarvestDate(startDateStr, durationDays = 120) {
      if (!startDateStr) return null;
      const d = new Date(startDateStr);
      d.setDate(d.getDate() + Number(durationDays));
      return d.toISOString().split('T')[0];
    },

    _computeDurationDays(startStr, endStr) {
      if (!startStr || !endStr) return 120;
      const s = new Date(startStr);
      const e = new Date(endStr);
      const diff = e.getTime() - s.getTime();
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      return days > 0 ? days : 120;
    }
  };

  // Attempt automatic rehydration on initial load
  TerraforgeUserData.loadFromStorage();

  return TerraforgeUserData;
}));
