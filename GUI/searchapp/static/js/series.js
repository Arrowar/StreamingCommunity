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
      
      episodeString = ranges.join(',');
    }
  }
  
  const inputField = document.getElementById(`selected_episodes_${sNum}`);
  if (inputField) {
    inputField.value = episodeString;
  }
}

export function initEpisodeSelection() {
  const checkboxes = document.querySelectorAll('.episode-checkbox');
  
  checkboxes.forEach(cb => {
    if (cb.checked) {
      updateSelectedEpisodes(cb.dataset.season);
    }
    
    cb.addEventListener('change', function() {
      updateSelectedEpisodes(this.dataset.season);
    });
  });
}

export function initFormValidation() {
  const forms = document.querySelectorAll('form[id^="form-season-"]');
  
  forms.forEach(form => {
    form.addEventListener('submit', function(e) {
      const seasonNumberInput = this.querySelector('input[name="season_number"]');
      if (!seasonNumberInput) return;
      
      const selectedEpisodesInput = this.querySelector('input[name="selected_episodes"]');
      if (selectedEpisodesInput && !selectedEpisodesInput.value.trim()) {
        e.preventDefault();
        alert('Seleziona almeno un episodio prima di scaricare.');
      }
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