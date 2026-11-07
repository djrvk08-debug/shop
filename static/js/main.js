/**
 * Dharti Mushroom Farm Storefront & Admin Interactive Scripts
 * Pure vanilla JavaScript with zero external dependencies.
 */

document.addEventListener("DOMContentLoaded", () => {
  const currencyFormatter = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  });
  const cartToast = document.getElementById("cart-toast");
  const cartToastMessage = document.getElementById("cart-toast-message");
  const cartToastAction = cartToast?.querySelector(".cart-toast-action");
  let cartToastTimer;

  function showCartToast(total, count) {
    if (!cartToast || !cartToastMessage) return;
    cartToastMessage.textContent = `Cart total: ${currencyFormatter.format(Number(total))} · ${count} ${count === 1 ? "item" : "items"}`;
    cartToast.hidden = false;
    cartToast.classList.remove("is-leaving");
    cartToast.classList.add("is-visible");
    clearTimeout(cartToastTimer);
    cartToastTimer = setTimeout(() => {
      cartToast.classList.remove("is-visible");
      cartToast.classList.add("is-leaving");
      setTimeout(() => {
        cartToast.hidden = true;
        cartToast.classList.remove("is-leaving");
      }, 220);
    }, 3000);
  }

  cartToast?.addEventListener("click", (event) => {
    if (!event.target.closest("a") && cartToastAction) {
      window.location.href = cartToastAction.href;
    }
  });

  document.querySelectorAll("form[action*='/cart/add']").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      const price = form.closest(".product-card, .product-detail-info")?.querySelector(".price-amount")?.textContent;
      if (price) formData.set("unit_price", price.trim());

      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: formData,
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (!response.ok) throw new Error("Cart update failed");
        const cart = await response.json();
        showCartToast(cart.cart_total, cart.item_count);
      } catch (error) {
        form.submit();
      }
    });
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/service-worker.js").catch(() => {
        // PWA support is optional and should never block storefront behavior.
      });
    });
  }

  /* ==========================================================================
     1. Flash Messages Auto-Dismiss & Manual Close
     ========================================================================== */
  const flashBanners = document.querySelectorAll(".flash");
  flashBanners.forEach((flash) => {
    // Manual close button
    const closeBtn = flash.querySelector(".flash-close-btn");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => {
        dismissFlash(flash);
      });
    }

    // Auto-dismiss after 6 seconds
    setTimeout(() => {
      dismissFlash(flash);
    }, 6000);
  });

  function dismissFlash(el) {
    if (!el || el.dataset.dismissed) return;
    el.dataset.dismissed = "true";
    el.style.transition = "opacity 0.3s ease, transform 0.3s ease";
    el.style.opacity = "0";
    el.style.transform = "translateY(-6px)";
    setTimeout(() => el.remove(), 300);
  }

  /* ==========================================================================
     2. Mobile Header Drawer & Admin Sidebar Toggles
     ========================================================================== */
  const mobileDrawer = document.querySelector(".mobile-drawer");

  const adminSidebarToggle = document.querySelector(".admin-sidebar-toggle-btn");
  const adminSidebar = document.querySelector(".admin-sidebar");
  if (adminSidebarToggle && adminSidebar) {
    adminSidebarToggle.addEventListener("click", () => {
      adminSidebar.classList.toggle("open");
    });
  }

  /* ==========================================================================
     3. Pincode Delivery Availability Checker (UI Only)
     ========================================================================== */
  const pincodeForms = document.querySelectorAll(".pincode-form");
  pincodeForms.forEach((form) => {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const input = form.querySelector(".pincode-input");
      const resultBox = form.closest(".pincode-strip, .pincode-widget")?.querySelector(".pincode-result");
      if (!input || !resultBox) return;

      const code = input.value.trim();
      if (!/^\d{6}$/.test(code)) {
        resultBox.textContent = "Please enter a valid 6-digit Indian pincode";
        resultBox.className = "pincode-result unavailable";
        resultBox.style.display = "inline-block";
        return;
      }

      // Demo delivery logic: all standard zones deliverable with cold-chain
      resultBox.textContent = `Pincode ${code}: Delivering cold & fresh! Next slot: Tomorrow 7-10 AM`;
      resultBox.className = "pincode-result available";
      resultBox.style.display = "inline-block";
    });
  });

  /* ==========================================================================
     4. Weight Selector (200 g / 500 g / 1 kg) with Dynamic Price Update
     ========================================================================== */
  const weightContainers = document.querySelectorAll("[data-weight-selector]");
  weightContainers.forEach((container) => {
    const buttons = container.querySelectorAll(".segmented-btn");
    const parentCard = container.closest(".product-card, .product-detail-info");
    const priceDisplay = parentCard?.querySelector(".price-amount");
    const unitDisplay = parentCard?.querySelector(".price-unit");
    const weightHiddenInput = parentCard?.querySelector("input[name='weight']");

    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        buttons.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");

        const weight = btn.dataset.weight || "200g";
        const price = btn.dataset.price;

        if (priceDisplay && price) {
          priceDisplay.textContent = price;
        }
        if (unitDisplay) {
          unitDisplay.textContent = `/ ${weight}`;
        }
        if (weightHiddenInput) {
          weightHiddenInput.value = weight;
        }

        // Also update mobile sticky bar price if on detail page
        const mobilePrice = document.querySelector(".mobile-sticky-pricing .price-amount");
        const mobileUnit = document.querySelector(".mobile-sticky-pricing .price-unit");
        if (mobilePrice && price) mobilePrice.textContent = price;
        if (mobileUnit) mobileUnit.textContent = `/ ${weight}`;
      });
    });
  });

  /* ==========================================================================
     5. Quantity Steppers (- and +)
     ========================================================================== */
  const steppers = document.querySelectorAll(".qty-stepper");
  steppers.forEach((stepper) => {
    const minusBtn = stepper.querySelector(".qty-minus");
    const plusBtn = stepper.querySelector(".qty-plus");
    const input = stepper.querySelector(".qty-input");
    if (!minusBtn || !plusBtn || !input) return;

    minusBtn.addEventListener("click", () => {
      let val = parseInt(input.value, 10) || 1;
      if (val > 1) {
        val -= 1;
        input.value = val;
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });

    plusBtn.addEventListener("click", () => {
      let val = parseInt(input.value, 10) || 1;
      if (val < 99) {
        val += 1;
        input.value = val;
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
  });

  /* ==========================================================================
     6. Radio Cards (Delivery Slot Selection in Checkout)
     ========================================================================== */
  const radioCards = document.querySelectorAll(".radio-card");
  radioCards.forEach((card) => {
    card.addEventListener("click", (e) => {
      if (card.classList.contains("disabled")) return;
      const radio = card.querySelector("input[type='radio']");
      if (radio && !radio.disabled) {
        radio.checked = true;
        const groupName = radio.name;
        document.querySelectorAll(`input[type='radio'][name='${groupName}']`).forEach((r) => {
          r.closest(".radio-card")?.classList.remove("selected");
        });
        card.classList.add("selected");
      }
    });
  });

  /* ==========================================================================
     7. Password Show/Hide Toggle in Auth Pages
     ========================================================================== */
  const passwordToggles = document.querySelectorAll(".password-toggle-btn");
  passwordToggles.forEach((btn) => {
    btn.addEventListener("click", () => {
      const wrapper = btn.closest(".password-input-wrapper");
      const input = wrapper?.querySelector("input");
      if (!input) return;

      const isPassword = input.type === "password";
      input.type = isPassword ? "text" : "password";
      btn.setAttribute("aria-label", isPassword ? "Hide password" : "Show password");

      // Swap eye SVG
      const icon = btn.querySelector("svg");
      if (icon) {
        if (isPassword) {
          // Eye closed slash
          icon.innerHTML = `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line>`;
        } else {
          // Normal eye
          icon.innerHTML = `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>`;
        }
      }
    });
  });

  /* ==========================================================================
     8. Category Chips Filter (Instant Client-side Filter)
     ========================================================================== */
  const chips = document.querySelectorAll(".chip[data-category]");
  const productCards = document.querySelectorAll(".product-card[data-category]");
  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      chips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");

      const cat = chip.dataset.category;
      productCards.forEach((card) => {
        if (cat === "all" || card.dataset.category === cat) {
          card.style.display = "flex";
        } else {
          card.style.display = "none";
        }
      });
    });
  });

  /* ==========================================================================
     9. Demo Admin Auto-Fill Button
     ========================================================================== */
  const fillAdminBtn = document.getElementById("fill-admin-btn");
  if (fillAdminBtn) {
    fillAdminBtn.addEventListener("click", () => {
      const emailInput = document.getElementById("email");
      const passInput = document.getElementById("password");
      if (emailInput) emailInput.value = "admin@example.com";
      if (passInput) passInput.value = "admin123";
    });
  }
});
