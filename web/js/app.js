const API_BASE = "";

const state = {
    user: null,
    profile: null,
    driver: null,
    rides: [],
    orders: [],
    notifications: [],
    unreadNotifications: 0,
    currentScreen: "home",
    telegram: null,
};


/* =========================
   TELEGRAM
========================= */

function initTelegram() {
    if (window.Telegram && window.Telegram.WebApp) {
        state.telegram = window.Telegram.WebApp;

        state.telegram.ready();
        state.telegram.expand();

        if (state.telegram.setHeaderColor) {
            state.telegram.setHeaderColor("#111827");
        }

        if (state.telegram.setBackgroundColor) {
            state.telegram.setBackgroundColor("#f5f6f8");
        }

        state.user =
            state.telegram.initDataUnsafe?.user || null;
    }
}


/* =========================
   HELPERS
========================= */

function $(selector) {
    return document.querySelector(selector);
}


function $$(selector) {
    return document.querySelectorAll(selector);
}


function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatPrice(price) {
    const number = Number(price || 0);

    return new Intl.NumberFormat("uz-UZ").format(number);
}


function formatDate(date) {
    if (!date) {
        return "—";
    }

    try {
        return new Date(date).toLocaleDateString("uz-UZ");
    } catch {
        return date;
    }
}


function formatTime(time) {
    if (!time) {
        return "—";
    }

    return String(time);
}


function showToast(message) {
    let container = $(".toast-container");

    if (!container) {
        container = document.createElement("div");
        container.className = "toast-container";
        document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}


function showLoading(
    element,
    text = "Yuklanmoqda..."
) {
    if (!element) {
        return;
    }

    element.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <span>
                ${escapeHtml(text)}
            </span>
        </div>
    `;
}


function showEmpty(
    element,
    icon,
    title,
    text = ""
) {
    if (!element) {
        return;
    }

    element.innerHTML = `
        <div class="empty-state">

            <div class="empty-icon">
                ${icon}
            </div>

            <div class="empty-title">
                ${escapeHtml(title)}
            </div>

            ${
                text
                    ? `
                        <div>
                            ${escapeHtml(text)}
                        </div>
                    `
                    : ""
            }

        </div>
    `;
}


/* =========================
   API
========================= */

async function api(
    url,
    options = {}
) {
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    if (
        state.telegram &&
        state.telegram.initData
    ) {
        headers["X-Telegram-Init-Data"] =
            state.telegram.initData;
    }

    const response = await fetch(
        API_BASE + url,
        {
            ...options,
            headers
        }
    );

    let result = null;

    try {
        result = await response.json();
    } catch {
        result = null;
    }

    if (!response.ok) {
        throw new Error(
            result?.error ||
            result?.message ||
            result?.data?.error ||
            "Server xatosi."
        );
    }

    if (
        result &&
        result.success === false
    ) {
        throw new Error(
            result.error ||
            result.message ||
            "Amal bajarilmadi."
        );
    }

    if (
        result &&
        result.ok === false
    ) {
        throw new Error(
            result.error ||
            result.message ||
            "Amal bajarilmadi."
        );
    }

    /*
       Backend ayrim joylarda:

       {
           ok: true,
           data: {...}
       }

       formatida javob beradi.

       Frontend esa bevosita data ichidagi
       ma'lumotlar bilan ishlaydi.
    */

    if (
        result &&
        result.ok === true &&
        result.data !== undefined
    ) {
        return result.data;
    }

    return result || {};
}


/* =========================
   NAVIGATION
========================= */

function showScreen(screenName) {
    state.currentScreen = screenName;

    $$(".screen").forEach(
        screen => {
            screen.classList.toggle(
                "active",
                screen.dataset.screen === screenName
            );
        }
    );

    $$(".nav-item").forEach(
        item => {
            item.classList.toggle(
                "active",
                item.dataset.screen === screenName
            );
        }
    );

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

    if (screenName === "home") {
        loadHome();
    }

    if (screenName === "rides") {
        loadRides();
    }

    if (screenName === "orders") {
        loadOrders();
    }

    if (screenName === "notifications") {
        loadNotifications();
    }

    if (screenName === "profile") {
        loadProfile();
    }
}


/* =========================
   PROFILE
========================= */

async function loadProfile() {
    const container = $("#profile-content");

    if (!container) {
        return;
    }

    showLoading(
        container,
        "Profil yuklanmoqda..."
    );

    try {
        const data = await api(
            "/api/profile"
        );

        state.profile =
            data.profile ||
            data.user ||
            null;

        state.driver =
            data.driver ||
            null;

        renderProfile();

    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-error">
                ${escapeHtml(error.message)}
            </div>
        `;
    }
}


function renderProfile() {
    const container =
        $("#profile-content");

    if (!container) {
        return;
    }

    const profile =
        state.profile || {};

    const firstName =
        profile.first_name ||
        state.user?.first_name ||
        "";

    const lastName =
        profile.last_name ||
        state.user?.last_name ||
        "";

    const username =
        profile.username ||
        state.user?.username ||
        "";

    const phone =
        profile.phone ||
        "";

    const fullName =
        `${firstName} ${lastName}`.trim() ||
        "Foydalanuvchi";

    let driverStatus = "";

    if (state.driver) {
        const status =
            state.driver.status;

        if (status === "approved") {
            driverStatus = `
                <span class="badge badge-green">
                    🚕 Haydovchi tasdiqlangan
                </span>
            `;
        } else if (status === "pending") {
            driverStatus = `
                <span class="badge badge-yellow">
                    ⏳ Ariza ko'rib chiqilmoqda
                </span>
            `;
        } else if (status === "rejected") {
            driverStatus = `
                <span class="badge badge-red">
                    ❌ Ariza rad etilgan
                </span>
            `;
        }
    }

    container.innerHTML = `

        <div class="card">

            <div class="profile-card">

                <div class="avatar">
                    👤
                </div>

                <div>

                    <div class="profile-name">
                        ${escapeHtml(fullName)}
                    </div>

                    <div class="profile-meta">
                        ${
                            username
                                ? "@" + escapeHtml(username)
                                : "Telegram foydalanuvchisi"
                        }
                    </div>

                </div>

            </div>

        </div>


        ${
            driverStatus
                ? `
                    <div class="card">
                        ${driverStatus}
                    </div>
                `
                : `
                    <div class="card">

                        <div class="card-title">
                            🚕 Haydovchi bo'lish
                        </div>

                        <div class="card-text">
                            O'z avtomobilingiz bilan
                            shaharlararo yo'lovchi tashish
                            uchun ariza yuboring.
                        </div>

                        <br>

                        <button
                            class="btn btn-primary"
                            onclick="openDriverApplication()"
                        >
                            Haydovchi bo'lish
                        </button>

                    </div>
                `
        }


        <div class="card">

            <div class="card-title">
                📱 Telefon raqami
            </div>

            <div class="card-text">
                ${
                    phone
                        ? escapeHtml(phone)
                        : "Telefon raqami kiritilmagan"
                }
            </div>

        </div>

    `;
}


/* =========================
   DRIVER APPLICATION
========================= */

function openDriverApplication() {
    const phone =
        state.profile?.phone ||
        state.user?.phone ||
        "";

    const modal =
        $("#driver-modal");

    if (!modal) {
        showToast(
            "Haydovchi ariza oynasi mavjud emas."
        );

        return;
    }

    const input =
        $("#driver-phone");

    if (input) {
        input.value = phone;
    }

    modal.classList.add("active");
}


function closeDriverApplication() {
    const modal =
        $("#driver-modal");

    if (modal) {
        modal.classList.remove("active");
    }
}


async function submitDriverApplication() {
    const input =
        $("#driver-phone");

    const phone =
        input?.value?.trim() || "";

    if (!phone) {
        showToast(
            "Telefon raqamingizni kiriting."
        );

        return;
    }

    try {
        const data =
            await api(
                "/api/driver/register",
                {
                    method: "POST",

                    body: JSON.stringify({
                        phone
                    })
                }
            );

        closeDriverApplication();

        if (data.already_exists) {
            if (data.status === "approved") {
                showToast(
                    "🚕 Siz allaqachon tasdiqlangan haydovchisiz."
                );
            } else if (data.status === "pending") {
                showToast(
                    "⏳ Arizangiz hali ko'rib chiqilmoqda."
                );
            } else if (data.status === "rejected") {
                showToast(
                    "❌ Arizangiz avval rad etilgan."
                );
            } else {
                showToast(
                    "Sizning haydovchi arizangiz mavjud."
                );
            }
        } else {
            showToast(
                "✅ Haydovchilik arizasi yuborildi."
            );
        }

        await loadProfile();

    } catch (error) {
        showToast(
            error.message
        );
    }
}


/* =========================
   RIDES
========================= */

async function loadRides() {
    const container =
        $("#rides-list");

    if (!container) {
        return;
    }

    showLoading(
        container,
        "Safarlar yuklanmoqda..."
    );

    try {
        const data =
            await api(
                "/api/rides"
            );

        state.rides =
            Array.isArray(data.rides)
                ? data.rides
                : [];

        renderRides();

    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-error">
                ${escapeHtml(error.message)}
            </div>
        `;
    }
}


function renderRides() {
    const container =
        $("#rides-list");

    if (!container) {
        return;
    }

    if (!state.rides.length) {
        showEmpty(
            container,
            "🚕",
            "Hozircha safarlar yo'q",
            "Yangi safarlar joylanganda shu yerda ko'rinadi."
        );

        return;
    }

    container.innerHTML =
        state.rides.map(
            ride => {

                const availableSeats =
                    ride.available_seats ??
                    ride.seats ??
                    0;

                return `
                    <div class="ride-card">

                        <div class="ride-route">

                            <span>
                                ${escapeHtml(
                                    ride.from_region ||
                                    ride.from ||
                                    ""
                                )}
                            </span>

                            <span class="ride-arrow">
                                →
                            </span>

                            <span>
                                ${escapeHtml(
                                    ride.to_region ||
                                    ride.to ||
                                    ""
                                )}
                            </span>

                        </div>


                        <div class="ride-info">

                            <div class="ride-info-item">

                                <div class="ride-info-label">
                                    📅 Sana
                                </div>

                                <div class="ride-info-value">
                                    ${escapeHtml(
                                        formatDate(
                                            ride.travel_date ||
                                            ride.date
                                        )
                                    )}
                                </div>

                            </div>


                            <div class="ride-info-item">

                                <div class="ride-info-label">
                                    🕐 Vaqt
                                </div>

                                <div class="ride-info-value">
                                    ${escapeHtml(
                                        formatTime(
                                            ride.travel_time ||
                                            ride.time
                                        )
                                    )}
                                </div>

                            </div>


                            <div class="ride-info-item">

                                <div class="ride-info-label">
                                    💺 Bo'sh o'rin
                                </div>

                                <div class="ride-info-value">
                                    ${Number(
                                        availableSeats
                                    )}
                                </div>

                            </div>


                            <div class="ride-info-item">

                                <div class="ride-info-label">
                                    👤 Haydovchi
                                </div>

                                <div class="ride-info-value">
                                    ${escapeHtml(
                                        ride.driver_name ||
                                        ride.full_name ||
                                        "Haydovchi"
                                    )}
                                </div>

                            </div>

                        </div>


                        <div
                            style="
                                display:flex;
                                align-items:center;
                                justify-content:space-between;
                                gap:10px;
                            "
                        >

                            <div class="ride-price">
                                ${formatPrice(
                                    ride.price
                                )}
                                <span>so'm</span>
                            </div>


                            <button
                                class="btn btn-primary btn-small"
                                onclick="orderRide(${Number(
                                    ride.id
                                )})"
                            >
                                Buyurtma berish
                            </button>

                        </div>

                    </div>
                `;
            }
        ).join("");
}


/* =========================
   ORDER RIDE
========================= */

async function orderRide(
    rideId
) {
    const seats =
        Number(
            prompt(
                "Nechta o'rin kerak?",
                "1"
            )
        );

    if (
        !Number.isInteger(seats) ||
        seats < 1 ||
        seats > 4
    ) {
        showToast(
            "O'rinlar soni 1 dan 4 gacha bo'lishi kerak."
        );

        return;
    }

    const phone =
        state.profile?.phone ||
        state.user?.phone ||
        "";

    if (!phone) {
        showToast(
            "Avval profilingizga telefon raqamingizni kiriting."
        );

        showScreen("profile");

        return;
    }

    try {
        await api(
            "/api/passenger/order",
            {
                method: "POST",

                body: JSON.stringify({
                    ride_id: rideId,
                    seats,
                    phone
                })
            }
        );

        showToast(
            "✅ Buyurtma yuborildi."
        );

        await Promise.allSettled([
            loadOrders(),
            loadRides(),
            loadNotifications()
        ]);

    } catch (error) {
        showToast(
            error.message
        );
    }
}


/* =========================
   ORDERS
========================= */

async function loadOrders() {
    const container =
        $("#orders-list");

    if (!container) {
        return;
    }

    showLoading(
        container,
        "Buyurtmalar yuklanmoqda..."
    );

    try {
        const data =
            await api(
                "/api/orders"
            );

        state.orders =
            Array.isArray(data.orders)
                ? data.orders
                : [];

        renderOrders();

    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-error">
                ${escapeHtml(error.message)}
            </div>
        `;
    }
}


function renderOrders() {
    const container =
        $("#orders-list");

    if (!container) {
        return;
    }

    if (!state.orders.length) {
        showEmpty(
            container,
            "📦",
            "Buyurtmalar yo'q",
            "Sizning buyurtmalaringiz shu yerda ko'rinadi."
        );

        return;
    }

    container.innerHTML =
        state.orders.map(
            order => {

                let statusText =
                    "Kutilmoqda";

                let statusClass =
                    "badge-yellow";

                if (
                    order.status ===
                    "accepted"
                ) {
                    statusText =
                        "Qabul qilindi";

                    statusClass =
                        "badge-green";

                } else if (
                    order.status ===
                    "rejected"
                ) {
                    statusText =
                        "Rad etildi";

                    statusClass =
                        "badge-red";

                } else if (
                    order.status ===
                    "cancelled"
                ) {
                    statusText =
                        "Bekor qilindi";

                    statusClass =
                        "badge-red";

                } else if (
                    order.status ===
                    "finished"
                ) {
                    statusText =
                        "Tugallangan";

                    statusClass =
                        "badge-blue";
                }

                return `
                    <div class="card">

                        <div
                            style="
                                display:flex;
                                justify-content:space-between;
                                gap:10px;
                                margin-bottom:12px;
                            "
                        >

                            <div class="card-title">
                                🚕 Safar #${Number(
                                    order.ride_id
                                )}
                            </div>

                            <span class="badge ${statusClass}">
                                ${statusText}
                            </span>

                        </div>


                        <div class="card-text">

                            ${escapeHtml(
                                order.from_region ||
                                ""
                            )}

                            →

                            ${escapeHtml(
                                order.to_region ||
                                ""
                            )}

                        </div>


                        <div
                            style="
                                margin-top:10px;
                                color:#6b7280;
                                font-size:12px;
                            "
                        >

                            📅 ${
                                escapeHtml(
                                    formatDate(
                                        order.travel_date
                                    )
                                )
                            }

                            &nbsp;&nbsp;

                            🕐 ${
                                escapeHtml(
                                    formatTime(
                                        order.travel_time
                                    )
                                )
                            }

                            <br><br>

                            💺 O'rin:
                            ${Number(
                                order.seats || 1
                            )}

                            <br>

                            💰 Narx:
                            ${formatPrice(
                                order.price
                            )}
                            so'm

                        </div>

                    </div>
                `;
            }
        ).join("");
}


/* =========================
   NOTIFICATIONS
========================= */

async function loadNotifications() {
    const container =
        $("#notifications-list");

    if (!container) {
        return;
    }

    showLoading(
        container,
        "Bildirishnomalar yuklanmoqda..."
    );

    try {
        const data =
            await api(
                "/api/notifications"
            );

        state.notifications =
            Array.isArray(data.notifications)
                ? data.notifications
                : [];

        state.unreadNotifications =
            Number(
                data.unread_count ??
                data.unread ??
                0
            );

        renderNotifications();

        updateNotificationBadges();

    } catch (error) {
        container.innerHTML = `
            <div class="alert alert-error">
                ${escapeHtml(error.message)}
            </div>
        `;
    }
}


function renderNotifications() {
    const container =
        $("#notifications-list");

    if (!container) {
        return;
    }

    if (!state.notifications.length) {
        showEmpty(
            container,
            "🔔",
            "Bildirishnomalar yo'q",
            "Yangi xabarlar shu yerda ko'rinadi."
        );

        return;
    }

    container.innerHTML =
        state.notifications.map(
            notification => {

                const unread =
                    Number(
                        notification.is_read
                    ) === 0;

                return `
                    <div
                        class="
                            notification
                            ${
                                unread
                                    ? "unread"
                                    : ""
                            }
                        "
                        onclick="
                            markNotificationRead(
                                ${Number(
                                    notification.id
                                )}
                            )
                        "
                    >

                        <div class="notification-icon">
                            🔔
                        </div>


                        <div>

                            <div class="notification-title">
                                ${escapeHtml(
                                    notification.title ||
                                    "Bildirishnoma"
                                )}
                            </div>

                            <div class="notification-message">
                                ${escapeHtml(
                                    notification.message ||
                                    ""
                                )}
                            </div>

                            <div class="notification-time">
                                ${escapeHtml(
                                    notification.created_at ||
                                    ""
                                )}
                            </div>

                        </div>

                    </div>
                `;
            }
        ).join("");
}


async function markNotificationRead(
    notificationId
) {
    try {
        await api(
            "/api/notifications/read",
            {
                method: "POST",

                body: JSON.stringify({
                    notification_id:
                        notificationId
                })
            }
        );

        await loadNotifications();

    } catch (error) {
        showToast(
            error.message
        );
    }
}


function updateNotificationBadges() {
    const badges =
        $$(".nav-badge");

    badges.forEach(
        badge => {

            if (
                badge.dataset.type ===
                "notifications"
            ) {

                const count =
                    state.unreadNotifications;

                if (count > 0) {

                    badge.textContent =
                        count > 99
                            ? "99+"
                            : count;

                    badge.style.display =
                        "flex";

                } else {

                    badge.style.display =
                        "none";
                }
            }
        }
    );
}


/* =========================
   HOME
========================= */

async function loadHome() {
    await Promise.allSettled([
        loadProfile(),
        loadNotifications()
    ]);
}


/* =========================
   NAV EVENTS
========================= */

function setupNavigation() {
    $$(".nav-item").forEach(
        item => {

            item.addEventListener(
                "click",
                () => {

                    const screen =
                        item.dataset.screen;

                    if (screen) {
                        showScreen(screen);
                    }

                }
            );
        }
    );


    $$("[data-go]").forEach(
        button => {

            button.addEventListener(
                "click",
                () => {

                    const screen =
                        button.dataset.go;

                    if (screen) {
                        showScreen(screen);
                    }

                }
            );
        }
    );
}


/* =========================
   PROFILE UPDATE
========================= */

async function updateProfile() {
    const firstName =
        $("#profile-first-name")
            ?.value
            ?.trim() || "";

    const lastName =
        $("#profile-last-name")
            ?.value
            ?.trim() || "";

    const username =
        $("#profile-username")
            ?.value
            ?.trim() || "";

    const phone =
        $("#profile-phone")
            ?.value
            ?.trim() ||
        state.profile?.phone ||
        "";

    try {
        await api(
            "/api/profile/update",
            {
                method: "POST",

                body: JSON.stringify({
                    first_name: firstName,
                    last_name: lastName,
                    username,
                    phone
                })
            }
        );

        showToast(
            "✅ Profil saqlandi."
        );

        await loadProfile();

    } catch (error) {
        showToast(
            error.message
        );
    }
}


/* =========================
   DRIVER RIDE
========================= */

async function submitDriverRide(
    payload
) {
    try {
        await api(
            "/api/driver/ride",
            {
                method: "POST",

                body: JSON.stringify(
                    payload
                )
            }
        );

        showToast(
            "✅ Safar muvaffaqiyatli joylandi."
        );

        await Promise.allSettled([
            loadRides(),
            loadNotifications()
        ]);

        return true;

    } catch (error) {

        showToast(
            error.message
        );

        return false;
    }
}


/* =========================
   INIT
========================= */

async function initApp() {
    initTelegram();

    setupNavigation();

    showScreen("home");

    await loadHome();
}


document.addEventListener(
    "DOMContentLoaded",
    initApp
);


/* =========================
   GLOBAL EXPORTS
========================= */

window.showScreen =
    showScreen;

window.loadRides =
    loadRides;

window.loadOrders =
    loadOrders;

window.loadNotifications =
    loadNotifications;

window.loadProfile =
    loadProfile;

window.orderRide =
    orderRide;

window.openDriverApplication =
    openDriverApplication;

window.closeDriverApplication =
    closeDriverApplication;

window.submitDriverApplication =
    submitDriverApplication;

window.markNotificationRead =
    markNotificationRead;

window.updateProfile =
    updateProfile;

window.submitDriverRide =
    submitDriverRide;
