const supabaseUrl = 'https://zvfngpoxwrgswnzytadh.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp2Zm5ncG94d3Jnc3duenl0YWRoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDAxNTIxNjMsImV4cCI6MjA1NTcyODE2M30.FNTCCMwi0QaKjOu8gtZsT5yQttUW8QiDDGXmzkn89QE';

async function loadSiteData() {
  try {
    const siteList = document.getElementById('site-list');
    const headers = {
      'apikey': supabaseKey,
      'Authorization': `Bearer ${supabaseKey}`,
      'Content-Type': 'application/json'
    };

    const response = await fetch(`${supabaseUrl}/rest/v1/public`, {
      method: 'GET',
      headers: headers
    });

    if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
    
    const data = await response.json();

    siteList.innerHTML = '';

    if (data && data.length > 0) {
      const configSite = data[0].data;

      for (const siteName in configSite) {
        const site = configSite[siteName];
        const siteItem = document.createElement('div');
        siteItem.className = 'site-item';

        const siteIcon = document.createElement('img');
        siteIcon.src = `https://t2.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url=${site.full_url}&size=128`;
        siteIcon.alt = `${siteName} icon`;
        siteIcon.onerror = function() {
          this.src = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 24 24" fill="none" stroke="%238c52ff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>';
        };

        const siteContent = document.createElement('div');
        siteContent.className = 'site-content';

        const siteTitle = document.createElement('h3');
        siteTitle.textContent = siteName;

        if (site.old_domain) {
          const oldDomain = document.createElement('p');
          oldDomain.className = 'old-domain';
          oldDomain.innerHTML = `<span class="label">Previous domain:</span> ${site.old_domain.replace(/^https?:\/\//, '')}`;
          siteContent.appendChild(oldDomain);
        }

        if (site.time_change) {
          const timeChange = document.createElement('p');
          timeChange.className = 'time-change';

          const changeDate = new Date(site.time_change);
          const dateString = isNaN(changeDate) ? site.time_change : changeDate.toLocaleDateString();
          timeChange.innerHTML = `<span class="label">Updated:</span> ${dateString}`;
          siteContent.appendChild(timeChange);
        }

        const siteLink = document.createElement('a');
        siteLink.href = site.full_url;
        siteLink.target = '_blank';
        siteLink.innerHTML = 'Visit <i class="fas fa-external-link-alt"></i>';
        siteLink.rel = 'noopener noreferrer';

        siteContent.appendChild(siteTitle);
        siteContent.appendChild(siteLink);
        siteItem.appendChild(siteIcon);
        siteItem.appendChild(siteContent);
        siteList.appendChild(siteItem);
      }
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

document.addEventListener('DOMContentLoaded', loadSiteData);
