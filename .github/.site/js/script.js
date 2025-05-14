document.documentElement.setAttribute('data-theme', 'dark');

function initGridControls() {
  const gridSize = document.getElementById('grid-size');
  const siteGrid = document.querySelector('.site-grid');
  
  gridSize.addEventListener('change', function() {
    switch(this.value) {
      case 'small':
        siteGrid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(200px, 1fr))';
        break;
      case 'medium':
        siteGrid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(300px, 1fr))';
        break;
      case 'large':
        siteGrid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(400px, 1fr))';
        break;
    }
    localStorage.setItem('preferredGridSize', this.value);
  });

  const savedSize = localStorage.getItem('preferredGridSize');
  if (savedSize) {
    gridSize.value = savedSize;
    gridSize.dispatchEvent(new Event('change'));
  }
}

async function checkSiteStatus(url) {
  try {
    console.log(`Checking status for: ${url}`);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const response = await fetch(url, { 
      method: 'HEAD',
      mode: 'no-cors',
      signal: controller.signal,
      headers: {
        'Accept': 'text/html',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/133.0.0.0'
      }
    });

    clearTimeout(timeoutId);

    const isOnline = response.type === 'opaque';
    console.log(`Site ${url} is ${isOnline ? 'online' : 'offline'} (Type: ${response.type})`);
    return isOnline;
  } catch (error) {
    console.log(`Error checking ${url}:`, error.message);
    return false;
  }
}

const supabaseUrl = 'https://zvfngpoxwrgswnzytadh.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp2Zm5ncG94d3Jnc3duenl0YWRoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDAxNTIxNjMsImV4cCI6MjA1NTcyODE2M30.FNTCCMwi0QaKjOu8gtZsT5yQttUW8QiDDGXmzkn89QE';

async function loadSiteData() {
  try {
    console.log('Starting to load site data...');
    const siteList = document.getElementById('site-list');
    siteList.innerHTML = '<div class="loader"></div>';

    const headers = {
      'accept': '*/*',
      'accept-language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
      'apikey': supabaseKey,
      'authorization': `Bearer ${supabaseKey}`,
      'content-type': 'application/json',
      'cache-control': 'no-cache',
      'pragma': 'no-cache',
      'range': '0-9'
    };

    console.log('Fetching from Supabase with headers:', headers);
    const response = await fetch(`${supabaseUrl}/rest/v1/public?select=*`, {
      method: 'GET',
      headers: headers
    });

    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
    
    const data = await response.json();
    
    siteList.innerHTML = '';    if (data && data.length > 0) {
      console.log('Raw data from Supabase:', data);
      const configSite = data[0].data;
      console.log('Parsed config site:', configSite);
      let totalSites = Object.keys(configSite).length;
      let latestUpdate = new Date(0);
      
      document.getElementById('sites-count').textContent = totalSites;

      for (const siteName in configSite) {
        const site = configSite[siteName];
        const siteItem = document.createElement('div');
        siteItem.className = 'site-item';
        siteItem.style.cursor = 'pointer';

        // Add status indicator
        const statusDot = document.createElement('div');
        statusDot.className = 'site-status';
        const isOnline = await checkSiteStatus(site.full_url);
        if (!isOnline) statusDot.classList.add('offline');
        siteItem.appendChild(statusDot);

        // Update latest update time
        const updateTime = new Date(site.time_change);
        if (updateTime > latestUpdate) {
          latestUpdate = updateTime;
        }

        const siteInfo = document.createElement('div');
        siteInfo.className = 'site-info';
        if (site.time_change) {
          const updateDate = new Date(site.time_change);
          const formattedDate = updateDate.toLocaleDateString('it-IT', { 
            year: 'numeric', 
            month: '2-digit', 
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
          });
          const lastUpdate = document.createElement('span');
          lastUpdate.className = 'last-update';
          lastUpdate.innerHTML = `<i class="fas fa-clock"></i> ${formattedDate}`;
          siteInfo.appendChild(lastUpdate);
        }

        if (site.old_domain) {
          const oldDomain = document.createElement('span');
          oldDomain.className = 'old-domain';
          oldDomain.innerHTML = `<i class="fas fa-history"></i> ${site.old_domain}`;
          siteInfo.appendChild(oldDomain);
        }        siteItem.addEventListener('click', function() {
          window.open(site.full_url, '_blank', 'noopener,noreferrer');
        });

        const siteIcon = document.createElement('img');
        siteIcon.src = `https://t2.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=${site.full_url}&size=128`;
        siteIcon.alt = `${siteName} icon`;
        siteIcon.onerror = function() {
          this.src = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="%238c52ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>';
        };

        const siteTitle = document.createElement('h3');
        siteTitle.textContent = siteName;
        siteItem.appendChild(siteIcon);
        siteItem.appendChild(siteTitle);
        siteItem.appendChild(siteInfo);
        siteList.appendChild(siteItem);
      }

      const formattedDate = latestUpdate.toLocaleDateString('it-IT', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
      document.getElementById('last-update-time').textContent = formattedDate;
    } else {
      siteList.innerHTML = '<div class="no-sites">No sites available</div>';
    }
  } catch (error) {
    console.error('Errore:', error);
    siteList.innerHTML = `
      <div class="error-message">
        <p>Errore nel caricamento</p>
        <button onclick="loadSiteData()" class="retry-button">Riprova</button>
      </div>
    `;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadSiteData();
});