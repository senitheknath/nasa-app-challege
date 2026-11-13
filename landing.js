/**
 * TERRAFORGE AGRO | Landing Page Search & Validation Controller
 */

(function () {
  'use strict';

  // Comprehensive Country Database (Clean names without raw 2-letter codes)
  const ALL_COUNTRIES = [
    { code: 'AF', name: 'Afghanistan', supported: false },
    { code: 'AL', name: 'Albania', supported: false },
    { code: 'DZ', name: 'Algeria', supported: false },
    { code: 'AR', name: 'Argentina', supported: false },
    { code: 'AU', name: 'Australia', supported: false },
    { code: 'AT', name: 'Austria', supported: false },
    { code: 'BD', name: 'Bangladesh', supported: false },
    { code: 'BE', name: 'Belgium', supported: false },
    { code: 'BR', name: 'Brazil', supported: false },
    { code: 'BG', name: 'Bulgaria', supported: false },
    { code: 'KH', name: 'Cambodia', supported: false },
    { code: 'CA', name: 'Canada', supported: false },
    { code: 'CL', name: 'Chile', supported: false },
    { code: 'CN', name: 'China', supported: false },
    { code: 'CO', name: 'Colombia', supported: false },
    { code: 'CR', name: 'Costa Rica', supported: false },
    { code: 'HR', name: 'Croatia', supported: false },
    { code: 'CZ', name: 'Czech Republic', supported: false },
    { code: 'DK', name: 'Denmark', supported: false },
    { code: 'EC', name: 'Ecuador', supported: false },
    { code: 'EG', name: 'Egypt', supported: false },
    { code: 'ET', name: 'Ethiopia', supported: false },
    { code: 'FI', name: 'Finland', supported: false },
    { code: 'FR', name: 'France', supported: false },
    { code: 'DE', name: 'Germany', supported: false },
    { code: 'GH', name: 'Ghana', supported: false },
    { code: 'GR', name: 'Greece', supported: false },
    { code: 'GT', name: 'Guatemala', supported: false },
    { code: 'HU', name: 'Hungary', supported: false },
    { code: 'IN', name: 'India', supported: false },
    { code: 'ID', name: 'Indonesia', supported: false },
    { code: 'IE', name: 'Ireland', supported: false },
    { code: 'IL', name: 'Israel', supported: false },
    { code: 'IT', name: 'Italy', supported: false },
    { code: 'JP', name: 'Japan', supported: false },
    { code: 'JO', name: 'Jordan', supported: false },
    { code: 'KZ', name: 'Kazakhstan', supported: false },
    { code: 'KE', name: 'Kenya', supported: false },
    { code: 'MY', name: 'Malaysia', supported: false },
    { code: 'MX', name: 'Mexico', supported: false },
    { code: 'MA', name: 'Morocco', supported: false },
    { code: 'MM', name: 'Myanmar', supported: false },
    { code: 'NP', name: 'Nepal', supported: false },
    { code: 'NL', name: 'Netherlands', supported: false },
    { code: 'NZ', name: 'New Zealand', supported: false },
    { code: 'NG', name: 'Nigeria', supported: false },
    { code: 'NO', name: 'Norway', supported: false },
    { code: 'PK', name: 'Pakistan', supported: false },
    { code: 'PA', name: 'Panama', supported: false },
    { code: 'PE', name: 'Peru', supported: false },
    { code: 'PH', name: 'Philippines', supported: false },
    { code: 'PL', name: 'Poland', supported: false },
    { code: 'PT', name: 'Portugal', supported: false },
    { code: 'RO', name: 'Romania', supported: false },
    { code: 'SA', name: 'Saudi Arabia', supported: false },
    { code: 'SG', name: 'Singapore', supported: false },
    { code: 'ZA', name: 'South Africa', supported: false },
    { code: 'KR', name: 'South Korea', supported: false },
    { code: 'ES', name: 'Spain', supported: false },
    { code: 'LK', name: 'Sri Lanka', supported: true }, // The ONLY supported country
    { code: 'SE', name: 'Sweden', supported: false },
    { code: 'CH', name: 'Switzerland', supported: false },
    { code: 'TW', name: 'Taiwan', supported: false },
    { code: 'TZ', name: 'Tanzania', supported: false },
    { code: 'TH', name: 'Thailand', supported: false },
    { code: 'TR', name: 'Turkey', supported: false },
    { code: 'UG', name: 'Uganda', supported: false },
    { code: 'UA', name: 'Ukraine', supported: false },
    { code: 'AE', name: 'United Arab Emirates', supported: false },
    { code: 'GB', name: 'United Kingdom', supported: false },
    { code: 'US', name: 'United States', supported: false },
    { code: 'UY', name: 'Uruguay', supported: false },
    { code: 'UZ', name: 'Uzbekistan', supported: false },
    { code: 'VN', name: 'Vietnam', supported: false },
    { code: 'ZW', name: 'Zimbabwe', supported: false }
  ];

  // Strictly sort alphabetically A to Z
  ALL_COUNTRIES.sort((a, b) => a.name.localeCompare(b.name));

  let selectedCountry = null;

  document.addEventListener('DOMContentLoaded', () => {
    initHighlightedSearch();
  });

  function initHighlightedSearch() {
    const searchInput = document.getElementById('landingCountrySearchInput');
    const dropdown = document.getElementById('landingCountryDropdown');
    const searchBtn = document.getElementById('landingSearchBtn');

    if (!searchInput || !dropdown) return;

    // Render initial alphabetical dropdown
    renderDropdownItems(ALL_COUNTRIES);

    searchInput.addEventListener('focus', () => {
      dropdown.classList.add('open');
    });

    searchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase().trim();
      const filtered = ALL_COUNTRIES.filter(c => 
        c.name.toLowerCase().includes(q)
      );
      renderDropdownItems(filtered);
      dropdown.classList.add('open');
    });

    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        const q = searchInput.value.toLowerCase().trim();
        const match = ALL_COUNTRIES.find(c => 
          c.name.toLowerCase().includes(q)
        );
        if (match) {
          handleCountrySelect(match);
          dropdown.classList.remove('open');
        }
      }
    });

    if (searchBtn) {
      searchBtn.addEventListener('click', () => {
        const q = searchInput.value.toLowerCase().trim();
        const match = ALL_COUNTRIES.find(c => 
          c.name.toLowerCase().includes(q)
        );
        if (match) {
          handleCountrySelect(match);
          dropdown.classList.remove('open');
        } else {
          dropdown.classList.add('open');
        }
      });
    }

    document.addEventListener('click', (e) => {
      if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.classList.remove('open');
      }
    });
  }

  function renderDropdownItems(countries) {
    const dropdown = document.getElementById('landingCountryDropdown');
    if (!dropdown) return;
    dropdown.innerHTML = '';

    if (countries.length === 0) {
      dropdown.innerHTML = '<div style="padding: 0.8rem 1rem; font-size: 0.85rem; color: #667085;">No country found</div>';
      return;
    }

    countries.forEach(c => {
      const item = document.createElement('div');
      item.className = 'country-option-item';
      if (selectedCountry && c.code === selectedCountry.code) {
        item.classList.add('selected');
      }

      // Clean country name only (NO LK, US, AU raw prefixes!)
      item.innerHTML = `
        <div style="display:flex; align-items:center; gap:0.5rem;">
          <span style="font-weight:600; color:var(--text-primary); font-size:0.92rem;">${c.name}</span>
        </div>
        <span style="font-size: 0.72rem; ${c.supported ? 'color:#187741; font-weight:700;' : 'color:#667085;'}">
          ${c.supported ? 'Online • Active Grid' : 'Not Detected'}
        </span>
      `;

      item.addEventListener('click', () => {
        handleCountrySelect(c);
        dropdown.classList.remove('open');
      });

      dropdown.appendChild(item);
    });
  }

  function handleCountrySelect(country) {
    selectedCountry = country;
    const searchInput = document.getElementById('landingCountrySearchInput');
    if (searchInput) {
      // Pure country name (NO LK, US, AU text)
      searchInput.value = country.name;
    }

    const feedbackBox = document.getElementById('landingFeedbackBox');
    if (!feedbackBox) return;

    if (country.supported && country.code === 'LK') {
      // Sri Lanka Validated -> Continue Button Appears
      feedbackBox.innerHTML = `
        <div class="compact-feedback-card available">
          <div class="compact-feedback-left">
            <div class="compact-feedback-icon">✓</div>
            <div>
              <div class="compact-feedback-title">Sri Lanka Agro Grid Online</div>
            </div>
          </div>
          <div>
            <a href="input.html" class="btn-proceed-territory" id="btnContinueToInput">
              <span>Continue to Area Selection</span>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <line x1="5" y1="12" x2="19" y2="12"></line>
                <polyline points="12 5 19 12 12 19"></polyline>
              </svg>
            </a>
          </div>
        </div>
      `;

      try {
        localStorage.setItem('terraforge_selected_country', JSON.stringify(country));
      } catch (e) {}

    } else {
      // Other country -> Local Data Not Detected
      feedbackBox.innerHTML = `
        <div class="compact-feedback-card not-detected">
          <div class="compact-feedback-left">
            <div class="compact-feedback-icon">!</div>
            <div>
              <div class="compact-feedback-title">Local Data Not Detected for ${country.name}</div>
            </div>
          </div>
          <div>
          </div>
        </div>
      `;

      const switchBtn = document.getElementById('btnSwitchToSriLanka');
      if (switchBtn) {
        switchBtn.addEventListener('click', () => {
          const lk = ALL_COUNTRIES.find(c => c.code === 'LK');
          if (lk) handleCountrySelect(lk);
        });
      }
    }
  }

})();
