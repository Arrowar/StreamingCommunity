/**
 * Series detail page - Episode selection logic
 */


export function selectAllEpisodes(seasonNumber) {
  const checkboxes = document.querySelectorAll(
    `input.episode-checkbox[data-season="${seasonNumber}"]`
  );
  checkboxes.forEach(cb => cb.checked = true);
  updateSelectedEpisodes(seasonNumber);
}

export function deselectAllEpisodes(seasonNumber) {
  const checkboxes = document.querySelectorAll(
    `input.episode-checkbox[data-season="${seasonNumber}"]`
  );
  checkboxes.forEach(cb => cb.checked = false);
  updateSelectedEpisodes(seasonNumber);
}

export function updateSelectedEpisodes(seasonNumber) {
  const sNum = String(seasonNumber);
  const checkboxes = document.querySelectorAll(
    `input.episode-checkbox[data-season="${sNum}"]:checked`
  );
  const episodes = Array.from(checkboxes).map(cb => cb.value);
  
  let episodeString = '';
  
  if (episodes.length > 0) {

    // Attempt to parse as integers for range calculation
    const numericEpisodes = episodes
      .map(val => parseInt(val, 10))
      .filter(num => !isNaN(num))
      .sort((a, b) => a - b);
    
    if (numericEpisodes.length === 0) {

      // Fallback for non-numeric episode "numbers" (e.g. dates)
      episodeString = episodes.join(',');
    } else {
      const ranges = [];
      let start = numericEpisodes[0];
      let end = numericEpisodes[0];
      
      for (let i = 1; i <= numericEpisodes.length; i++) {
        if (i < numericEpisodes.length && numericEpisodes[i] === end + 1) {
          end = numericEpisodes[i];
        } else {
          if (start === end) {
            ranges.push(String(start));
          } else if (end === start + 1) {
            ranges.push(String(start));
            ranges.push(String(end));
          } else {
            ranges.push(`${start}-${end}`);
          }
          
          if (i < numericEpisodes.length) {
            start = numericEpisodes[i];
            end = numericEpisodes[i];
          }
        }
      }
      
      // If we have mixed numeric and non-numeric (unlikely but possible), 
      // we only used numeric for ranges. Let's keep it simple for now.
      episodeString = ranges.join(',');
    }
  }
  
  const inputField = document.getElementById(`selected_episodes_${sNum}`);
  if (inputField) {
    inputField.value = episodeString;
    console.log(`[Series] Set hidden input selected_episodes_${sNum} to: "${episodeString}"`);
  } else {
    console.error(`[Series] Could not find hidden input selected_episodes_${sNum}`);
  }
}

export function initEpisodeSelection() {
  const checkboxes = document.querySelectorAll('.episode-checkbox');
  
  checkboxes.forEach(cb => {
    if (cb.checked) {
      updateSelectedEpisodes(cb.dataset.season);
    }
    
    cb.addEventListener('change', function() {
      console.log(`[Series] Checkbox change detected for season ${this.dataset.season} episode ${this.value}`);
      updateSelectedEpisodes(this.dataset.season);
    });
  });
}

export function initFormValidation() {
  const forms = document.querySelectorAll('form[id^="form-season-"]');
  
  forms.forEach(form => {
    form.addEventListener('submit', function(e) {
      const downloadTypeInput = this.querySelector('input[name="download_type"]');
      if (downloadTypeInput && downloadTypeInput.value !== 'episodes') {
        return; // Non validiamo se scarichiamo la stagione completa
      }

      const seasonNumberInput = this.querySelector('input[name="season"]');
      if (!seasonNumberInput) return;

      const seasonNumber = seasonNumberInput.value;
      const episodesInput = document.getElementById(`selected_episodes_${seasonNumber}`);
      const selectedEpisodes = episodesInput ? episodesInput.value : '';
      
      console.log(`[Series] Form submission for season ${seasonNumber}. Selected: "${selectedEpisodes}"`);
    });
  });
}

export function init() {
  initEpisodeSelection();
  initFormValidation();
}

if (typeof window !== 'undefined') {
  window.selectAllEpisodes = selectAllEpisodes;
  window.deselectAllEpisodes = deselectAllEpisodes;
}