/**
 * TERRAFORGE AGRO | Industrial Agronomic Intelligence Platform
 * Apple UI Architecture + Leaflet Geodesic Polygon Engine
 */

(function () {
  'use strict';

  // =========================================================================
  // 1. Agricultural Country Geodatabase
  // =========================================================================
  const COUNTRY_DATABASE = [
    { code: 'US', name: 'United States', flag: '🇺🇸', center: [39.8283, -98.5795], zoom: 5, defaultAgriArea: 'Corn Belt, Midwest' },
    { code: 'BR', name: 'Brazil', flag: '🇧🇷', center: [-14.235, -51.9253], zoom: 5, defaultAgriArea: 'Mato Grosso & Cerrado' },
    { code: 'UA', name: 'Ukraine', flag: '🇺🇦', center: [48.3794, 31.1656], zoom: 6, defaultAgriArea: 'Chernozem Black Soil Belt' },
    { code: 'CA', name: 'Canada', flag: '🇨🇦', center: [51.2538, -105.3232], zoom: 5, defaultAgriArea: 'Saskatchewan & Alberta Prairies' },
    { code: 'IN', name: 'India', flag: '🇮🇳', center: [20.5937, 78.9629], zoom: 5, defaultAgriArea: 'Indo-Gangetic Plain, Punjab' },
    { code: 'AU', name: 'Australia', flag: '🇦🇺', center: [-25.2744, 133.7751], zoom: 5, defaultAgriArea: 'Murray-Darling Basin' },
    { code: 'AR', name: 'Argentina', flag: '🇦🇷', center: [-38.4161, -63.6167], zoom: 5, defaultAgriArea: 'Pampas Humedas' },
    { code: 'FR', name: 'France', flag: '🇫🇷', center: [46.2276, 2.2137], zoom: 6, defaultAgriArea: 'Beauce & Nouvelle-Aquitaine' },
    { code: 'DE', name: 'Germany', flag: '🇩🇪', center: [51.1657, 10.4515], zoom: 6, defaultAgriArea: 'Lower Saxony & Bavaria' },
    { code: 'ES', name: 'Spain', flag: '🇪🇸', center: [40.4637, -3.7492], zoom: 6, defaultAgriArea: 'Castilla y Leon & Andalusia' },
    { code: 'CN', name: 'China', flag: '🇨🇳', center: [35.8617, 104.1954], zoom: 5, defaultAgriArea: 'Northeast Plain & Yellow River' },
    { code: 'IT', name: 'Italy', flag: '🇮🇹', center: [41.8719, 12.5674], zoom: 6, defaultAgriArea: 'Po Valley & Tuscany' },
    { code: 'PL', name: 'Poland', flag: '🇵🇱', center: [51.9194, 19.1451], zoom: 6, defaultAgriArea: 'Greater Poland & Silesia' },
    { code: 'TR', name: 'Turkey', flag: '🇹🇷', center: [38.9637, 35.2433], zoom: 6, defaultAgriArea: 'Central Anatolia & Cukurova' },
    { code: 'KZ', name: 'Kazakhstan', flag: '🇰🇿', center: [48.0196, 66.9237], zoom: 5, defaultAgriArea: 'Northern Steppe Grain Zone' },
    { code: 'MX', name: 'Mexico', flag: '🇲🇽', center: [23.6345, -102.5528], zoom: 5, defaultAgriArea: 'Sinaloa & Bajio Valleys' },
    { code: 'ZA', name: 'South Africa', flag: '🇿🇦', center: [-30.5595, 22.9375], zoom: 6, defaultAgriArea: 'Free State Maize Triangle' },
    { code: 'ID', name: 'Indonesia', flag: '🇮🇩', center: [-0.7893, 113.9213], zoom: 5, defaultAgriArea: 'Java & Sumatra Plains' },
    { code: 'RO', name: 'Romania', flag: '🇷🇴', center: [45.9432, 24.9668], zoom: 6, defaultAgriArea: 'Danube Plain' },
    { code: 'GB', name: 'United Kingdom', flag: '🇬🇧', center: [55.3781, -3.436], zoom: 6, defaultAgriArea: 'East Anglia & Yorkshire' }
  ];

  // Available Crops Data with Industrial Yield and Price Benchmarks
  const CROPS_DATA = [
    { id: 'wheat', name: 'Winter Wheat', category: 'Cereals', emoji: '🌾', baseYieldHa: 7.8, baseRevenueHa: 2350, waterReq: 0.55, soilBenefit: 0.7 },
    { id: 'corn', name: 'Industrial Corn / Maize', category: 'Cereals', emoji: '🌽', baseYieldHa: 11.4, baseRevenueHa: 3100, waterReq: 0.85, soilBenefit: 0.5 },
    { id: 'soybeans', name: 'High-Protein Soybeans', category: 'Oilseeds', emoji: '🫘', baseYieldHa: 3.6, baseRevenueHa: 2650, waterReq: 0.60, soilBenefit: 0.9 },
    { id: 'canola', name: 'Canola / Rapeseed', category: 'Oilseeds', emoji: '🌼', baseYieldHa: 3.2, baseRevenueHa: 2200, waterReq: 0.50, soilBenefit: 0.75 },
    { id: 'barley', name: 'Malting Barley', category: 'Cereals', emoji: '🌾', baseYieldHa: 6.4, baseRevenueHa: 1950, waterReq: 0.45, soilBenefit: 0.65 },
    { id: 'sunflower', name: 'Oilseed Sunflower', category: 'Oilseeds', emoji: '🌻', baseYieldHa: 2.8, baseRevenueHa: 1850, waterReq: 0.40, soilBenefit: 0.6 },
    { id: 'cotton', name: 'Industrial Cotton', category: 'Fiber', emoji: '☁️', baseYieldHa: 1.8, baseRevenueHa: 2900, waterReq: 0.90, soilBenefit: 0.4 },
    { id: 'alfalfa', name: 'Perennial Alfalfa', category: 'Forage', emoji: '🌿', baseYieldHa: 14.5, baseRevenueHa: 2400, waterReq: 0.70, soilBenefit: 0.95 },
    { id: 'sorghum', name: 'Drought Sorghum', category: 'Cereals', emoji: '🌾', baseYieldHa: 5.5, baseRevenueHa: 1600, waterReq: 0.35, soilBenefit: 0.7 },
    { id: 'potatoes', name: 'Industrial Potatoes', category: 'Tubers', emoji: '🥔', baseYieldHa: 42.0, baseRevenueHa: 6800, waterReq: 0.95, soilBenefit: 0.45 },
    { id: 'sugarbeets', name: 'Sugar Beets', category: 'Roots', emoji: '🌱', baseYieldHa: 65.0, baseRevenueHa: 4200, waterReq: 0.80, soilBenefit: 0.55 },
    { id: 'silage', name: 'Silage Biomass Corn', category: 'Forage', emoji: '🌱', baseYieldHa: 38.0, baseRevenueHa: 2800, waterReq: 0.75, soilBenefit: 0.6 }
  ];

  // =========================================================================
  // 2. Application State
  // =========================================================================
  const state = {
    selectedCountry: COUNTRY_DATABASE[0], // Default US
    drawingMode: false,
    polygonVertices: [],      // Array of L.LatLng
    polygonCompleted: false,
    parcelAreaHa: 0,
    parcelAreaAc: 0,
    parcelPerimeterKm: 0,
    parcelCenter: null,
    
    // Step 2: Crops & Season
    season: 'spring_summer',
    selectedCropIds: ['wheat', 'soybeans'],
    
    // Step 3: Farm Constraints
    irrigationAccess: 'limited', // 'none' | 'limited' | 'full'
    availableEquipment: ['tractor', 'drill', 'combine'],
    targetMarkets: ['regional', 'export'],
    
    // Step 4: Priority Sliders (0.0 to 1.0 weights)
    weights: {
      waterSaving: 0.75,
      soilHealth: 0.85,
      income: 0.90,
      erosionControl: 0.65,
      forage: 0.50
    },
    normalizeWeights: false
  };

  // Leaflet references
  let map = null;
  let satelliteLayer = null;
  let vectorLayer = null;
  let activeTileLayer = 'satellite';
  
  // Drawing overlays
  let tempMarkersLayer = null;
  let tempPolyline = null;
  let guideLine = null;
  let completedPolygon = null;
  let firstPointMarker = null;

  // =========================================================================
  // 3. Initialization
  // =========================================================================
  document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initCountrySearch();
    initQuickCountryChips();
    initMapTools();
    initCropSelection();
    initSeasonControls();
    initConstraintControls();
    initPrioritySliders();
    initActionButtons();

    // Initial simulation run with sample parcel
    createPresetSampleParcel();
    runAgronomicSimulation();
  });

  // =========================================================================
  // 4. Map Engine Initialization
  // =========================================================================
  function initMap() {
    // Esri World Imagery (High-res satellite, crucial for industrial agriculture)
    satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Tiles &copy; Esri, Maxar, Earthstar Geographics',
      maxZoom: 19
    });

    // Carto Positron (High-contrast clean vector for administrative borders)
    vectorLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; OpenStreetMap, &copy; CARTO',
      maxZoom: 19
    });

    map = L.map('industrialMap', {
      center: state.selectedCountry.center,
      zoom: state.selectedCountry.zoom,
      layers: [satelliteLayer],
      zoomControl: false,
      attributionControl: false // Attribution hidden as requested
    });

    // Add layers group
    tempMarkersLayer = L.layerGroup().addTo(map);

    // Map Event Listeners for Polygon Drawing
    map.on('click', onMapClick);
    map.on('mousemove', onMapMouseMove);

    // Prevent map dragging when drawing with rapid clicks
    map.on('dblclick', (e) => {
      if (state.drawingMode && state.polygonVertices.length >= 3) {
        L.DomEvent.stop(e);
        completePolygon();
      }
    });
  }

  // Preset sample field parcel in Kansas/Iowa so the user sees immediate richness
  function createPresetSampleParcel() {
    const lat = 38.905;
    const lng = -98.35;
    const sampleVertices = [
      L.latLng(lat, lng),
      L.latLng(lat + 0.018, lng + 0.005),
      L.latLng(lat + 0.024, lng + 0.038),
      L.latLng(lat + 0.008, lng + 0.045),
      L.latLng(lat - 0.012, lng + 0.022)
    ];

    state.polygonVertices = sampleVertices;
    state.polygonCompleted = true;
    renderCompletedPolygon(sampleVertices);
    updateParcelHUD();
    
    // Fly to Kansas field
    map.setView([lat + 0.006, lng + 0.02], 13);
  }

  // =========================================================================
  // 5. Interactive Polygon Drawing Engine (Unlimited Edges)
  // =========================================================================
  function setDrawingMode(active) {
    state.drawingMode = active;
    const drawBtn = document.getElementById('btnDrawParcel');
    const hintEl = document.getElementById('polygonGuideHint');
    
    if (active) {
      drawBtn.classList.add('active-tool');
      drawBtn.innerHTML = `
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <span>Drawing Active...</span>
      `;
      hintEl.style.display = 'inline-flex';
      hintEl.textContent = 'Click map to place vertex 1. Add unlimited vertices.';
      map.getContainer().style.cursor = 'crosshair';

      // Clear existing polygon if starting fresh
      clearPolygon();
    } else {
      drawBtn.classList.remove('active-tool');
      drawBtn.innerHTML = `
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
          <polyline points="2 17 12 22 22 17"></polyline>
          <polyline points="2 12 12 17 22 12"></polyline>
        </svg>
        <span>Draw Parcel Area</span>
      `;
      hintEl.style.display = 'none';
      map.getContainer().style.cursor = '';
      if (guideLine) {
        map.removeLayer(guideLine);
        guideLine = null;
      }
    }
  }

  function onMapClick(e) {
    if (!state.drawingMode || state.polygonCompleted) return;

    const clickedLatLng = e.latlng;
    const vertices = state.polygonVertices;

    // Check if clicked near the very first point to snap and close
    if (vertices.length >= 3) {
      const firstPt = vertices[0];
      const distPixels = map.latLngToContainerPoint(clickedLatLng).distanceTo(map.latLngToContainerPoint(firstPt));

      if (distPixels <= 24) {
        // Connected to the first edge!
        completePolygon();
        return;
      }
    }

    // Add new vertex (No limit on edge count)
    vertices.push(clickedLatLng);
    const vertexIndex = vertices.length;

    // Add vertex point marker with Apple aesthetic
    const isFirst = vertexIndex === 1;
    const marker = createVertexMarker(clickedLatLng, isFirst, vertexIndex);
    tempMarkersLayer.addLayer(marker);

    if (isFirst) {
      firstPointMarker = marker;
      marker.on('click', () => {
        if (state.polygonVertices.length >= 3) {
          completePolygon();
        }
      });
    }

    // Redraw polyline between placed vertices
    updateDrawingPolyline();

    // Update Guide Hint
    const hintEl = document.getElementById('polygonGuideHint');
    if (vertexIndex < 3) {
      hintEl.textContent = `${vertexIndex} point${vertexIndex > 1 ? 's' : ''} set. Need at least 3 points.`;
    } else {
      hintEl.innerHTML = `<strong>${vertexIndex} vertices placed.</strong> Click the first point or double-click to close parcel boundary.`;
    }
  }

  function onMapMouseMove(e) {
    if (!state.drawingMode || state.polygonCompleted || state.polygonVertices.length === 0) return;

    const mouseLatLng = e.latlng;
    const lastVertex = state.polygonVertices[state.polygonVertices.length - 1];

    // Update dynamic dashed guideline
    if (!guideLine) {
      guideLine = L.polyline([lastVertex, mouseLatLng], {
        color: '#38C172',
        weight: 2,
        dashArray: '6, 6',
        opacity: 0.9
      }).addTo(map);
    } else {
      guideLine.setLatLngs([lastVertex, mouseLatLng]);
    }

    // Check proximity to first point for magnetic snap feedback
    if (state.polygonVertices.length >= 3 && firstPointMarker) {
      const firstPt = state.polygonVertices[0];
      const dist = map.latLngToContainerPoint(mouseLatLng).distanceTo(map.latLngToContainerPoint(firstPt));
      
      const el = firstPointMarker.getElement();
      if (el) {
        if (dist <= 24) {
          el.classList.add('snap-first-point');
          el.innerHTML = '<div class="snap-pulse-circle" title="Click to close polygon"></div>';
        } else {
          el.classList.remove('snap-first-point');
          el.innerHTML = `<div style="width:12px; height:12px; background:#187741; border:2px solid #FFFFFF; border-radius:50%; box-shadow:0 1px 4px rgba(0,0,0,0.4);"></div>`;
        }
      }
    }
  }

  function createVertexMarker(latlng, isFirst, index) {
    const iconHtml = isFirst 
      ? `<div style="width:14px; height:14px; background:#187741; border:2px solid #FFFFFF; border-radius:50%; box-shadow:0 2px 6px rgba(0,0,0,0.5);"></div>`
      : `<div style="width:10px; height:10px; background:#38C172; border:2px solid #FFFFFF; border-radius:50%; box-shadow:0 1px 4px rgba(0,0,0,0.4);"></div>`;

    const icon = L.divIcon({
      className: 'apple-map-vertex-node',
      html: iconHtml,
      iconSize: isFirst ? [14, 14] : [10, 10],
      iconAnchor: isFirst ? [7, 7] : [5, 5]
    });

    return L.marker(latlng, { icon: icon });
  }

  function updateDrawingPolyline() {
    if (tempPolyline) {
      map.removeLayer(tempPolyline);
    }

    if (state.polygonVertices.length > 1) {
      tempPolyline = L.polyline(state.polygonVertices, {
        color: '#249D57',
        weight: 3,
        opacity: 0.85
      }).addTo(map);
    }
  }

  // Triggered when the last edge is connected back to the first edge
  function completePolygon() {
    if (state.polygonVertices.length < 3) return;

    state.polygonCompleted = true;
    setDrawingMode(false);

    // Remove guide line and temp polyline
    if (guideLine) {
      map.removeLayer(guideLine);
      guideLine = null;
    }
    if (tempPolyline) {
      map.removeLayer(tempPolyline);
      tempPolyline = null;
    }
    tempMarkersLayer.clearLayers();

    renderCompletedPolygon(state.polygonVertices);
    updateParcelHUD();

    // Trigger Apple Haptic/Visual notification
    showNotification('Field Boundary Closed', `Generated boundary with ${state.polygonVertices.length} edges across ${state.parcelAreaHa.toFixed(1)} hectares.`);

    // Reveal the "Continue" button as specified
    const continueBtn = document.getElementById('btnContinueToCrops');
    continueBtn.style.display = 'inline-flex';

    // Update step tracker
    updateStepTracker(1, true);

    // Run dynamic model
    runAgronomicSimulation();
  }

  function renderCompletedPolygon(latlngs) {
    if (completedPolygon) {
      map.removeLayer(completedPolygon);
    }

    completedPolygon = L.polygon(latlngs, {
      color: '#187741',
      weight: 3,
      fillColor: '#38C172',
      fillOpacity: 0.28,
      dashArray: null
    }).addTo(map);

    // Calculate Geodesic area
    calculatePolygonMetrics(latlngs);

    // Add vertex dots
    latlngs.forEach((pt, i) => {
      const nodeMarker = L.circleMarker(pt, {
        radius: 4,
        fillColor: '#FFFFFF',
        color: '#187741',
        weight: 2,
        fillOpacity: 1
      });
      tempMarkersLayer.addLayer(nodeMarker);
    });

    // Fit map bounds smoothly
    map.fitBounds(completedPolygon.getBounds(), { padding: [50, 50], maxZoom: 16 });
  }

  // Geodesic Area Calculation using Spherical Shoelace Formula
  function calculatePolygonMetrics(latlngs) {
    const R = 6378137; // Earth radius in meters (WGS84)
    const len = latlngs.length;
    let area = 0;
    let perimeter = 0;

    for (let i = 0; i < len; i++) {
      const p1 = latlngs[i];
      const p2 = latlngs[(i + 1) % len];

      // Perimeter distance
      perimeter += p1.distanceTo(p2);

      // Spherical Shoelace Area
      const lat1Rad = p1.lat * Math.PI / 180;
      const lat2Rad = p2.lat * Math.PI / 180;
      const lngDiffRad = (p2.lng - p1.lng) * Math.PI / 180;

      area += lngDiffRad * (2 + Math.sin(lat1Rad) + Math.sin(lat2Rad));
    }

    area = Math.abs(area * R * R / 4.0);

    const hectares = area / 10000;
    const acres = hectares * 2.47105;
    const perimeterKm = perimeter / 1000;

    state.parcelAreaHa = hectares;
    state.parcelAreaAc = acres;
    state.parcelPerimeterKm = perimeterKm;
    state.parcelCenter = completedPolygon ? completedPolygon.getBounds().getCenter() : latlngs[0];
  }

  function updateParcelHUD() {
    document.getElementById('hudAreaHa').textContent = state.parcelAreaHa.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    document.getElementById('hudAreaAc').textContent = state.parcelAreaAc.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    document.getElementById('hudPerimeter').textContent = state.parcelPerimeterKm.toFixed(2);
    document.getElementById('hudVertices').textContent = state.polygonVertices.length;
  }

  function clearPolygon() {
    state.polygonVertices = [];
    state.polygonCompleted = false;
    state.parcelAreaHa = 0;
    state.parcelAreaAc = 0;
    state.parcelPerimeterKm = 0;

    if (completedPolygon) {
      map.removeLayer(completedPolygon);
      completedPolygon = null;
    }
    if (tempPolyline) {
      map.removeLayer(tempPolyline);
      tempPolyline = null;
    }
    if (guideLine) {
      map.removeLayer(guideLine);
      guideLine = null;
    }
    tempMarkersLayer.clearLayers();

    updateParcelHUD();
    document.getElementById('btnContinueToCrops').style.display = 'none';
  }

  // =========================================================================
  // 6. Map Tools & Layer Switcher
  // =========================================================================
  function initMapTools() {
    document.getElementById('btnDrawParcel').addEventListener('click', () => {
      setDrawingMode(!state.drawingMode);
    });

    document.getElementById('btnClearParcel').addEventListener('click', () => {
      clearPolygon();
      setDrawingMode(false);
      showNotification('Field Cleared', 'Parcel polygon boundary reset.');
    });

    document.getElementById('btnCenterMap').addEventListener('click', () => {
      if (completedPolygon) {
        map.fitBounds(completedPolygon.getBounds(), { padding: [50, 50] });
      } else {
        map.flyTo(state.selectedCountry.center, state.selectedCountry.zoom);
      }
    });

    // Optional Satellite vs Vector Layer Toggle
    const btnLayerSat = document.getElementById('btnLayerSatellite');
    const btnLayerVec = document.getElementById('btnLayerVector');

    if (btnLayerSat && btnLayerVec) {
      btnLayerSat.addEventListener('click', () => {
        if (activeTileLayer !== 'satellite') {
          map.removeLayer(vectorLayer);
          map.addLayer(satelliteLayer);
          activeTileLayer = 'satellite';
          btnLayerSat.classList.add('active');
          btnLayerVec.classList.remove('active');
        }
      });

      btnLayerVec.addEventListener('click', () => {
        if (activeTileLayer !== 'vector') {
          map.removeLayer(satelliteLayer);
          map.addLayer(vectorLayer);
          activeTileLayer = 'vector';
          btnLayerVec.classList.add('active');
          btnLayerSat.classList.remove('active');
        }
      });
    }

    // "Continue to Configuration" Button
    document.getElementById('btnContinueToCrops').addEventListener('click', () => {
      revealConfigurationSections();
    });
  }

  function revealConfigurationSections() {
    const configSection = document.getElementById('cropAndConstraintsSection');
    configSection.classList.add('visible');

    // Update step tracker
    updateStepTracker(2, true);

    // Smooth scroll down to the configuration section
    configSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // =========================================================================
  // 7. Country Search & Selection Tool
  // =========================================================================
  function initCountrySearch() {
    const searchInput = document.getElementById('countrySearchInput');
    const dropdown = document.getElementById('countryDropdownList');

    // Populate dropdown options
    renderDropdownItems(COUNTRY_DATABASE);

    searchInput.addEventListener('focus', () => {
      dropdown.classList.add('open');
    });

    searchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase().trim();
      const filtered = COUNTRY_DATABASE.filter(c => 
        c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q) || c.defaultAgriArea.toLowerCase().includes(q)
      );
      renderDropdownItems(filtered);
      dropdown.classList.add('open');
    });

    // Close on click outside
    document.addEventListener('click', (e) => {
      if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.classList.remove('open');
      }
    });
  }

  function renderDropdownItems(countries) {
    const dropdown = document.getElementById('countryDropdownList');
    dropdown.innerHTML = '';

    if (countries.length === 0) {
      dropdown.innerHTML = '<div style="padding: 0.8rem 1rem; font-size: 0.85rem; color: #667085;">No agricultural region found</div>';
      return;
    }

    countries.forEach(c => {
      const item = document.createElement('div');
      item.className = 'country-option-item';
      if (c.code === state.selectedCountry.code) {
        item.classList.add('selected');
      }

      item.innerHTML = `
        <div style="display:flex; align-items:center;">
          <span class="country-flag-icon">${c.flag}</span>
          <span>${c.name}</span>
        </div>
        <span style="font-size: 0.72rem; color: #667085;">${c.defaultAgriArea}</span>
      `;

      item.addEventListener('click', () => {
        selectCountry(c);
        dropdown.classList.remove('open');
      });

      dropdown.appendChild(item);
    });
  }

  function selectCountry(country) {
    state.selectedCountry = country;
    const searchInput = document.getElementById('countrySearchInput');
    searchInput.value = `${country.flag} ${country.name}`;

    // Update country chips
    document.querySelectorAll('.quick-country-chip').forEach(chip => {
      chip.classList.toggle('active', chip.dataset.code === country.code);
    });

    // Smoothly fly map to target country
    map.flyTo(country.center, country.zoom, {
      duration: 1.6,
      easeLinearity: 0.25
    });

    showNotification('Country Selected', `Focusing satellite feed on ${country.name} agricultural zones.`);
    runAgronomicSimulation();
  }

  function initQuickCountryChips() {
    const container = document.getElementById('quickCountryChips');
    if (!container) return; // Cleanly bypassed when chips row is removed
    const popularCodes = ['US', 'BR', 'UA', 'CA', 'IN', 'AU', 'AR', 'FR'];

    popularCodes.forEach(code => {
      const c = COUNTRY_DATABASE.find(item => item.code === code);
      if (!c) return;

      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = `quick-country-chip ${c.code === state.selectedCountry.code ? 'active' : ''}`;
      chip.dataset.code = c.code;
      chip.innerHTML = `<span>${c.flag}</span> <span>${c.name}</span>`;

      chip.addEventListener('click', () => {
        selectCountry(c);
      });

      container.appendChild(chip);
    });
  }

  // =========================================================================
  // 8. Crops & Seasonal Growth Controls
  // =========================================================================
  function initCropSelection() {
    const container = document.getElementById('cropsGridContainer');
    container.innerHTML = '';

    CROPS_DATA.forEach(crop => {
      const card = document.createElement('div');
      card.className = `crop-card-item ${state.selectedCropIds.includes(crop.id) ? 'selected' : ''}`;
      card.dataset.id = crop.id;

      card.innerHTML = `
        <span class="crop-emoji">${crop.emoji}</span>
        <span class="crop-name">${crop.name}</span>
        <span class="crop-yield-tag">${crop.baseYieldHa} t/ha est.</span>
      `;

      card.addEventListener('click', () => {
        const index = state.selectedCropIds.indexOf(crop.id);
        if (index > -1) {
          if (state.selectedCropIds.length > 1) { // Keep at least one
            state.selectedCropIds.splice(index, 1);
            card.classList.remove('selected');
          } else {
            showNotification('Selection Notice', 'Please select at least one agricultural crop.');
          }
        } else {
          state.selectedCropIds.push(crop.id);
          card.classList.add('selected');
        }
        runAgronomicSimulation();
      });

      container.appendChild(card);
    });
  }

  function initSeasonControls() {
    // Segmented option controls
    const seasonOptions = document.querySelectorAll('.season-option');
    seasonOptions.forEach(opt => {
      opt.addEventListener('click', () => {
        seasonOptions.forEach(o => o.classList.remove('active'));
        opt.classList.add('active');
        state.season = opt.dataset.season;
        runAgronomicSimulation();
      });
    });

    const startInput = document.getElementById('cropPeriodStart');
    const endInput = document.getElementById('cropPeriodEnd');
    if (startInput) startInput.addEventListener('change', runAgronomicSimulation);
    if (endInput) endInput.addEventListener('change', runAgronomicSimulation);
  }

  // =========================================================================
  // 9. Farm Constraints Controls
  // =========================================================================
  function initConstraintControls() {
    // 1. Irrigation Access (None, Limited, Full)
    const irrChoices = document.querySelectorAll('.irrigation-card-choice');
    irrChoices.forEach(card => {
      card.addEventListener('click', () => {
        irrChoices.forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        state.irrigationAccess = card.dataset.irrigation;
        runAgronomicSimulation();
      });
    });

    // 2. Available Equipment (Tractor, Drill, Combine, Pivot, Drone Swarm)
    const equipChips = document.querySelectorAll('.equipment-chip');
    equipChips.forEach(chip => {
      chip.addEventListener('click', () => {
        const eq = chip.dataset.equip;
        const idx = state.availableEquipment.indexOf(eq);
        if (idx > -1) {
          state.availableEquipment.splice(idx, 1);
          chip.classList.remove('selected');
        } else {
          state.availableEquipment.push(eq);
          chip.classList.add('selected');
        }
        runAgronomicSimulation();
      });
    });

    // 3. Target Markets (Local, Regional, Export, Organic)
    const marketChips = document.querySelectorAll('.market-chip');
    marketChips.forEach(chip => {
      chip.addEventListener('click', () => {
        const m = chip.dataset.market;
        const idx = state.targetMarkets.indexOf(m);
        if (idx > -1) {
          if (state.targetMarkets.length > 1) {
            state.targetMarkets.splice(idx, 1);
            chip.classList.remove('selected');
          }
        } else {
          state.targetMarkets.push(m);
          chip.classList.add('selected');
        }
        runAgronomicSimulation();
      });
    });
  }

  // =========================================================================
  // 10. Priority Sliders (0.0 to 1.0 weights)
  // =========================================================================
  function initPrioritySliders() {
    const sliderKeys = ['waterSaving', 'soilHealth', 'income', 'erosionControl', 'forage'];

    sliderKeys.forEach(key => {
      const slider = document.getElementById(`slider_${key}`);
      const badge = document.getElementById(`badge_${key}`);
      if (!slider || !badge) return;

      // Set initial value
      slider.value = state.weights[key];
      badge.textContent = state.weights[key].toFixed(2);
      updateSliderFill(slider);

      slider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        state.weights[key] = val;
        badge.textContent = val.toFixed(2);
        updateSliderFill(slider);

        // Normalize if toggle active
        if (state.normalizeWeights) {
          normalizeOtherSliders(key, val);
        }

        runAgronomicSimulation();
      });
    });

    // Normalize Toggle Switch
    const normSwitch = document.getElementById('toggleNormalizeWeights');
    if (normSwitch) {
      normSwitch.addEventListener('change', (e) => {
        state.normalizeWeights = e.target.checked;
        if (state.normalizeWeights) {
          normalizeAllCurrentSliders();
          runAgronomicSimulation();
        }
      });
    }
  }

  function updateSliderFill(slider) {
    const min = parseFloat(slider.min) || 0;
    const max = parseFloat(slider.max) || 1;
    const val = parseFloat(slider.value);
    const pct = ((val - min) / (max - min)) * 100;
    slider.style.background = `linear-gradient(to right, #38C172 0%, #187741 ${pct}%, #E2E8F0 ${pct}%, #E2E8F0 100%)`;
  }

  function normalizeOtherSliders(changedKey, changedVal) {
    const keys = ['waterSaving', 'soilHealth', 'income', 'erosionControl', 'forage'];
    const otherKeys = keys.filter(k => k !== changedKey);
    const targetRemaining = Math.max(0, 1.0 - changedVal);

    const currentOtherSum = otherKeys.reduce((acc, k) => acc + state.weights[k], 0);

    otherKeys.forEach(k => {
      if (currentOtherSum > 0) {
        state.weights[k] = (state.weights[k] / currentOtherSum) * targetRemaining;
      } else {
        state.weights[k] = targetRemaining / otherKeys.length;
      }
      const slider = document.getElementById(`slider_${k}`);
      const badge = document.getElementById(`badge_${k}`);
      if (slider && badge) {
        slider.value = state.weights[k];
        badge.textContent = state.weights[k].toFixed(2);
        updateSliderFill(slider);
      }
    });
  }

  function normalizeAllCurrentSliders() {
    const keys = ['waterSaving', 'soilHealth', 'income', 'erosionControl', 'forage'];
    const total = keys.reduce((acc, k) => acc + state.weights[k], 0);
    if (total === 0) return;

    keys.forEach(k => {
      state.weights[k] = state.weights[k] / total;
      const slider = document.getElementById(`slider_${k}`);
      const badge = document.getElementById(`badge_${k}`);
      if (slider && badge) {
        slider.value = state.weights[k];
        badge.textContent = state.weights[k].toFixed(2);
        updateSliderFill(slider);
      }
    });
  }

  // =========================================================================
  // 11. Industrial Agronomic Simulation Engine (Taprobyte-Style Output)
  // =========================================================================
  function runAgronomicSimulation() {
    const ha = state.parcelAreaHa > 0 ? state.parcelAreaHa : 185.0; // Fallback to realistic Kansas industrial pivot parcel if not drawn yet

    // Active selected crops data
    const activeCrops = CROPS_DATA.filter(c => state.selectedCropIds.includes(c.id));
    const avgRevenueHa = activeCrops.reduce((acc, c) => acc + c.baseRevenueHa, 0) / (activeCrops.length || 1);
    const avgYieldHa = activeCrops.reduce((acc, c) => acc + c.baseYieldHa, 0) / (activeCrops.length || 1);
    const avgWaterReq = activeCrops.reduce((acc, c) => acc + c.waterReq, 0) / (activeCrops.length || 1);
    const avgSoilBenefit = activeCrops.reduce((acc, c) => acc + c.soilBenefit, 0) / (activeCrops.length || 1);

    // Multipliers from Constraints
    let irrigationMultiplier = 1.0;
    let waterSavingPotential = 0.5;
    if (state.irrigationAccess === 'full') {
      irrigationMultiplier = 1.25;
      waterSavingPotential = 0.35 + (state.weights.waterSaving * 0.45);
    } else if (state.irrigationAccess === 'limited') {
      irrigationMultiplier = 1.05;
      waterSavingPotential = 0.45 + (state.weights.waterSaving * 0.35);
    } else { // None (Dryland)
      irrigationMultiplier = 0.82;
      waterSavingPotential = 0.85; // Natural dryland minimal consumption
    }

    // Equipment efficiency boost
    let equipmentBoost = 1.0;
    if (state.availableEquipment.includes('drill')) equipmentBoost += 0.06; // No-till improves soil and moisture retention
    if (state.availableEquipment.includes('drone')) equipmentBoost += 0.05; // Precision drone spray avoids waste
    if (state.availableEquipment.includes('combine')) equipmentBoost += 0.04;

    // Target market premium
    let marketPremium = 1.0;
    if (state.targetMarkets.includes('export')) marketPremium += 0.08;
    if (state.targetMarkets.includes('organic')) marketPremium += 0.18;

    // Financial Calculation (Matches DOW J Style Card in Reference Image!)
    const incomeWeightBonus = 0.85 + (state.weights.income * 0.3);
    const grossRevenue = ha * avgRevenueHa * irrigationMultiplier * equipmentBoost * marketPremium * incomeWeightBonus;
    const netMarginPct = 14.5 + (state.weights.income * 9.2) - (state.weights.waterSaving * 2.1) + (state.availableEquipment.length * 1.2);

    // Key KPIs
    const waterSavedVolumeM3 = Math.round(ha * 1200 * (1 - avgWaterReq * (1 - state.weights.waterSaving * 0.4)));
    const soilHealthScore = Math.min(98, Math.round((avgSoilBenefit * 60) + (state.weights.soilHealth * 25) + (state.availableEquipment.includes('drill') ? 12 : 0)));
    const erosionMitigationScore = Math.min(99, Math.round((state.weights.erosionControl * 50) + (state.weights.soilHealth * 30) + (state.availableEquipment.includes('drill') ? 18 : 8)));
    const biomassYieldTons = Math.round(ha * (avgYieldHa * 1.35) * (0.8 + state.weights.forage * 0.5));
    const fuelSavingsLiters = Math.round(ha * 14.8 * (state.availableEquipment.includes('drill') ? 1.4 : 1.0));

    // Update DOW J Card (Reference Asset Styling)
    updateDowCard(grossRevenue, netMarginPct);

    // Update KPI Matrix
    updateKpiCards({
      waterVolume: waterSavedVolumeM3,
      soilHealth: soilHealthScore,
      erosionScore: erosionMitigationScore,
      biomass: biomassYieldTons,
      fuel: fuelSavingsLiters,
      ha: ha
    });

    // Update Radar Chart SVG
    renderRadarChart({
      water: state.weights.waterSaving,
      soil: state.weights.soilHealth,
      income: state.weights.income,
      erosion: state.weights.erosionControl,
      forage: state.weights.forage
    });

    // Update Strategic Directives
    updateDirectivesList();
  }

  // Update DOW J Aesthetic Financial Card
  function updateDowCard(revenue, marginPct) {
    const valEl = document.getElementById('dowMetricValue');
    const pillEl = document.getElementById('dowMarginPill');
    const sparklineSvg = document.getElementById('dowSparklinePath');

    if (valEl) {
      valEl.textContent = `$${Math.round(revenue).toLocaleString('en-US')}`;
    }

    if (pillEl) {
      pillEl.innerHTML = `+ ${marginPct.toFixed(1)}% Margins`;
    }

    // Generate dynamic sparkline path
    if (sparklineSvg) {
      const points = [
        [0, 24],
        [15, 20],
        [30, 26],
        [45, 14],
        [60, 18],
        [75, 8],
        [90, 12],
        [105, 4]
      ];
      const d = points.reduce((acc, pt, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${pt[0]} ${pt[1]}`, '');
      sparklineSvg.setAttribute('d', d);
    }
  }

  function updateKpiCards(kpis) {
    const elWater = document.getElementById('kpiWaterConserved');
    const elSoil = document.getElementById('kpiSoilHealth');
    const elErosion = document.getElementById('kpiErosionMitigation');
    const elBiomass = document.getElementById('kpiBiomassYield');

    if (elWater) elWater.textContent = `${kpis.waterVolume.toLocaleString('en-US')} m³`;
    if (elSoil) elSoil.textContent = `${kpis.soilHealth} / 100`;
    if (elErosion) elErosion.textContent = `${kpis.erosionScore}%`;
    if (elBiomass) elBiomass.textContent = `${kpis.biomass.toLocaleString('en-US')} t`;
  }

  // Apple-grade SVG Radar Chart
  function renderRadarChart(weights) {
    const svg = document.getElementById('radarSvg');
    if (!svg) return;

    const cx = 160;
    const cy = 140;
    const rMax = 95;

    // 5 Axes: Water, Soil, Income, Erosion, Forage
    const keys = ['water', 'soil', 'income', 'erosion', 'forage'];
    const labels = ['Water Saving', 'Soil Health', 'Income Yield', 'Erosion Control', 'Forage Biomass'];
    const count = keys.length;

    let polygonPoints = [];
    let axesHtml = '';

    // Draw background concentric web rings (0.25, 0.5, 0.75, 1.0)
    let ringsHtml = '';
    [0.25, 0.5, 0.75, 1.0].forEach(level => {
      let ringPts = [];
      for (let i = 0; i < count; i++) {
        const angle = (i * 2 * Math.PI / count) - (Math.PI / 2);
        const x = cx + Math.cos(angle) * (rMax * level);
        const y = cy + Math.sin(angle) * (rMax * level);
        ringPts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
      }
      ringsHtml += `<polygon points="${ringPts.join(' ')}" fill="none" stroke="rgba(16, 24, 40, 0.08)" stroke-width="1" />`;
    });

    for (let i = 0; i < count; i++) {
      const angle = (i * 2 * Math.PI / count) - (Math.PI / 2);
      const val = Math.max(0.12, weights[keys[i]]);
      const x = cx + Math.cos(angle) * (rMax * val);
      const y = cy + Math.sin(angle) * (rMax * val);
      polygonPoints.push(`${x.toFixed(1)},${y.toFixed(1)}`);

      // Axis spoke
      const spokeX = cx + Math.cos(angle) * rMax;
      const spokeY = cy + Math.sin(angle) * rMax;
      axesHtml += `<line x1="${cx}" y1="${cy}" x2="${spokeX.toFixed(1)}" y2="${spokeY.toFixed(1)}" stroke="rgba(16, 24, 40, 0.1)" stroke-width="1" />`;

      // Axis label placement
      const labelX = cx + Math.cos(angle) * (rMax + 22);
      const labelY = cy + Math.sin(angle) * (rMax + 14);
      axesHtml += `<text x="${labelX.toFixed(1)}" y="${labelY.toFixed(1)}" font-size="10" font-weight="600" fill="#475467" text-anchor="middle" dominant-baseline="middle">${labels[i]}</text>`;
    }

    svg.innerHTML = `
      <g>
        ${ringsHtml}
        ${axesHtml}
        <!-- Data Polygon Fill -->
        <polygon points="${polygonPoints.join(' ')}" 
                 fill="rgba(56, 193, 114, 0.28)" 
                 stroke="#187741" 
                 stroke-width="2.5" 
                 stroke-linejoin="round" />
        <!-- Data Vertex Markers -->
        ${polygonPoints.map(pt => `<circle cx="${pt.split(',')[0]}" cy="${pt.split(',')[1]}" r="4" fill="#38C172" stroke="#FFFFFF" stroke-width="2" />`).join('')}
      </g>
    `;
  }

  function updateDirectivesList() {
    const list = document.getElementById('agronomicDirectivesList');
    if (!list) return;

    const directives = [];

    // Directive 1 based on irrigation
    if (state.irrigationAccess === 'none') {
      directives.push(`<strong>Dryland Water Conservation Protocol:</strong> Implement deep stubble retention and prioritize drought-tolerant varieties for ${state.selectedCountry.name}'s climate.`);
    } else if (state.irrigationAccess === 'limited') {
      directives.push(`<strong>Deficit Irrigation Strategy:</strong> Deploy precision pulse scheduling timed to reproductive anthesis to achieve an estimated ${(state.weights.waterSaving * 40).toFixed(0)}% water conservation index.`);
    } else {
      directives.push(`<strong>High-Frequency Variable Irrigation:</strong> Calibrate center pivot flow rates with satellite soil moisture data to maintain optimal root saturation without deep percolation loss.`);
    }

    // Directive 2 based on equipment
    if (state.availableEquipment.includes('drill')) {
      directives.push(`<strong>Direct-Seeding Soil Protection:</strong> Utilize no-till drill to minimize topsoil disturbance, boosting mycorrhizal fungal networks and soil organic carbon.`);
    } else {
      directives.push(`<strong>Tillage Management:</strong> Shift toward reduced-tillage passes to curb tractor fuel consumption and mitigate surface wind erosion.`);
    }

    // Directive 3 based on markets
    if (state.targetMarkets.includes('export')) {
      directives.push(`<strong>Export Quality Specifications:</strong> Maintain strict moisture thresholds (<12.5%) and protein standards to capture terminal port price premiums.`);
    } else {
      directives.push(`<strong>Local Hub Logistics:</strong> Align harvest timing with regional elevator receiving contracts to minimize post-harvest warehousing depreciation.`);
    }

    // Directive 4 based on sliders
    if (state.weights.soilHealth >= 0.75) {
      directives.push(`<strong>Soil Regeneration Priority:</strong> Introduce multi-species cover crops (legumes + radishes) between harvest windows to fix up to 45 kg N/ha naturally.`);
    } else {
      directives.push(`<strong>Industrial Yield Maximization:</strong> Prioritize split-nitrogen applications at peak vegetative canopy to optimize economic return per hectare.`);
    }

    list.innerHTML = directives.map(d => `
      <li class="directive-item">
        <span class="directive-check">✓</span>
        <span>${d}</span>
      </li>
    `).join('');
  }

  // =========================================================================
  // 12. Action Buttons & Export Utilities
  // =========================================================================
  function initActionButtons() {
    // Export Ag-Plan
    const exportBtn = document.getElementById('btnExportPlan');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => {
        exportConfigurationJson();
      });
    }

    // Print / PDF Button
    const printBtn = document.getElementById('btnPrintReport');
    if (printBtn) {
      printBtn.addEventListener('click', () => {
        window.print();
      });
    }
  }

  function exportConfigurationJson() {
    const exportData = {
      platform: 'TERRAFORGE AGRO Intelligence',
      timestamp: new Date().toISOString(),
      country: state.selectedCountry,
      parcel: {
        vertices: state.polygonVertices.map(v => ({ lat: v.lat, lng: v.lng })),
        areaHectares: state.parcelAreaHa,
        areaAcres: state.parcelAreaAc,
        perimeterKm: state.parcelPerimeterKm
      },
      crops: state.selectedCropIds,
      season: state.season,
      constraints: {
        irrigation: state.irrigationAccess,
        equipment: state.availableEquipment,
        markets: state.targetMarkets
      },
      priorityWeights: state.weights
    };

    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(exportData, null, 2));
    const dlAnchor = document.createElement('a');
    dlAnchor.setAttribute('href', dataStr);
    dlAnchor.setAttribute('download', `terraforge-agri-plan-${state.selectedCountry.code.toLowerCase()}.json`);
    dlAnchor.click();

    showNotification('Export Complete', 'Industrial configuration package downloaded as JSON.');
  }

  // Notification Toast Helper
  function showNotification(title, message) {
    let toast = document.getElementById('appleToast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'appleToast';
      toast.style.position = 'fixed';
      toast.style.bottom = '24px';
      toast.style.right = '24px';
      toast.style.background = 'rgba(21, 82, 57, 0.94)';
      toast.style.backdropFilter = 'blur(16px)';
      toast.style.color = '#FFFFFF';
      toast.style.padding = '12px 20px';
      toast.style.borderRadius = '16px';
      toast.style.boxShadow = '0 8px 30px rgba(0, 0, 0, 0.2)';
      toast.style.zIndex = '9999';
      toast.style.fontSize = '0.85rem';
      toast.style.display = 'flex';
      toast.style.flexDirection = 'column';
      toast.style.gap = '2px';
      toast.style.transition = 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)';
      toast.style.pointerEvents = 'none';
      document.body.appendChild(toast);
    }

    toast.innerHTML = `<strong style="font-size:0.9rem; color:#A8EEC1;">${title}</strong><span>${message}</span>`;
    toast.style.transform = 'translateY(0) scale(1)';
    toast.style.opacity = '1';

    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => {
      toast.style.transform = 'translateY(12px) scale(0.95)';
      toast.style.opacity = '0';
    }, 4000);
  }

  function updateStepTracker(activeStepNum, isCompleted) {
    const steps = document.querySelectorAll('.stage-step');
    steps.forEach((step, idx) => {
      const stepNum = idx + 1;
      if (stepNum < activeStepNum) {
        step.classList.add('completed');
        step.classList.remove('active');
      } else if (stepNum === activeStepNum) {
        step.classList.add('active');
        step.classList.remove('completed');
      } else {
        step.classList.remove('active', 'completed');
      }
    });
  }

})();
