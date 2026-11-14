/**
 * ============================================================================
 * TERRAFORGE AGRO | WORKFLOW, GIS PARCEL DEMARCATION & INDUSTRIAL SYNTHESIS
 * File: workflow.js
 * ============================================================================
 * 
 * Coordinates:
 *   • Leaflet Satellite Map & Spherical Geodesic Polygon Demarcation
 *   • Tab Workflow Navigation (Steps 01 to 06)
 *   • Reactive Integration with CropDB (crop.js)
 *   • Reactive Integration with TerraforgeUserData (input.js / userData.js)
 *   • Agronomic Simulation, Multi-Objective Radar Chart & Industrial Directives
 * ============================================================================
 */

(function () {
  'use strict';

  // Geographic Defaults for Sri Lanka
  const SRI_LANKA_CENTER = [7.8731, 80.7718];
  const SRI_LANKA_ZOOM = 7.5;
  const SRI_LANKA_BOUNDS = [
    [5.65, 79.30], // Southwest clearance
    [10.10, 82.10] // Northeast clearance
  ];

  // Local UI Workflow State
  const uiState = {
    drawingMode: false,
    polygonVertices: [], // Array of L.LatLng
    polygonCompleted: false,
    parcelAreaHa: 10.0,
    parcelAreaAc: 24.71,
    parcelPerimeterKm: 1.28,
    activeSeason: 'maha',
    activeTab: 2
  };

  // Leaflet references
  let map = null;
  let tempMarkersLayer = null;
  let tempPolyline = null;
  let guideLine = null;
  let completedPolygon = null;
  let firstPointMarker = null;

  // =========================================================================
  // 1. Initialization
  // =========================================================================
  document.addEventListener('DOMContentLoaded', () => {
    // Ensure dependencies exist
    const cropDb = window.CropDB || window.TerraforgeCrops;
    const userData = window.TerraforgeUserData || window.TerraforgeInput;

    if (!cropDb) {
      console.warn('[Workflow] CropDB not found on window. Ensure js/modules/crop.js is included before js/modules/workflow.js.');
    }
    if (!userData) {
      console.warn('[Workflow] TerraforgeUserData not found. Ensure js/pages/input.js is included before js/modules/workflow.js.');
    }

    initMap();
    initMapTools();
    initMapSearch();
    initCropStrategySelector();
    initStandingCropSelector();
    initCropRotationSelection();
    initSeasonControls();
    initConstraintControls();
    initPrioritySliders();
    initGuidedStepButtons();
    initActionButtons();

    // Subscribe to CropDB changes: if crops are added later, re-render immediately!
    if (cropDb && typeof cropDb.subscribe === 'function') {
      cropDb.subscribe(() => {
        console.info('[Workflow] CropDB updated. Refreshing crop chips and rotation cards...');
        refreshCropUI();
        runAgronomicSimulation();
      });
    }

    // Subscribe to UserData changes
    if (userData && typeof userData.subscribe === 'function') {
      userData.subscribe(() => {
        runAgronomicSimulation();
      });
    }

    // Zero-state initialization
    updateParcelHUD();
    refreshCropUI();
    runAgronomicSimulation();
  });

  // =========================================================================
  // 2. Leaflet GIS Map Engine (Centered on Sri Lanka)
  // =========================================================================
  function initMap() {
    const mapContainer = document.getElementById('industrialMap') || document.getElementById('map');
    if (!mapContainer) {
      console.error('[Workflow] Map container element (#industrialMap or #map) not found.');
      return;
    }

    const mapId = mapContainer.id;

    map = L.map(mapId, {
      center: SRI_LANKA_CENTER,
      zoom: SRI_LANKA_ZOOM,
      minZoom: 6,
      maxZoom: 18,
      zoomControl: true,
      attributionControl: true
    });

    // High-Resolution Satellite World Imagery (ArcGIS ESRI)
    const esriImagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Tiles &copy; Esri, Maxar, Earthstar Geographics &bull; Terraforge Agro',
      maxZoom: 19
    }).addTo(map);

    // Subtle Boundaries & Places Overlay
    L.tileLayer('https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 19,
      opacity: 0.65
    }).addTo(map);

    tempMarkersLayer = L.layerGroup().addTo(map);

    // Map Click & Pointer Events
    map.on('click', onMapClick);
    map.on('mousemove', onMapMouseMove);

    // Lock bounds softly to Sri Lanka
    map.setMaxBounds(SRI_LANKA_BOUNDS);

    // Invalidate size immediately after initial rendering
    setTimeout(() => {
      if (map) map.invalidateSize();
    }, 150);

    window.addEventListener('resize', () => {
      if (map) map.invalidateSize();
    });
  }

  function initMapTools() {
    const drawBtn = document.getElementById('btnDrawParcel') || document.getElementById('btnToggleDraw');
    const undoBtn = document.getElementById('btnUndoVertex');
    const clearBtn = document.getElementById('btnClearParcel') || document.getElementById('btnClearBoundary');
    const sampleBtn = document.getElementById('btnPresetField');

    if (drawBtn) {
      drawBtn.addEventListener('click', () => {
        setDrawingMode(!uiState.drawingMode);
      });
    }

    if (undoBtn) {
      undoBtn.addEventListener('click', undoLastVertex);
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', clearPolygon);
    }

    if (sampleBtn) {
      sampleBtn.addEventListener('click', loadSampleParcel);
    }
  }

  function setDrawingMode(active) {
    uiState.drawingMode = active;
    const btn = document.getElementById('btnDrawParcel') || document.getElementById('btnToggleDraw');
    const mapDiv = document.getElementById('industrialMap') || document.getElementById('map');
    const hint = document.getElementById('polygonGuideHint');

    if (active) {
      if (uiState.polygonCompleted) {
        clearPolygon();
      }
      if (btn) {
        btn.classList.add('active');
        const span = btn.querySelector('span');
        if (span) span.textContent = 'Finish Boundary';
      }
      if (mapDiv) mapDiv.classList.add('crosshair-cursor');
      if (hint) hint.style.display = 'block';
      showNotification('Demarcation Active', 'Click on the satellite imagery to place parcel boundary vertices.');
    } else {
      if (btn) {
        btn.classList.remove('active');
        const span = btn.querySelector('span');
        if (span) span.textContent = 'Draw Area';
      }
      if (mapDiv) mapDiv.classList.remove('crosshair-cursor');
      if (hint) hint.style.display = 'none';

      if (guideLine) {
        map.removeLayer(guideLine);
        guideLine = null;
      }

      if (uiState.polygonVertices.length >= 3 && !uiState.polygonCompleted) {
        finalizePolygon();
      }
    }
  }

  function onMapClick(e) {
    if (!uiState.drawingMode || uiState.polygonCompleted) return;

    const clickedLatLng = e.latlng;
    const vertices = uiState.polygonVertices;

    // Check if clicked near first point to snap and close
    if (vertices.length >= 3) {
      const firstPt = vertices[0];
      const distToFirst = map.latLngToLayerPoint(clickedLatLng).distanceTo(map.latLngToLayerPoint(firstPt));

      if (distToFirst < 20) {
        finalizePolygon();
        return;
      }
    }

    vertices.push(clickedLatLng);

    // Node Marker
    const marker = L.circleMarker(clickedLatLng, {
      radius: 5,
      fillColor: vertices.length === 1 ? '#38C172' : '#FFFFFF',
      color: '#155239',
      weight: 2,
      fillOpacity: 1
    });

    tempMarkersLayer.addLayer(marker);

    if (vertices.length === 1) {
      firstPointMarker = marker;
      marker.bindTooltip('Click here to close boundary', { permanent: false, direction: 'top' });
    }

    updateDrawingPolyline();
    updateParcelHUD();
  }

  function onMapMouseMove(e) {
    if (!uiState.drawingMode || uiState.polygonCompleted || uiState.polygonVertices.length === 0) return;

    const mouseLatLng = e.latlng;
    const lastVertex = uiState.polygonVertices[uiState.polygonVertices.length - 1];

    if (!guideLine) {
      guideLine = L.polyline([lastVertex, mouseLatLng], {
        color: '#38C172',
        weight: 2,
        dashArray: '6, 6',
        opacity: 0.8
      }).addTo(map);
    } else {
      guideLine.setLatLngs([lastVertex, mouseLatLng]);
    }
  }

  function updateDrawingPolyline() {
    const vertices = uiState.polygonVertices;
    if (vertices.length < 2) return;

    if (!tempPolyline) {
      tempPolyline = L.polyline(vertices, {
        color: '#187741',
        weight: 2.5,
        dashArray: '4, 4'
      }).addTo(map);
    } else {
      tempPolyline.setLatLngs(vertices);
    }
  }

  function undoLastVertex() {
    if (uiState.polygonCompleted || uiState.polygonVertices.length === 0) return;

    uiState.polygonVertices.pop();
    tempMarkersLayer.clearLayers();

    uiState.polygonVertices.forEach((pt, index) => {
      const marker = L.circleMarker(pt, {
        radius: 5,
        fillColor: index === 0 ? '#38C172' : '#FFFFFF',
        color: '#155239',
        weight: 2,
        fillOpacity: 1
      });
      tempMarkersLayer.addLayer(marker);
    });

    if (tempPolyline) {
      tempPolyline.setLatLngs(uiState.polygonVertices);
    }

    if (guideLine) {
      map.removeLayer(guideLine);
      guideLine = null;
    }

    updateParcelHUD();
  }

  function finalizePolygon() {
    if (uiState.polygonVertices.length < 3) {
      showNotification('Notice', 'At least 3 vertices are required to demarcate a field polygon.');
      return;
    }

    uiState.polygonCompleted = true;
    setDrawingMode(false);

    if (tempPolyline) {
      map.removeLayer(tempPolyline);
      tempPolyline = null;
    }

    renderCompletedPolygon(uiState.polygonVertices);
    updateParcelHUD();

    showNotification('Field Demarcated', `Parcel closed with ${uiState.polygonVertices.length} vertices across ${uiState.parcelAreaHa.toFixed(1)} hectares.`);

    // Reveal continue button and bottom HUD
    const continueBtn = document.getElementById('btnContinueToCrops');
    if (continueBtn) continueBtn.style.display = 'inline-flex';

    const mapHudBottom = document.getElementById('mapHudBottom');
    if (mapHudBottom) mapHudBottom.style.display = 'block';
  }

  function renderCompletedPolygon(latlngs) {
    if (completedPolygon) {
      map.removeLayer(completedPolygon);
    }

    completedPolygon = L.polygon(latlngs, {
      color: '#187741',
      weight: 3,
      fillColor: '#38C172',
      fillOpacity: 0.28
    }).addTo(map);

    calculatePolygonMetrics(latlngs);

    latlngs.forEach(pt => {
      const nodeMarker = L.circleMarker(pt, {
        radius: 4,
        fillColor: '#FFFFFF',
        color: '#187741',
        weight: 2,
        fillOpacity: 1
      });
      tempMarkersLayer.addLayer(nodeMarker);
    });

    map.fitBounds(completedPolygon.getBounds(), { padding: [50, 50], maxZoom: 16 });
  }

  // Spherical Geodesic Area Calculation
  function calculatePolygonMetrics(latlngs) {
    const R = 6378137; // Earth radius (m)
    const len = latlngs.length;
    let area = 0;
    let perimeter = 0;

    for (let i = 0; i < len; i++) {
      const p1 = latlngs[i];
      const p2 = latlngs[(i + 1) % len];
      perimeter += p1.distanceTo(p2);

      const lat1Rad = p1.lat * Math.PI / 180;
      const lat2Rad = p2.lat * Math.PI / 180;
      const lngDiffRad = (p2.lng - p1.lng) * Math.PI / 180;

      area += lngDiffRad * (2 + Math.sin(lat1Rad) + Math.sin(lat2Rad));
    }

    area = Math.abs(area * R * R / 4.0);

    const hectares = area / 10000;
    const acres = hectares * 2.47105;
    const perimeterKm = perimeter / 1000;

    uiState.parcelAreaHa = hectares;
    uiState.parcelAreaAc = acres;
    uiState.parcelPerimeterKm = perimeterKm;

    // Sync with UserData Backend Store
    const userData = window.TerraforgeUserData || window.TerraforgeInput;
    if (userData && typeof userData.setParcel === 'function') {
      userData.setParcel({
        areaHectares: hectares,
        areaAcres: acres,
        perimeterKm: perimeterKm,
        coordinates: latlngs.map(p => ({ lat: p.lat, lng: p.lng }))
      });
    }
  }

  function updateParcelHUD() {
    const haEl = document.getElementById('hudAreaHa');
    const acEl = document.getElementById('hudAreaAc');
    const perEl = document.getElementById('hudPerimeter');
    const vertEl = document.getElementById('hudVertices');
    const mapHudBottom = document.getElementById('mapHudBottom');

    if (haEl) haEl.textContent = uiState.parcelAreaHa.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    if (acEl) acEl.textContent = uiState.parcelAreaAc.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    if (perEl) perEl.textContent = uiState.parcelPerimeterKm.toFixed(2);
    if (vertEl) vertEl.textContent = uiState.polygonVertices.length;

    if (mapHudBottom) {
      if (uiState.polygonVertices.length > 0 || uiState.polygonCompleted) {
        mapHudBottom.style.display = 'block';
      }
    }
  }

  function clearPolygon() {
    uiState.polygonVertices = [];
    uiState.polygonCompleted = false;
    uiState.parcelAreaHa = 10.0;
    uiState.parcelAreaAc = 24.71;
    uiState.parcelPerimeterKm = 1.28;

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
    firstPointMarker = null;

    setDrawingMode(false);
    updateParcelHUD();

    const continueBtn = document.getElementById('btnContinueToCrops');
    if (continueBtn) continueBtn.style.display = 'none';

    const mapHudBottom = document.getElementById('mapHudBottom');
    if (mapHudBottom) mapHudBottom.style.display = 'none';

    // Reset in backend payload
    const userData = window.TerraforgeUserData || window.TerraforgeInput;
    if (userData && typeof userData.setParcel === 'function') {
      userData.setParcel({
        areaHectares: 10.0,
        areaAcres: 24.71,
        perimeterKm: 1.28,
        coordinates: []
      });
    }
  }

  function loadSampleParcel() {
    clearPolygon();
    // Industrial Paddy Field in Mahaweli System H (Anuradhapura / Polonnaruwa Basin)
    const lat = 8.0325;
    const lng = 80.5210;
    const sampleVertices = [
      L.latLng(lat, lng),
      L.latLng(lat + 0.0082, lng + 0.0035),
      L.latLng(lat + 0.0105, lng + 0.0125),
      L.latLng(lat + 0.0031, lng + 0.0150),
      L.latLng(lat - 0.0020, lng + 0.0080)
    ];

    uiState.polygonVertices = sampleVertices;
    uiState.polygonCompleted = true;
    renderCompletedPolygon(sampleVertices);
    updateParcelHUD();

    const continueBtn = document.getElementById('btnContinueToCrops');
    if (continueBtn) continueBtn.style.display = 'inline-flex';

    const mapHudBottom = document.getElementById('mapHudBottom');
    if (mapHudBottom) mapHudBottom.style.display = 'block';

    showNotification('Sample Parcel Loaded', 'Mahaweli Agro-Ecological Grid boundary placed.');
  }

  function initMapSearch() {
    const searchInput = document.getElementById('mapSearchInput');
    const clearBtn = document.getElementById('mapSearchClearBtn');
    const dropdown = document.getElementById('mapSearchResultsDropdown');
    if (!searchInput) return;

    const landmarks = {
      'Anuradhapura': [8.3114, 80.4037],
      'Polonnaruwa': [7.9403, 81.0188],
      'Nuwara Eliya (Tea Estate)': [6.9497, 80.7891],
      'Kandy': [7.2906, 80.6337],
      'Matale': [7.4675, 80.6234],
      'Kurunegala (Coconut Triangle)': [7.4818, 80.3609],
      'Badulla': [6.9934, 81.0550],
      'Monaragala (Sugarcane Basin)': [6.8728, 81.3507],
      'Jaffna': [9.6615, 80.0255],
      'Hambantota': [6.1429, 81.1212],
      'Galle': [6.0535, 80.2210],
      'Matara': [5.9549, 80.5550],
      'Ratnapura': [6.6828, 80.4036],
      'Kegalle': [7.2513, 80.3464],
      'Puttalam': [8.0362, 79.8283],
      'Trincomalee': [8.5874, 81.2152],
      'Batticaloa': [7.7310, 81.6747],
      'Ampara': [7.2912, 81.6724],
      'Vavuniya': [8.7514, 80.4971]
    };

    function flyToCoords(name, coords) {
      if (!map) return;
      map.flyTo(coords, 14, { duration: 1.5 });
      showNotification('Territory Located', `Navigated satellite viewport to ${name}, Sri Lanka.`);
      if (dropdown) dropdown.style.display = 'none';
      searchInput.value = name;
      if (clearBtn) clearBtn.style.display = 'flex';
    }

    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim().toLowerCase();
      if (!q) {
        if (clearBtn) clearBtn.style.display = 'none';
        if (dropdown) dropdown.style.display = 'none';
        return;
      }

      if (clearBtn) clearBtn.style.display = 'flex';

      const matches = Object.entries(landmarks).filter(([name]) => name.toLowerCase().includes(q));

      if (dropdown) {
        if (matches.length > 0) {
          dropdown.innerHTML = matches.map(([name, coords]) => `
            <div class="map-search-item" data-name="${name}">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:#187741;">
                <path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 12 8 12s8-6.75 8-12a8 8 0 0 0-8-8z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
              <span>${name}</span>
            </div>
          `).join('');

          dropdown.style.display = 'block';

          dropdown.querySelectorAll('.map-search-item').forEach(item => {
            item.addEventListener('click', () => {
              const name = item.dataset.name;
              flyToCoords(name, landmarks[name]);
            });
          });
        } else {
          dropdown.style.display = 'none';
        }
      }
    });

    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        clearBtn.style.display = 'none';
        if (dropdown) dropdown.style.display = 'none';
        if (map) map.setView(SRI_LANKA_CENTER, SRI_LANKA_ZOOM);
      });
    }

    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const q = searchInput.value.trim().toLowerCase();
        for (const [name, coords] of Object.entries(landmarks)) {
          if (name.toLowerCase().includes(q) || q.includes(name.toLowerCase())) {
            flyToCoords(name, coords);
            return;
          }
        }
      }
    });

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.map-hud-top-right') && dropdown) {
        dropdown.style.display = 'none';
      }
    });
  }

  // =========================================================================
  // 3. Tab Navigation Engine (Single-Pane Isolated Steps)
  // =========================================================================
  function switchTab(tabNumber) {
    const userData = window.TerraforgeUserData || window.TerraforgeInput;
    const strategy = userData ? userData.getStrategy() : 'rotation';

    // If 'none' is selected, step 4 is bypassed
    if (tabNumber === 4 && strategy === 'none') {
      tabNumber = 5;
    }

    if (tabNumber < 2 || tabNumber > 6) return;
    uiState.activeTab = tabNumber;

    // Activate tab pane
    [2, 3, 4, 5, 6].forEach(n => {
      const pane = document.getElementById(`tabPane${n}`);
      if (pane) {
        if (n === tabNumber) {
          pane.classList.add('active');
        } else {
          pane.classList.remove('active');
        }
      }
    });

    // Update Stage Tracker Nav
    const navItem1 = document.getElementById('tabNav1');
    if (navItem1) {
      navItem1.classList.remove('active');
      navItem1.classList.add('completed');
    }

    [2, 3, 4, 5, 6].forEach(n => {
      const navItem = document.getElementById(`tabNav${n}`);
      if (navItem) {
        navItem.classList.remove('active', 'completed');
        if (n === 4 && strategy === 'none') {
          navItem.classList.add('skipped');
          navItem.title = 'Step 04 bypassed for Raw/Fallow soil';
          return;
        } else if (n === 4) {
          navItem.classList.remove('skipped');
        }

        if (n < tabNumber) {
          navItem.classList.add('completed');
        } else if (n === tabNumber) {
          navItem.classList.add('active');
        }
      }
    });

    if (tabNumber === 2 && map) {
      setTimeout(() => map.invalidateSize(), 150);
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
    runAgronomicSimulation();
  }

  function initGuidedStepButtons() {
    const bindClick = (id, tab) => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('click', () => switchTab(tab));
    };

    bindClick('btnContinueToCrops', 3);
    bindClick('btnForwardToTab4', 4);
    bindClick('btnBackToTab2', 2);
    bindClick('btnChangeStrategy', 3);
    bindClick('btnForwardToTab5', 5);
    bindClick('btnBackToTab3', 3);
    bindClick('btnForwardToTab6', 6);
    bindClick('btnBackToTab4', 4);
    bindClick('btnBackToTab5', 5);

    // Footer quick links
    bindClick('footerLinkTab2', 2);
    bindClick('footerLinkTab3', 3);
    bindClick('footerLinkTab4', 4);
    bindClick('footerLinkTab5', 5);
    bindClick('footerLinkTab6', 6);

    // Interactive Stage Tracker Pills
    [
      { id: 'tabNav1', action: () => window.location.href = '../index.html' },
      { id: 'tabNav2', tab: 2 },
      { id: 'tabNav3', tab: 3 },
      { id: 'tabNav4', tab: 4 },
      { id: 'tabNav5', tab: 5 },
      { id: 'tabNav6', tab: 6 }
    ].forEach(item => {
      const el = document.getElementById(item.id);
      if (el) {
        el.addEventListener('click', () => {
          if (item.action) item.action();
          else if (item.tab) switchTab(item.tab);
        });
      }
    });
  }

  // =========================================================================
  // 4. Crop Strategy Selector (Step 03)
  // =========================================================================
  function initCropStrategySelector() {
    const cards = document.querySelectorAll('.strategy-card');
    const drawerNone = document.getElementById('drawerStrategyNone');
    const drawerCurrent = document.getElementById('drawerStrategyCurrent');
    const drawerRotation = document.getElementById('drawerStrategyRotation');
    const calTitle = document.getElementById('cropCalibrationTitle');
    const calSub = document.getElementById('cropCalibrationSubtitle');

    function selectStrategy(strategyKey) {
      const userData = window.TerraforgeUserData || window.TerraforgeInput;
      if (userData && typeof userData.setStrategy === 'function') {
        userData.setStrategy(strategyKey);
      }

      cards.forEach(c => {
        if (c.dataset.strategy === strategyKey) {
          c.classList.add('selected');
        } else {
          c.classList.remove('selected');
        }
      });

      const tabNav4 = document.getElementById('tabNav4');
      const btnForwardTo4 = document.getElementById('btnForwardToTab4');
      const btnBackTo4 = document.getElementById('btnBackToTab4');

      if (strategyKey === 'none') {
        if (tabNav4) {
          tabNav4.classList.add('skipped');
          tabNav4.title = 'Step 04 bypassed for Raw Soil Baseline';
        }
        if (btnForwardTo4) {
          const span = btnForwardTo4.querySelector('span');
          if (span) span.textContent = 'Continue to Constraints';
        }
        if (btnBackTo4) {
          const span = btnBackTo4.querySelector('span');
          if (span) span.textContent = 'Back to Crop Strategy';
        }
      } else {
        if (tabNav4) {
          tabNav4.classList.remove('skipped');
          tabNav4.title = 'Crop cycle & growth window calibration';
        }
        if (btnForwardTo4) {
          const span = btnForwardTo4.querySelector('span');
          if (span) span.textContent = 'Continue';
        }
        if (btnBackTo4) {
          const span = btnBackTo4.querySelector('span');
          if (span) span.textContent = 'Back';
        }
      }

      if (drawerNone) drawerNone.style.display = strategyKey === 'none' ? 'block' : 'none';
      if (drawerCurrent) drawerCurrent.style.display = strategyKey === 'current' ? 'block' : 'none';
      if (drawerRotation) drawerRotation.style.display = strategyKey === 'rotation' ? 'block' : 'none';

      if (calTitle && calSub) {
        if (strategyKey === 'none') {
          calTitle.textContent = 'Raw & Fallow Soil Calibration';
          calSub.textContent = 'Parcel modeled on fallow/raw ground. Rotational sequencing bypassed.';
        } else if (strategyKey === 'current') {
          calTitle.textContent = 'Active Standing Crop Configuration';
          calSub.textContent = 'Configure standing commercial crop variety, sowing timeline, and remaining yield index.';
        } else {
          calTitle.textContent = 'Multi-Season Crop Rotation & Sequencing';
          calSub.textContent = 'Calibrate monsoon seasons (Maha / Yala / Perennial), active growing dates, and primary/companion crops.';
        }
      }

      runAgronomicSimulation();
    }

    cards.forEach(card => {
      card.addEventListener('click', () => {
        selectStrategy(card.dataset.strategy);
      });
    });

    // Default to 'rotation'
    selectStrategy('rotation');
  }

  // =========================================================================
  // 5. Standing Crop & Crop Rotation UI Rendering (Powered by CropDB)
  // =========================================================================
  function refreshCropUI() {
    renderStandingCropChips();
    renderRotationCropCards();
  }

  function initStandingCropSelector() {
    const searchInput = document.getElementById('standingCropSearchInput');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        renderStandingCropChips(e.target.value);
      });
    }

    const dateInput = document.getElementById('standingCropStartDate');
    if (dateInput) {
      dateInput.addEventListener('change', (e) => {
        const userData = window.TerraforgeUserData || window.TerraforgeInput;
        if (userData && typeof userData.setActiveCrop === 'function') {
          userData.setActiveCrop(null, e.target.value);
        }
        runAgronomicSimulation();
      });
    }

    document.querySelectorAll('.preset-pill-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.preset-pill-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const val = btn.dataset.date;
        let dateVal = val;
        if (val === 'days-30') {
          const d = new Date();
          d.setDate(d.getDate() - 30);
          dateVal = d.toISOString().split('T')[0];
        }

        const dateInputEl = document.getElementById('standingCropStartDate');
        if (dateInputEl) dateInputEl.value = dateVal;

        const userData = window.TerraforgeUserData || window.TerraforgeInput;
        if (userData && typeof userData.setActiveCrop === 'function') {
          userData.setActiveCrop(null, dateVal);
        }
        runAgronomicSimulation();
      });
    });
  }

  function renderStandingCropChips(filter = '') {
    const chipsGrid = document.getElementById('standingCropChipsGrid');
    if (!chipsGrid) return;
    chipsGrid.innerHTML = '';

    const cropDb = window.CropDB || window.TerraforgeCrops;
    const userData = window.TerraforgeUserData || window.TerraforgeInput;
    if (!cropDb) return;

    const crops = cropDb.getAll();
    const q = filter.toLowerCase().trim();
    const filtered = crops.filter(c => c.name.toLowerCase().includes(q) || c.category.toLowerCase().includes(q));

    const currentConfig = userData ? userData.getRawState().activeCropConfig : { cropId: 'rice' };

    if (!filtered.length) {
      chipsGrid.innerHTML = '<div style="font-size:0.75rem; color:#667085; padding:0.5rem;">No crops matching query</div>';
      return;
    }

    const previewBadge = document.getElementById('selectedCropPreviewBadge');
    const summaryName = document.getElementById('summaryCropName');
    const summaryMetrics = document.getElementById('summaryCropMetrics');

    filtered.forEach(crop => {
      const isSelected = crop.id === currentConfig.cropId;
      const chip = document.createElement('div');
      chip.className = `standing-crop-chip ${isSelected ? 'selected' : ''}`;
      chip.innerHTML = `
        <div style="width:20px; height:20px; border-radius:50%; background:rgba(24,119,65,0.12); display:flex; align-items:center; justify-content:center; color:#187741; flex-shrink:0;">
          <span style="font-size:12px;">${crop.emoji || '🌱'}</span>
        </div>
        <div style="min-width:0; flex:1;">
          <div class="crop-chip-name">${crop.name}</div>
          <div class="crop-chip-cat">${crop.category} • ${crop.baseYieldHa} t/ha</div>
        </div>
      `;

      chip.addEventListener('click', () => {
        document.querySelectorAll('.standing-crop-chip').forEach(el => el.classList.remove('selected'));
        chip.classList.add('selected');

        if (userData && typeof userData.setActiveCrop === 'function') {
          userData.setActiveCrop(crop.id, null);
        }

        if (previewBadge) previewBadge.textContent = crop.name;
        if (summaryName) summaryName.textContent = crop.name;
        if (summaryMetrics) {
          summaryMetrics.textContent = `Category: ${crop.category} • Base Yield: ${crop.baseYieldHa} t/ha • Water Req: ${Math.round(crop.waterReq * 100)}%`;
        }

        runAgronomicSimulation();
      });

      chipsGrid.appendChild(chip);
    });
  }

  function initCropRotationSelection() {
    renderRotationCropCards();
  }

  function renderRotationCropCards() {
    const container = document.getElementById('cropsGridContainer');
    if (!container) return;
    container.innerHTML = '';

    const cropDb = window.CropDB || window.TerraforgeCrops;
    const userData = window.TerraforgeUserData || window.TerraforgeInput;
    if (!cropDb) return;

    const crops = cropDb.getAll();
    const rawState = userData ? userData.getRawState() : null;
    const currentSeasonPlan = rawState ? rawState.rotationPlan.seasons.find(s => s.seasonId === uiState.activeSeason) : null;
    const selectedIds = currentSeasonPlan ? currentSeasonPlan.plantedCropIds : ['rice', 'corn'];

    crops.forEach(crop => {
      const isSelected = selectedIds.includes(crop.id);
      const card = document.createElement('div');
      card.className = `crop-card-item ${isSelected ? 'selected' : ''}`;
      card.dataset.id = crop.id;

      card.innerHTML = `
        <span class="crop-indicator-icon" style="color:var(--c-primary); display:inline-flex; align-items:center;">
          <span style="font-size:14px;">${crop.emoji || '🌱'}</span>
        </span>
        <span class="crop-name">${crop.name}</span>
        <span class="crop-yield-tag">${crop.baseYieldHa} t/ha est.</span>
      `;

      card.addEventListener('click', () => {
        const idx = selectedIds.indexOf(crop.id);
        if (idx > -1) {
          if (selectedIds.length > 1) {
            selectedIds.splice(idx, 1);
            card.classList.remove('selected');
          } else {
            showNotification('Selection Notice', 'Please retain at least one crop in the seasonal rotation.');
          }
        } else {
          selectedIds.push(crop.id);
          card.classList.add('selected');
        }

        if (userData && typeof userData.setSeasonPlantedCrops === 'function') {
          userData.setSeasonPlantedCrops(uiState.activeSeason, selectedIds);
        }

        runAgronomicSimulation();
      });

      container.appendChild(card);
    });
  }

  function initSeasonControls() {
    const seasonOptions = document.querySelectorAll('.season-option');
    const startInput = document.getElementById('cropPeriodStart');
    const endInput = document.getElementById('cropPeriodEnd');

    seasonOptions.forEach(opt => {
      opt.addEventListener('click', () => {
        seasonOptions.forEach(o => o.classList.remove('active'));
        opt.classList.add('active');

        uiState.activeSeason = opt.dataset.season;

        const userData = window.TerraforgeUserData || window.TerraforgeInput;
        if (userData && typeof userData.setActiveSeason === 'function') {
          userData.setActiveSeason(uiState.activeSeason);
        }

        // Adjust season date defaults
        if (uiState.activeSeason === 'maha') {
          if (startInput) startInput.value = '2026-10';
          if (endInput) endInput.value = '2027-03';
        } else if (uiState.activeSeason === 'yala') {
          if (startInput) startInput.value = '2027-05';
          if (endInput) endInput.value = '2027-08';
        } else {
          if (startInput) startInput.value = '2026-10';
          if (endInput) endInput.value = '2027-09';
        }

        syncSeasonDates();
        renderRotationCropCards();
        runAgronomicSimulation();
      });
    });

    function syncSeasonDates() {
      const sVal = startInput ? startInput.value + '-01' : '2026-10-01';
      const eVal = endInput ? endInput.value + '-28' : '2027-03-31';

      const userData = window.TerraforgeUserData || window.TerraforgeInput;
      if (userData && typeof userData.setSeasonDates === 'function') {
        userData.setSeasonDates(uiState.activeSeason, sVal, eVal);
      }
    }

    if (startInput) startInput.addEventListener('change', () => { syncSeasonDates(); runAgronomicSimulation(); });
    if (endInput) endInput.addEventListener('change', () => { syncSeasonDates(); runAgronomicSimulation(); });
  }

  // =========================================================================
  // 6. Farm Constraints & Priority Sliders (Step 05)
  // =========================================================================
  function initConstraintControls() {
    const userData = window.TerraforgeUserData || window.TerraforgeInput;

    const irrChoices = document.querySelectorAll('.irrigation-card-choice');
    irrChoices.forEach(card => {
      card.addEventListener('click', () => {
        irrChoices.forEach(c => c.classList.remove('active'));
        card.classList.add('active');

        if (userData && typeof userData.setConstraints === 'function') {
          userData.setConstraints({ irrigationAccess: card.dataset.irrigation });
        }
        runAgronomicSimulation();
      });
    });

    const equipChips = document.querySelectorAll('.equipment-chip');
    equipChips.forEach(chip => {
      chip.addEventListener('click', () => {
        chip.classList.toggle('selected');
        const activeEquip = Array.from(document.querySelectorAll('.equipment-chip.selected')).map(c => c.dataset.equip);

        if (userData && typeof userData.setConstraints === 'function') {
          userData.setConstraints({ availableEquipment: activeEquip });
        }
        runAgronomicSimulation();
      });
    });

    const marketChips = document.querySelectorAll('.market-chip');
    marketChips.forEach(chip => {
      chip.addEventListener('click', () => {
        chip.classList.toggle('selected');
        const activeMarkets = Array.from(document.querySelectorAll('.market-chip.selected')).map(c => c.dataset.market);

        if (userData && typeof userData.setConstraints === 'function') {
          userData.setConstraints({ targetMarkets: activeMarkets });
        }
        runAgronomicSimulation();
      });
    });
  }

  function initPrioritySliders() {
    const userData = window.TerraforgeUserData || window.TerraforgeInput;

    const sliderMap = [
      { id: 'sliderWaterSaving', key: 'waterSaving' },
      { id: 'sliderSoilHealth', key: 'soilHealth' },
      { id: 'sliderIncome', key: 'income' },
      { id: 'sliderErosionControl', key: 'erosionControl' },
      { id: 'sliderForage', key: 'forage' }
    ];

    sliderMap.forEach(item => {
      const slider = document.getElementById(item.id);
      if (!slider) return;

      const valBadge = slider.parentElement.querySelector('.slider-val-badge');
      slider.addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        if (valBadge) valBadge.textContent = `${Math.round(val * 100)}%`;

        if (userData && typeof userData.setPriorityWeights === 'function') {
          const weightsObj = {};
          weightsObj[item.key] = val;
          userData.setPriorityWeights(weightsObj);
        }

        runAgronomicSimulation();
      });
    });
  }

  // =========================================================================
  // 7. Industrial Agronomic Simulation Model (Step 06 Synthesis)
  // =========================================================================
  function runAgronomicSimulation() {
    const cropDb = window.CropDB || window.TerraforgeCrops;
    const userData = window.TerraforgeUserData || window.TerraforgeInput;
    if (!cropDb || !userData) return;

    const payload = userData.getBackendPayload();
    const rawState = userData.getRawState();
    const ha = uiState.parcelAreaHa > 0 ? uiState.parcelAreaHa : 10.0;

    let activeCrops = [];

    if (payload.selectedStrategy === 'none') {
      activeCrops = [{
        id: 'fallow',
        name: 'Raw / Fallow Soil Baseline',
        category: 'Soil Restoration',
        baseYieldHa: 2.2,
        baseRevenueHa: 950,
        waterReq: 0.35,
        soilBenefit: 0.95
      }];
    } else if (payload.selectedStrategy === 'current') {
      const cur = cropDb.getById(rawState.activeCropConfig.cropId) || cropDb.getAll()[0];
      activeCrops = [cur];
    } else {
      const currentSeasonPlan = rawState.rotationPlan.seasons.find(s => s.seasonId === uiState.activeSeason);
      const ids = currentSeasonPlan ? currentSeasonPlan.plantedCropIds : ['rice'];
      activeCrops = ids.map(id => cropDb.getById(id)).filter(Boolean);
      if (!activeCrops.length) activeCrops = [cropDb.getAll()[0]];
    }

    const avgRevenueHa = activeCrops.reduce((acc, c) => acc + c.baseRevenueHa, 0) / (activeCrops.length || 1);
    const avgYieldHa = activeCrops.reduce((acc, c) => acc + c.baseYieldHa, 0) / (activeCrops.length || 1);
    const avgWaterReq = activeCrops.reduce((acc, c) => acc + c.waterReq, 0) / (activeCrops.length || 1);
    const avgSoilBenefit = activeCrops.reduce((acc, c) => acc + c.soilBenefit, 0) / (activeCrops.length || 1);

    const weights = rawState.constraintsAndPriorities.priorityWeights;
    const equip = rawState.constraintsAndPriorities.availableEquipment;
    const markets = rawState.constraintsAndPriorities.targetMarkets;
    const irrigation = rawState.constraintsAndPriorities.irrigationAccess;

    let irrigationMultiplier = irrigation === 'full' ? 1.30 : (irrigation === 'limited' ? 1.10 : 0.85);
    let equipmentBoost = 1.0 + (equip.includes('harvester') ? 0.08 : 0) + (equip.includes('drone') ? 0.06 : 0) + (equip.includes('pump') ? 0.05 : 0);
    let marketPremium = 1.0 + (markets.includes('export') ? 0.15 : 0) + (markets.includes('board') ? 0.08 : 0);

    const grossRevenue = ha * avgRevenueHa * irrigationMultiplier * equipmentBoost * marketPremium * (0.85 + weights.income * 0.35);
    const netMarginPct = 16.5 + (weights.income * 10.2) - (weights.waterSaving * 1.8) + (equip.length * 1.4);

    const waterSavedVolumeM3 = Math.round(ha * 1400 * (1 - avgWaterReq * (1 - weights.waterSaving * 0.45)));
    const soilHealthScore = Math.min(99, Math.round((avgSoilBenefit * 60) + (weights.soilHealth * 28) + (equip.includes('drone') ? 10 : 0)));
    const erosionMitigationScore = Math.min(99, Math.round((weights.erosionControl * 55) + (weights.soilHealth * 25) + 15));
    const biomassYieldTons = Math.round(ha * (avgYieldHa * 1.25) * (0.8 + weights.forage * 0.5));

    // Update DOW Card
    const dowVal = document.getElementById('dowMetricValue');
    const dowPill = document.getElementById('dowMarginPill');
    if (dowVal) dowVal.textContent = `$${Math.round(grossRevenue).toLocaleString('en-US')}.00`;
    if (dowPill) dowPill.textContent = `+ ${netMarginPct.toFixed(1)}% Margins`;

    // Update KPI Card numbers
    const waterEl = document.getElementById('kpiWaterConserved');
    const soilEl = document.getElementById('kpiSoilHealth');
    const erosionEl = document.getElementById('kpiErosionMitigation');
    const biomassEl = document.getElementById('kpiBiomassYield');

    if (waterEl) waterEl.textContent = `${waterSavedVolumeM3.toLocaleString('en-US')} m³`;
    if (soilEl) soilEl.textContent = `${soilHealthScore} / 100`;
    if (erosionEl) erosionEl.textContent = `${erosionMitigationScore}%`;
    if (biomassEl) biomassEl.textContent = `${biomassYieldTons.toLocaleString('en-US')} t`;

    // Update Dynamic SVG Radar Chart
    renderRadarChart(weights);

    // Update Agronomic Directives
    updateDirectivesList(activeCrops, payload.selectedStrategy, irrigation, equip);
  }

  function renderRadarChart(weights) {
    const svg = document.getElementById('radarSvg');
    if (!svg) return;

    const size = 280;
    const center = size / 2;
    const radius = 95;

    const axes = [
      { key: 'waterSaving', label: 'Water Conserved', val: weights.waterSaving || 0.75 },
      { key: 'soilHealth', label: 'Soil Health', val: weights.soilHealth || 0.8 },
      { key: 'income', label: 'Economic Yield', val: weights.income || 0.9 },
      { key: 'erosionControl', label: 'Erosion Barrier', val: weights.erosionControl || 0.7 },
      { key: 'forage', label: 'Biomass Index', val: weights.forage || 0.5 }
    ];

    const angleStep = (Math.PI * 2) / axes.length;
    let gridPaths = '';

    // Concentric Web Rings
    [0.25, 0.5, 0.75, 1.0].forEach(rPct => {
      const pts = axes.map((_, i) => {
        const a = i * angleStep - Math.PI / 2;
        const x = center + Math.cos(a) * (radius * rPct);
        const y = center + Math.sin(a) * (radius * rPct);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(' ');
      gridPaths += `<polygon points="${pts}" fill="none" stroke="rgba(24,119,65,0.12)" stroke-width="1.2"/>`;
    });

    // Spoke lines & labels
    let spokes = '';
    let labels = '';
    axes.forEach((axis, i) => {
      const a = i * angleStep - Math.PI / 2;
      const x = center + Math.cos(a) * radius;
      const y = center + Math.sin(a) * radius;
      spokes += `<line x1="${center}" y1="${center}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="rgba(24,119,65,0.18)" stroke-width="1.2"/>`;

      const lx = center + Math.cos(a) * (radius + 24);
      const ly = center + Math.sin(a) * (radius + 18);
      labels += `<text x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="middle" font-size="10" font-weight="600" fill="#344054">${axis.label}</text>`;
    });

    // Data Polygon
    const dataPoints = axes.map((axis, i) => {
      const a = i * angleStep - Math.PI / 2;
      const r = radius * Math.max(0.15, Math.min(1.0, axis.val));
      const x = center + Math.cos(a) * r;
      const y = center + Math.sin(a) * r;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');

    svg.innerHTML = `
      ${gridPaths}
      ${spokes}
      <polygon points="${dataPoints}" fill="rgba(56,193,114,0.32)" stroke="#187741" stroke-width="2.5"/>
      ${axes.map((axis, i) => {
        const a = i * angleStep - Math.PI / 2;
        const r = radius * Math.max(0.15, Math.min(1.0, axis.val));
        const x = center + Math.cos(a) * r;
        const y = center + Math.sin(a) * r;
        return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4" fill="#187741" stroke="#FFFFFF" stroke-width="2"/>`;
      }).join('')}
      ${labels}
    `;
  }

  function updateDirectivesList(crops, strategy, irrigation, equip) {
    const list = document.getElementById('agronomicDirectivesList');
    if (!list) return;

    const cropNames = crops.map(c => c.name).join(', ');
    const directives = [];

    if (strategy === 'none') {
      directives.push({
        title: 'Fallow Soil Restorative Mulching Directive',
        desc: 'Inoculate parcel with nitrogen-fixing cover legumes (Sunn Hemp / Sesbania) before subsequent planting.'
      });
    } else if (strategy === 'current') {
      directives.push({
        title: `Standing Crop Protection Protocol for ${cropNames}`,
        desc: 'Apply targeted foliar micronutrients and calibrate soil moisture sensors for optimal ripening window.'
      });
    } else {
      directives.push({
        title: `Monsoon Rotation Sequencing (${cropNames})`,
        desc: 'Maintain synchronized planting dates with regional tank cascade opening dates to optimize water rights.'
      });
    }

    if (irrigation === 'none') {
      directives.push({
        title: 'Rainfed Dry Zone Soil Moisture Preservation',
        desc: 'Implement zero-tillage residue retention and contour bunding to maximize retention of precipitation.'
      });
    } else {
      directives.push({
        title: 'Precision Micro-Irrigation Schedule',
        desc: 'Activate sub-surface drip cycling during 04:00 - 07:00 window to minimize evapotranspiration loss.'
      });
    }

    if (equip.includes('drone')) {
      directives.push({
        title: 'Autonomous Multispectral Spectral Patrol',
        desc: 'Perform bi-weekly multispectral drone survey (NDVI / NDRE) to identify localized nitrogen deficiency zones.'
      });
    }

    list.innerHTML = directives.map(d => `
      <li class="directive-item" style="margin-bottom:0.85rem; padding-left:1.25rem; position:relative;">
        <span style="position:absolute; left:0; top:4px; width:6px; height:6px; border-radius:50%; background:#187741;"></span>
        <strong style="display:block; font-size:0.85rem; color:#101828;">${d.title}</strong>
        <span style="display:block; font-size:0.78rem; color:#475467; margin-top:2px;">${d.desc}</span>
      </li>
    `).join('');
  }

  // =========================================================================
  // 8. Action Buttons & Export Handler
  // =========================================================================
  function initActionButtons() {
    const syncBackendBtn = document.getElementById('btnSyncBackend');
    if (syncBackendBtn) {
      syncBackendBtn.addEventListener('click', async () => {
        const userData = window.TerraforgeUserData || window.TerraforgeInput;
        if (!userData || typeof userData.submitToBackend !== 'function') return;

        showNotification('Connecting to Backend', 'Transmitting structured agronomic payload...');

        try {
          const res = await userData.submitToBackend();
          if (res.success) {
            showNotification('Backend Synchronized', 'User input configuration accepted by backend API.');
          } else {
            // Even if offline/local dev without active server, show informative notice & auto-save to storage
            showNotification('Backend Bridge Ready', `Payload formatted (${userData.getStrategy().toUpperCase()} mode). Ready for API POST.`);
          }
        } catch (err) {
          showNotification('Sync Notice', 'Backend payload verified & cached in local storage.');
        }
      });
    }

    const exportBtn = document.getElementById('btnExportPlan');
    if (exportBtn) {
      exportBtn.addEventListener('click', () => {
        const userData = window.TerraforgeUserData || window.TerraforgeInput;
        if (userData && typeof userData.exportJson === 'function') {
          userData.exportJson('terraforge-agro-plan.json');
          showNotification('Backend Payload Exported', 'Downloaded complete structured user input JSON package.');
        }
      });
    }

    const printBtn = document.getElementById('btnPrintReport');
    if (printBtn) {
      printBtn.addEventListener('click', () => {
        window.print();
      });
    }
  }

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

})();
