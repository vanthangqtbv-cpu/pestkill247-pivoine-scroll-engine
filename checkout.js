/*!
 * checkout.js — Vanilla JS 3-Step In-Page Luxury Bag & B2B Checkout Engine
 * Modeled after Ascenta Studio's PIVOINE checkout module for Pest Kill 247 (Hoàng Trang VN).
 */
(function () {
  "use strict";

  const CATALOG = {
    "PK-BIOGOLD-35": {
      sku: "PK-BIOGOLD-35",
      name: "BioGold Pro — Gel Diệt Gián Đức",
      sub: "Ống pha lê 35g · Chiết xuất Cúc Trừ Sâu & Domino Matrix",
      price: 480000,
      img: "assets/products/prod_gel_biogold.jpg",
    },
    "PK-ULV-500": {
      sku: "PK-ULV-500",
      name: "Nano Shield — Tinh Chất Phun ULV",
      sub: "Chai 500ml · Không mùi · Chuẩn an toàn Bộ Y Tế",
      price: 890000,
      img: "assets/products/prod_ulv_nano.jpg",
    },
    "PK-BAIT-PRO": {
      sku: "PK-BAIT-PRO",
      name: "SmartBait — Trạm Kiểm Soát Chuột",
      sub: "Vỏ ABS chống va đập · Khóa an toàn chuẩn kiểm toán HACCP",
      price: 650000,
      img: "assets/products/prod_smart_bait.jpg",
    },
    "PK-B2B-SUITE": {
      sku: "PK-B2B-SUITE",
      name: "B2B Master Kit & Dịch Vụ Định Kỳ",
      sub: "Trọn bộ F&B, Khách sạn, Nhà máy · Kèm biên bản & Hóa đơn VAT",
      price: 2450000,
      img: "assets/products/prod_b2b_kit.jpg",
    },
  };

  const state = {
    items: [
      { sku: "PK-BIOGOLD-35", qty: 1 },
    ],
    step: 1,
    needVat: true,
  };

  function formatVND(amount) {
    return amount.toLocaleString("vi-VN") + " ₫";
  }

  function getTotalCount() {
    return state.items.reduce((acc, it) => acc + it.qty, 0);
  }

  function getSubtotal() {
    return state.items.reduce((acc, it) => {
      const prod = CATALOG[it.sku];
      return acc + (prod ? prod.price * it.qty : 0);
    }, 0);
  }

  function updateNavBadge() {
    const badges = document.querySelectorAll("[data-bag-count]");
    const count = getTotalCount();
    badges.forEach((el) => {
      el.textContent = String(count);
    });
  }

  function renderBagItems() {
    const container = document.getElementById("pk-bag-list");
    if (!container) return;

    if (state.items.length === 0) {
      container.innerHTML =
        '<div style="padding:24px 12px;text-align:center;color:#7D6B5B;font-size:14px;">Giỏ hàng đang trống. Hãy chọn giải pháp bên dưới để thêm vào đơn.</div>';
    } else {
      container.innerHTML = state.items
        .map((entry) => {
          const p = CATALOG[entry.sku];
          if (!p) return "";
          return `
            <div class="pk-bag-item">
              <img src="${p.img}" alt="${p.name}" loading="lazy" />
              <div>
                <div class="pk-bag-item-name">${p.name}</div>
                <div class="pk-bag-item-sub">${p.sub}</div>
                <div class="pk-qty-controls">
                  <button type="button" class="pk-qty-btn" data-qty-act="dec" data-sku="${p.sku}" aria-label="Giảm">−</button>
                  <span style="font-size:12.5px;font-weight:700;min-width:16px;text-align:center;">${entry.qty}</span>
                  <button type="button" class="pk-qty-btn" data-qty-act="inc" data-sku="${p.sku}" aria-label="Tăng">+</button>
                </div>
              </div>
              <div class="pk-bag-item-price">${formatVND(p.price * entry.qty)}</div>
            </div>
          `;
        })
        .join("");
    }

    const sub = getSubtotal();
    const ship = sub >= 1000000 || sub === 0 ? 0 : 35000;
    const grand = sub + ship;

    const subEl = document.getElementById("pk-total-sub");
    const shipEl = document.getElementById("pk-total-ship");
    const grandEl = document.getElementById("pk-total-grand");
    if (subEl) subEl.textContent = formatVND(sub);
    if (shipEl) shipEl.textContent = ship === 0 ? "Miễn phí (Express 2h)" : formatVND(ship);
    if (grandEl) grandEl.textContent = formatVND(grand);
  }

  function setStep(stepNum) {
    state.step = stepNum;
    document.querySelectorAll("[data-step-pill]").forEach((pill) => {
      const s = Number(pill.getAttribute("data-step-pill"));
      pill.classList.toggle("is-active", s === stepNum);
    });
    document.querySelectorAll("[data-step-pane]").forEach((pane) => {
      const s = Number(pane.getAttribute("data-step-pane"));
      pane.classList.toggle("is-active", s === stepNum);
    });
  }

  function openModal(skuToAdd) {
    if (skuToAdd && CATALOG[skuToAdd]) {
      const existing = state.items.find((i) => i.sku === skuToAdd);
      if (existing) {
        existing.qty += 1;
      } else {
        state.items.push({ sku: skuToAdd, qty: 1 });
      }
    }
    updateNavBadge();
    renderBagItems();
    setStep(1);

    const modal = document.getElementById("pk-checkout-modal");
    if (modal) {
      modal.classList.add("is-open");
      modal.setAttribute("aria-hidden", "false");
    }
    if (window.__lenis) {
      window.__lenis.stop();
    }
  }

  function closeModal() {
    const modal = document.getElementById("pk-checkout-modal");
    if (modal) {
      modal.classList.remove("is-open");
      modal.setAttribute("aria-hidden", "true");
    }
    if (window.__lenis) {
      window.__lenis.start();
    }
  }

  function initCheckout() {
    updateNavBadge();
    renderBagItems();

    // Delegate clicks on Add-to-Bag / Open Bag buttons
    document.addEventListener("click", (e) => {
      const addBtn = e.target.closest("[data-add-sku]");
      if (addBtn) {
        e.preventDefault();
        const sku = addBtn.getAttribute("data-add-sku");
        openModal(sku);
        return;
      }

      const openBagBtn = e.target.closest("[data-open-bag]");
      if (openBagBtn) {
        e.preventDefault();
        openModal(null);
        return;
      }

      const closeBtn = e.target.closest("[data-close-bag]");
      if (closeBtn) {
        e.preventDefault();
        closeModal();
        return;
      }

      const qtyBtn = e.target.closest("[data-qty-act]");
      if (qtyBtn) {
        const sku = qtyBtn.getAttribute("data-sku");
        const act = qtyBtn.getAttribute("data-qty-act");
        const item = state.items.find((i) => i.sku === sku);
        if (item) {
          if (act === "inc") item.qty += 1;
          if (act === "dec") item.qty -= 1;
          if (item.qty <= 0) {
            state.items = state.items.filter((i) => i.sku !== sku);
          }
          updateNavBadge();
          renderBagItems();
        }
        return;
      }

      const nextStepBtn = e.target.closest("[data-goto-step]");
      if (nextStepBtn) {
        e.preventDefault();
        const targetStep = Number(nextStepBtn.getAttribute("data-goto-step"));
        if (targetStep === 3) {
          // Populate confirmation summary
          const nameVal = (document.getElementById("pk-inp-name") || {}).value || "Quý khách hàng / Đối tác B2B";
          const phoneVal = (document.getElementById("pk-inp-phone") || {}).value || "0902 972 860";
          const companyVal = (document.getElementById("pk-inp-company") || {}).value || "Khách hàng Doanh nghiệp";
          const refEl = document.getElementById("pk-confirm-ref");
          const summaryEl = document.getElementById("pk-confirm-summary");
          const code = "PK247-" + Math.floor(100000 + Math.random() * 900000);
          if (refEl) refEl.textContent = code;
          if (summaryEl) {
            summaryEl.textContent = `${nameVal} (${companyVal}) · SĐT: ${phoneVal} · Tổng thanh toán: ${formatVND(getSubtotal())}`;
          }
        }
        setStep(targetStep);
      }
    });

    // Close on backdrop click or Escape key
    const modal = document.getElementById("pk-checkout-modal");
    if (modal) {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
      });
    }
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeModal();
    });

    // Interactive 3D tilt on Corporate Payment Card
    const cardWrap = document.querySelector(".pk-card-3d-wrap");
    const card3d = document.querySelector(".pk-card-3d");
    if (cardWrap && card3d) {
      cardWrap.addEventListener("mousemove", (e) => {
        const rect = cardWrap.getBoundingClientRect();
        const x = (e.clientX - rect.left) / rect.width - 0.5;
        const y = (e.clientY - rect.top) / rect.height - 0.5;
        card3d.style.transform = `rotateY(${x * 14}deg) rotateX(${-y * 14}deg)`;
      });
      cardWrap.addEventListener("mouseleave", () => {
        card3d.style.transform = "rotateY(0deg) rotateX(0deg)";
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCheckout);
  } else {
    initCheckout();
  }
})();
