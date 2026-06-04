(function () {
  document.querySelectorAll('[data-image-upload]').forEach(function (root) {
    var input = root.querySelector('.image-upload__input, .avatar-upload__input');
    var img = root.querySelector('[data-image-preview-img]');
    var placeholder = root.querySelector('[data-image-placeholder]');
    if (!input || !img) return;

    var objectUrl = null;

    function clearObjectUrl() {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
        objectUrl = null;
      }
    }

    input.addEventListener('change', function () {
      clearObjectUrl();
      var file = input.files && input.files[0];
      if (!file || !file.type.startsWith('image/')) {
        return;
      }
      objectUrl = URL.createObjectURL(file);
      img.src = objectUrl;
      img.hidden = false;
      if (placeholder) {
        placeholder.hidden = true;
      }
    });
  });
})();
