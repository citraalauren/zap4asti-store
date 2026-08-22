'use strict';

/* ==========================================================================
   Тема (тёмная/светлая) — сохраняется в localStorage
   ========================================================================== */
var THEME_KEY = 'zap4asti-theme';

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  var icon = document.querySelector('#theme-toggle .theme-icon');
  if (icon) icon.textContent = theme === 'dark' ? '☀️' : '🌙';
}

(function initTheme() {
  var saved = localStorage.getItem(THEME_KEY);
  var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  applyTheme(saved || (prefersDark ? 'dark' : 'light'));
})();

var themeToggle = document.getElementById('theme-toggle');
if (themeToggle) {
  themeToggle.addEventListener('click', function () {
    var next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    applyTheme(next);
    localStorage.setItem(THEME_KEY, next);
  });
}

/* ==========================================================================
   Мобильное меню
   ========================================================================== */
var menuToggle = document.getElementById('mobile-menu-toggle');
var headerNav = document.getElementById('header-nav');
if (menuToggle && headerNav) {
  menuToggle.addEventListener('click', function () {
    headerNav.classList.toggle('is-open');
  });
}

/* ==========================================================================
   Toast-уведомления
   ========================================================================== */
function showToast(message, category) {
  var container = document.getElementById('toast-container');
  if (!container || !message) return;

  var toast = document.createElement('div');
  toast.className = 'toast toast--' + (category || 'info');
  toast.textContent = message;
  container.appendChild(toast);

  requestAnimationFrame(function () { toast.classList.add('is-visible'); });

  setTimeout(function () {
    toast.classList.remove('is-visible');
    setTimeout(function () { toast.remove(); }, 250);
  }, 3500);
}

// Flash-сообщения Flask (флешатся в base.html) показываем как toast-ы
document.querySelectorAll('#flash-data .flash-item').forEach(function (el, i) {
  setTimeout(function () { showToast(el.dataset.message, el.dataset.category); }, i * 150);
});

/* ==========================================================================
   CSRF-токен для fetch-запросов (Flask-WTF читает заголовок X-CSRFToken)
   ========================================================================== */
function getCsrfToken() {
  var meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.content : '';
}

/* ==========================================================================
   Анимация «улёта» товара в иконку корзины
   ========================================================================== */
function flyToCart(startEl) {
  var cartLink = document.querySelector('.cart-link');
  var flyIcon = document.getElementById('fly-icon');
  if (!cartLink || !flyIcon) return;

  var startRect = startEl.getBoundingClientRect();
  var endRect = cartLink.getBoundingClientRect();
  var startX = startRect.left + startRect.width / 2 - 12;
  var startY = startRect.top + startRect.height / 2 - 12;
  var endX = endRect.left + endRect.width / 2 - 12;
  var endY = endRect.top + endRect.height / 2 - 12;

  flyIcon.style.transition = 'none';
  flyIcon.style.transform = 'translate(' + startX + 'px, ' + startY + 'px) scale(1)';
  flyIcon.hidden = false;
  void flyIcon.offsetWidth; // форсируем reflow, чтобы браузер применил стартовую позицию без анимации
  flyIcon.style.transition = '';

  requestAnimationFrame(function () {
    flyIcon.style.transform = 'translate(' + endX + 'px, ' + endY + 'px) scale(0.3)';
  });

  flyIcon.addEventListener('transitionend', function handler() {
    flyIcon.hidden = true;
    flyIcon.removeEventListener('transitionend', handler);
  }, { once: true });
}

/* ==========================================================================
   Добавление в корзину (AJAX + анимация + toast + счётчик в шапке)
   ========================================================================== */
function updateCartBadge(count) {
  var badge = document.getElementById('cart-badge');
  if (!badge) return;
  badge.textContent = count;
  badge.classList.toggle('is-hidden', count === 0);
}

document.addEventListener('click', function (e) {
  var btn = e.target.closest('.btn-add-cart');
  if (!btn) return;

  flyToCart(btn);

  fetch('/api/cart/add', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken(),
    },
    body: JSON.stringify({ product_id: Number(btn.dataset.productId), quantity: 1 }),
  })
    .then(function (res) { return res.json(); })
    .then(function (data) {
      if (data.success) {
        updateCartBadge(data.cart_count);
        showToast(data.message, 'success');
      } else {
        showToast(data.message || 'Не удалось добавить товар в корзину.', 'error');
      }
    })
    .catch(function () {
      showToast('Ошибка сети. Попробуйте ещё раз.', 'error');
    });
});

/* ==========================================================================
   Галерея фото товара — клик по миниатюре меняет главное фото
   ========================================================================== */
document.addEventListener('click', function (e) {
  var thumb = e.target.closest('.product-detail__thumb');
  if (!thumb) return;

  var mainImg = document.querySelector('#product-main-image img');
  if (mainImg) mainImg.src = thumb.dataset.fullSrc;

  document.querySelectorAll('.product-detail__thumb').forEach(function (el) {
    el.classList.toggle('is-active', el === thumb);
  });
});

/* ==========================================================================
   Подтверждение перед удалением (замена inline onsubmit — CSP без unsafe-inline)
   ========================================================================== */
document.addEventListener('submit', function (e) {
  var form = e.target.closest('.js-confirm');
  if (form && !window.confirm(form.dataset.confirm || 'Вы уверены?')) {
    e.preventDefault();
  }
});

/* ==========================================================================
   Автоотправка формы при смене select (например, статус заказа в админке)
   ========================================================================== */
document.addEventListener('change', function (e) {
  if (e.target.matches('.js-auto-submit')) {
    e.target.form.submit();
  }
});

/* ==========================================================================
   Чекаут: переключение курьер / пункт выдачи + каскадные списки город/пункт
   ========================================================================== */
(function initDeliveryForm() {
  var form = document.getElementById('checkout-form');
  if (!form) return;

  var courierFields = document.getElementById('courier-fields');
  var pickupFields = document.getElementById('pickup-fields');
  var providerSelect = document.getElementById('delivery-provider');
  var citySelect = document.getElementById('delivery-city');
  var pointSelect = document.getElementById('delivery-point');

  function fillSelect(select, options, placeholder) {
    select.innerHTML = '';
    var placeholderOpt = document.createElement('option');
    placeholderOpt.value = '';
    placeholderOpt.textContent = placeholder;
    select.appendChild(placeholderOpt);
    options.forEach(function (value) {
      var opt = document.createElement('option');
      opt.value = value;
      opt.textContent = value;
      select.appendChild(opt);
    });
  }

  form.querySelectorAll('input[name="delivery_type"]').forEach(function (radio) {
    radio.addEventListener('change', function () {
      var isPickup = radio.value === 'pickup' && radio.checked;
      pickupFields.hidden = !isPickup;
      courierFields.hidden = isPickup;
    });
  });

  if (providerSelect) {
    providerSelect.addEventListener('change', function () {
      fillSelect(citySelect, [], 'Загрузка...');
      fillSelect(pointSelect, [], 'Сначала выберите город');
      citySelect.disabled = true;
      pointSelect.disabled = true;
      if (!providerSelect.value) {
        fillSelect(citySelect, [], 'Сначала выберите службу');
        return;
      }
      fetch('/api/delivery/cities?provider=' + encodeURIComponent(providerSelect.value))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          fillSelect(citySelect, data.cities || [], 'Выберите город');
          citySelect.disabled = false;
        });
    });
  }

  if (citySelect) {
    citySelect.addEventListener('change', function () {
      fillSelect(pointSelect, [], 'Загрузка...');
      pointSelect.disabled = true;
      if (!citySelect.value) {
        fillSelect(pointSelect, [], 'Сначала выберите город');
        return;
      }
      var url = '/api/delivery/points?provider=' + encodeURIComponent(providerSelect.value)
        + '&city=' + encodeURIComponent(citySelect.value);
      fetch(url)
        .then(function (r) { return r.json(); })
        .then(function (data) {
          fillSelect(pointSelect, data.points || [], 'Выберите пункт выдачи');
          pointSelect.disabled = false;
        });
    });
  }
})();

/* ==========================================================================
   Демо-страница оплаты: вкладки карта/СБП, форматирование полей карты,
   имитация обработки платежа перед отправкой формы
   ========================================================================== */
(function initPaymentPage() {
  var paymentForm = document.getElementById('payment-form');
  if (!paymentForm) return;

  document.querySelectorAll('.payment-tabs__btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.payment-tabs__btn').forEach(function (b) {
        b.classList.toggle('is-active', b === btn);
      });
      document.querySelectorAll('.payment-tab-panel').forEach(function (panel) {
        panel.hidden = panel.dataset.panel !== btn.dataset.tab;
      });
    });
  });

  var cardNumber = document.getElementById('card-number');
  if (cardNumber) {
    cardNumber.addEventListener('input', function () {
      var digits = cardNumber.value.replace(/\D/g, '').slice(0, 16);
      cardNumber.value = digits.replace(/(.{4})/g, '$1 ').trim();
    });
  }

  var cardExpiry = document.getElementById('card-expiry');
  if (cardExpiry) {
    cardExpiry.addEventListener('input', function () {
      var digits = cardExpiry.value.replace(/\D/g, '').slice(0, 4);
      cardExpiry.value = digits.length > 2 ? digits.slice(0, 2) + '/' + digits.slice(2) : digits;
    });
  }

  var cardCvv = document.getElementById('card-cvv');
  if (cardCvv) {
    cardCvv.addEventListener('input', function () {
      cardCvv.value = cardCvv.value.replace(/\D/g, '').slice(0, 3);
    });
  }

  paymentForm.addEventListener('submit', function (e) {
    var btn = document.getElementById('pay-submit-btn');
    if (btn.dataset.processing) {
      e.preventDefault();
      return;
    }
    e.preventDefault();
    btn.dataset.processing = '1';
    var originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Обработка платежа...';
    setTimeout(function () {
      paymentForm.submit();
    }, 1200);
  });
})();

/* ==========================================================================
   Плавные анимации при скролле (AOS, подключён через CDN в base.html)
   ========================================================================== */
if (window.AOS) {
  AOS.init({ duration: 500, once: true, offset: 40 });
}
