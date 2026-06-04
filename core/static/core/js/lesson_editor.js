(function () {
  var textarea = document.getElementById('id_material');
  if (!textarea || typeof tinymce === 'undefined') return;

  var uploadUrl = textarea.dataset.uploadUrl;
  var csrfToken = textarea.dataset.csrfToken;

  function normalizeLessonHtml(html) {
    if (!html) return html;
    var wrap = document.createElement('div');
    wrap.innerHTML = html;
    wrap.querySelectorAll('[data-mce-style]').forEach(function (el) {
      var mce = el.getAttribute('data-mce-style') || '';
      var style = el.getAttribute('style') || '';
      var combined = [style.replace(/;\s*$/, ''), mce].filter(Boolean).join('; ');
      combined = combined.replace(/\bbackground\s*:\s*([^;]+)/gi, 'background-color: $1');
      el.setAttribute('style', combined);
      el.removeAttribute('data-mce-style');
    });
    wrap.querySelectorAll('[style]').forEach(function (el) {
      var s = el.getAttribute('style') || '';
      s = s.replace(/\bbackground\s*:\s*([^;]+)/gi, 'background-color: $1');
      el.setAttribute('style', s);
    });
    return wrap.innerHTML;
  }

  tinymce.init({
    selector: '#id_material',
    language: 'ru',
    height: 560,
    min_height: 480,
    autoresize_bottom_margin: 40,
    menubar: false,
    statusbar: false,
    elementpath: false,
    plugins: 'lists link image table media code autoresize fullscreen',
    toolbar: [
      'undo redo | blocks | bold italic underline | alignleft aligncenter alignright',
      'bullist numlist | link image table tablecellprops tablecellbackgroundcolor | media',
      'lessonlayoutleft lessonlayoutright lessonlayouttable | lessoncallout lessonbutton | fullscreen code removeformat',
    ].join(' | '),
    block_formats: 'Абзац=p; Заголовок 2=h2; Заголовок 3=h3; Заголовок 4=h4',
    content_css: window.__lessonEditorContentCss || '/static/core/css/lesson_content.css',
    body_class: 'lesson-material-content',
    content_style: [
      'body{font-family:Montserrat,sans-serif;font-size:16px;line-height:1.65;color:#191a23;padding:12px 16px;}',
      '.mce-content-body[data-mce-placeholder]:not(.mce-visualblocks)::before{color:rgba(25,26,35,.45);}',
    ].join(''),
    branding: false,
    promotion: false,
    license_key: 'gpl',
    relative_urls: false,
    convert_urls: true,
    extended_valid_elements: [
      'iframe[src|title|allow|allowfullscreen|referrerpolicy|loading|class]',
      'td[style|bgcolor|colspan|rowspan|class]',
      'th[style|bgcolor|colspan|rowspan|class]',
      'tr[style|class]',
      'table[style|border|cellpadding|cellspacing|class]',
      'img[class|style|src|alt|width|height]',
      'div[class|style]',
    ].join(','),
    valid_children: '+div[iframe|div|p|ul|ol|table|img]',
    image_class_list: [
      { title: 'По центру', value: 'lesson-align-center' },
      { title: 'Слева (текст обтекает)', value: 'lesson-align-left' },
      { title: 'Справа (текст обтекает)', value: 'lesson-align-right' },
    ],
    table_toolbar: 'tableprops tabledelete | tableinsertrowbefore tableinsertrowafter tabledeleterow | tableinsertcolbefore tableinsertcolafter tabledeletecol | tablecellprops tablecellbackgroundcolor tablecellbordercolor',
    table_appearance_options: true,
    table_advtab: true,
    table_cell_advtab: true,
    table_row_advtab: true,
    table_resize_bars: true,
    table_default_attributes: { border: '0' },
    table_default_styles: {},
    table_responsive_width: false,
    object_resizing: true,
    resize_img_proportional: true,
    media_live_embeds: true,
    images_upload_url: uploadUrl,
    images_upload_credentials: true,
    automatic_uploads: true,
    file_picker_types: 'image',
    paste_data_images: false,
    formats: {
      alignleft: { selector: 'img', classes: 'lesson-align-left' },
      alignright: { selector: 'img', classes: 'lesson-align-right' },
      aligncenter: { selector: 'img', classes: 'lesson-align-center' },
    },
    media_url_resolver: function (data, resolve) {
      if (data.url && (data.url.indexOf('youtube.com') !== -1 || data.url.indexOf('youtu.be') !== -1)) {
        resolve({ html: '<div class="lesson-video-wrap">' + data.html + '</div>' });
        return;
      }
      resolve({ html: data.html });
    },
    setup: function (editor) {
      function insertMediaRow(imgRight) {
        var rowClass = imgRight ? 'lesson-media-row--img-right' : 'lesson-media-row--img-left';
        editor.insertContent(
          '<div class="lesson-media-row ' + rowClass + '">' +
            '<div class="lesson-media-row__body">' +
              '<p><strong>Текст:</strong> опишите материал в этой колонке. Текст будет рядом с изображением или таблицей.</p>' +
            '</div>' +
            '<div class="lesson-media-row__media">' +
              '<p><img loading="lazy" src="' + (window.__lessonPlaceholderImg || '') + '" alt="Замените на своё изображение" style="max-width:100%;" /></p>' +
            '</div>' +
          '</div><p></p>'
        );
      }

      editor.ui.registry.addButton('lessonlayoutright', {
        text: 'Текст + медиа справа',
        tooltip: 'Текст слева, картинка или таблица справа',
        onAction: function () { insertMediaRow(true); },
      });

      editor.ui.registry.addButton('lessonlayoutleft', {
        text: 'Медиа + текст',
        tooltip: 'Картинка или таблица слева, текст справа',
        onAction: function () { insertMediaRow(false); },
      });

      editor.ui.registry.addButton('lessonlayouttable', {
        text: 'Текст + таблица',
        tooltip: 'Блок: текст слева, таблица справа',
        onAction: function () {
          editor.insertContent(
            '<div class="lesson-media-row lesson-media-row--img-right">' +
              '<div class="lesson-media-row__body"><p>Текст рядом с таблицей.</p></div>' +
              '<div class="lesson-media-row__media lesson-table-float-right">' +
                '<table><tbody>' +
                  '<tr><th style="background-color:#ffe7ea;">A</th><th>B</th></tr>' +
                  '<tr><td>1</td><td>2</td></tr>' +
                '</tbody></table>' +
              '</div>' +
            '</div><p></p>'
          );
        },
      });

      editor.ui.registry.addButton('lessoncallout', {
        text: 'Выноска',
        onAction: function () {
          editor.insertContent(
            '<div class="lesson-callout"><p><strong>Важно:</strong> введите текст выноски.</p></div>'
          );
        },
      });

      editor.ui.registry.addButton('lessonbutton', {
        text: 'Кнопка',
        onAction: function () {
          var url = window.prompt('Ссылка для кнопки:', 'https://');
          if (!url) return;
          editor.insertContent(
            '<p class="lesson-btn-wrap"><a class="lesson-btn" href="' +
              editor.dom.encode(url) +
              '" target="_blank" rel="noopener">Текст кнопки</a></p>'
          );
        },
      });

      editor.on('PostProcess', function (e) {
        if (e.format === 'html' && e.get) {
          e.content = normalizeLessonHtml(e.content);
        }
      });

      editor.on('change input undo redo', function () {
        editor.save();
      });

      editor.on('NodeChange', function () {
        var img = editor.selection.getNode();
        if (img && img.nodeName === 'IMG' && !img.getAttribute('class')) {
          img.classList.add('lesson-align-center');
        }
      });
    },
    images_upload_handler: function (blobInfo, progress) {
      return new Promise(function (resolve, reject) {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', uploadUrl);
        xhr.setRequestHeader('X-CSRFToken', csrfToken);
        xhr.upload.onprogress = function (e) {
          if (e.lengthComputable) {
            progress((e.loaded / e.total) * 100);
          }
        };
        xhr.onload = function () {
          if (xhr.status < 200 || xhr.status >= 300) {
            reject('Ошибка загрузки изображения');
            return;
          }
          try {
            var json = JSON.parse(xhr.responseText);
            if (json.location) {
              resolve(json.location);
            } else {
              reject(json.error || 'Ошибка загрузки');
            }
          } catch (err) {
            reject('Неверный ответ сервера');
          }
        };
        xhr.onerror = function () {
          reject('Сеть недоступна');
        };
        var formData = new FormData();
        formData.append('file', blobInfo.blob(), blobInfo.filename());
        xhr.send(formData);
      });
    },
  });

  var form = document.querySelector('.lesson-editor-form');
  if (form) {
    form.addEventListener('submit', function () {
      var editor = tinymce.get('id_material');
      if (editor) {
        var html = normalizeLessonHtml(editor.getContent());
        editor.setContent(html, { format: 'html' });
        editor.save();
      }
    });
  }
})();
