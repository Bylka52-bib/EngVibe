(function () {
  document.querySelectorAll('[data-role-select]').forEach(function (wrap) {
    var native = wrap.querySelector('.role-select-native');
    var trigger = wrap.querySelector('.role-select__trigger');
    var list = wrap.querySelector('.role-select__list');
    var valueEl = wrap.querySelector('.role-select__value');
    var options = wrap.querySelectorAll('.role-select__option');

    if (!native || !trigger || !list || !valueEl) return;

    function closeSelect() {
      wrap.classList.remove('is-open');
      trigger.setAttribute('aria-expanded', 'false');
      list.hidden = true;
    }

    function openSelect() {
      wrap.classList.add('is-open');
      trigger.setAttribute('aria-expanded', 'true');
      list.hidden = false;
    }

    function toggleSelect() {
      if (wrap.classList.contains('is-open')) {
        closeSelect();
      } else {
        openSelect();
      }
    }

    function setValue(value, label) {
      native.value = value;
      valueEl.textContent = label;
      options.forEach(function (option) {
        var selected = option.dataset.value === value;
        option.classList.toggle('is-selected', selected);
        option.setAttribute('aria-selected', selected ? 'true' : 'false');
      });
      native.dispatchEvent(new Event('change', { bubbles: true }));
    }

    trigger.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopPropagation();
      toggleSelect();
    });

    options.forEach(function (option) {
      option.addEventListener('click', function (event) {
        event.stopPropagation();
        setValue(option.dataset.value, option.textContent.trim());
        closeSelect();
        trigger.focus();
      });
    });

    document.addEventListener('click', function (event) {
      if (!wrap.contains(event.target)) {
        closeSelect();
      }
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        closeSelect();
        if (document.activeElement === trigger || wrap.contains(document.activeElement)) {
          trigger.focus();
        }
      }
    });

    trigger.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleSelect();
      } else if (event.key === 'ArrowDown') {
        event.preventDefault();
        if (!wrap.classList.contains('is-open')) {
          openSelect();
        }
        var first = list.querySelector('.role-select__option');
        if (first) first.focus();
      }
    });

    options.forEach(function (option) {
      option.tabIndex = -1;
      option.addEventListener('keydown', function (event) {
        var items = Array.prototype.slice.call(options);
        var index = items.indexOf(option);

        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          setValue(option.dataset.value, option.textContent.trim());
          closeSelect();
          trigger.focus();
        } else if (event.key === 'ArrowDown') {
          event.preventDefault();
          var next = items[index + 1] || items[0];
          next.focus();
        } else if (event.key === 'ArrowUp') {
          event.preventDefault();
          var prev = items[index - 1] || items[items.length - 1];
          prev.focus();
        } else if (event.key === 'Escape') {
          event.preventDefault();
          closeSelect();
          trigger.focus();
        }
      });
    });
  });

  document.querySelectorAll('[data-multi-select]').forEach(function (wrap) {
    var trigger = wrap.querySelector('.role-select__trigger');
    var list = wrap.querySelector('.role-select__list');
    var display = wrap.querySelector('[data-multi-select-display]');
    var options = wrap.querySelectorAll('.role-select__option');
    var placeholder = wrap.dataset.placeholder || 'Выберите';

    if (!trigger || !list || !display) return;

    function closeSelect() {
      wrap.classList.remove('is-open');
      trigger.setAttribute('aria-expanded', 'false');
      list.hidden = true;
    }

    function openSelect() {
      wrap.classList.add('is-open');
      trigger.setAttribute('aria-expanded', 'true');
      list.hidden = false;
    }

    function toggleSelect() {
      if (wrap.classList.contains('is-open')) {
        closeSelect();
      } else {
        openSelect();
      }
    }

    function syncOption(option, checked) {
      option.classList.toggle('is-selected', checked);
      option.setAttribute('aria-selected', checked ? 'true' : 'false');
    }

    function updateDisplay() {
      var labels = [];
      options.forEach(function (option) {
        var cb = document.getElementById(option.dataset.checkboxId);
        if (cb && cb.checked) {
          labels.push(option.dataset.label || option.textContent.trim());
        }
      });

      if (!labels.length) {
        display.textContent = placeholder;
      } else if (labels.length <= 2) {
        display.textContent = labels.join(', ');
      } else {
        display.textContent = 'Выбрано: ' + labels.length;
      }
    }

    function toggleOption(option) {
      var cb = document.getElementById(option.dataset.checkboxId);
      if (!cb) return;
      cb.checked = !cb.checked;
      syncOption(option, cb.checked);
      updateDisplay();
      cb.dispatchEvent(new Event('change', { bubbles: true }));
    }

    options.forEach(function (option) {
      var cb = document.getElementById(option.dataset.checkboxId);
      if (cb) {
        syncOption(option, cb.checked);
      }
    });
    updateDisplay();

    trigger.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopPropagation();
      toggleSelect();
    });

    options.forEach(function (option) {
      option.addEventListener('click', function (event) {
        event.stopPropagation();
        toggleOption(option);
      });

      option.tabIndex = -1;
      option.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          toggleOption(option);
        } else if (event.key === 'Escape') {
          event.preventDefault();
          closeSelect();
          trigger.focus();
        }
      });
    });

    document.addEventListener('click', function (event) {
      if (!wrap.contains(event.target)) {
        closeSelect();
      }
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && wrap.classList.contains('is-open')) {
        closeSelect();
        trigger.focus();
      }
    });

    trigger.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleSelect();
      } else if (event.key === 'ArrowDown') {
        event.preventDefault();
        if (!wrap.classList.contains('is-open')) {
          openSelect();
        }
        var first = list.querySelector('.role-select__option');
        if (first) first.focus();
      }
    });
  });
})();
