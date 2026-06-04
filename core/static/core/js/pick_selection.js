(function () {
  function syncPicked(card) {
    var input = card.querySelector('.pick-select-input');
    if (!input) return;
    card.classList.toggle('is-picked', input.checked);
  }

  function initForm(form) {
    form.querySelectorAll('.pick-select-card').forEach(syncPicked);
    form.addEventListener('change', function (e) {
      var card = e.target.closest('.pick-select-card');
      if (card) {
        syncPicked(card);
      }
      if (e.target.classList.contains('pick-select-input') && e.target.type === 'radio') {
        form.querySelectorAll('.pick-select-card').forEach(function (c) {
          var inp = c.querySelector('.pick-select-input[type="radio"]');
          if (inp && inp.name === e.target.name) {
            syncPicked(c);
          }
        });
      }
    });
  }

  document.querySelectorAll('.pick-courses-form, .pick-group-form, .pick-setup-form').forEach(initForm);
})();
