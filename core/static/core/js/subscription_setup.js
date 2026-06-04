(function () {
  var cfg = window.__subscriptionSetup || {};
  var maxCourses = cfg.maxCourses || 0;
  var form = document.getElementById('subscription-setup-form');
  if (!form) return;

  var modeInput = document.getElementById('choice-mode-input');
  var groupSection = document.getElementById('setup-group-section');
  var coursesSection = document.getElementById('setup-courses-section');
  var countEl = document.getElementById('courses-picked-count');

  function groupRadios() {
    return form.querySelectorAll('input[name="group_id"]');
  }

  function courseChecks() {
    return form.querySelectorAll('input[name="course_ids"]');
  }

  function syncCard(input) {
    var card = input.closest('.pick-select-card');
    if (!card) return;
    card.classList.toggle('is-picked', input.checked);
  }

  function clearGroups() {
    groupRadios().forEach(function (r) {
      r.checked = false;
      syncCard(r);
    });
    if (groupSection) {
      groupSection.classList.remove('is-dimmed');
    }
  }

  function clearCourses() {
    courseChecks().forEach(function (c) {
      c.checked = false;
      syncCard(c);
    });
    updateCourseCount();
    if (coursesSection) {
      coursesSection.classList.remove('is-dimmed');
    }
  }

  function updateCourseCount() {
    if (!countEl) return;
    var n = form.querySelectorAll('input[name="course_ids"]:checked').length;
    countEl.textContent = String(n);
  }

  function dimSection(section, dim) {
    if (!section) return;
    section.classList.toggle('is-dimmed', dim);
  }

  form.querySelectorAll('.pick-select-input').forEach(syncCard);

  groupRadios().forEach(function (radio) {
    radio.addEventListener('change', function () {
      if (radio.checked) {
        clearCourses();
        dimSection(coursesSection, true);
        dimSection(groupSection, false);
        groupRadios().forEach(syncCard);
      }
    });
  });

  courseChecks().forEach(function (box) {
    box.addEventListener('change', function () {
      if (box.checked) {
        clearGroups();
        dimSection(groupSection, true);
        dimSection(coursesSection, false);
      }
      var checked = form.querySelectorAll('input[name="course_ids"]:checked');
      if (checked.length > maxCourses) {
        box.checked = false;
        syncCard(box);
        alert('Можно выбрать не более ' + maxCourses + ' курсов.');
      }
      updateCourseCount();
      courseChecks().forEach(syncCard);
      if (!form.querySelector('input[name="course_ids"]:checked')) {
        dimSection(groupSection, false);
      }
    });
  });

  updateCourseCount();

  form.addEventListener('submit', function (e) {
    var checkedCourses = form.querySelectorAll('input[name="course_ids"]:checked');
    var checkedGroup = form.querySelector('input[name="group_id"]:checked');

    if (checkedCourses.length > 0) {
      if (maxCourses && checkedCourses.length !== maxCourses) {
        e.preventDefault();
        var word = maxCourses === 1 ? 'курс' : (maxCourses < 5 ? 'курса' : 'курсов');
        alert('Выберите ' + maxCourses + ' ' + word + '.');
        return;
      }
      if (modeInput) modeInput.value = 'courses';
      return;
    }

    if (checkedGroup) {
      if (modeInput) modeInput.value = 'group';
      return;
    }

    e.preventDefault();
    alert('Выберите группу курсов или отметьте нужное число курсов.');
  });
})();
