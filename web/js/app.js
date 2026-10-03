/* =========================================================
   OPPER TAXI
   Main Frontend JavaScript
   ========================================================= */

"use strict";

/* =========================================================
   TELEGRAM
   ========================================================= */

const tg = window.Telegram?.WebApp || null;

if (tg) {
    try {
        tg.ready();
        tg.expand();

        if (tg.setHeaderColor) {
            tg.setHeaderColor("#111111");
        }

        if (tg.setBackgroundColor) {
            tg.setBackgroundColor("#f5f5f5");
        }
    } catch (error) {
        console.error("Telegram WebApp error:", error);
    }
}


/* =========================================================
   GLOBAL VARIABLES
   ========================================================= */

let currentUser = null;
let currentPage = "home";

const API_BASE = "";


/* =========================================================
   UZBEKISTAN REGIONS / DISTRICTS
   ========================================================= */

const REGIONS = {

    "Toshkent shahri": [
        "Bektemir",
        "Chilonzor",
        "Mirobod",
        "Mirzo Ulug‘bek",
        "Olmazor",
        "Sergeli",
        "Shayxontohur",
        "Uchtepa",
        "Yakkasaroy",
        "Yashnobod",
        "Yunusobod",
        "Yangihayot"
    ],

    "Toshkent viloyati": [
        "Angren",
        "Bekobod",
        "Bo‘ka",
        "Chirchiq",
        "Chinoz",
        "Ohangaron",
        "Olmaliq",
        "Parkent",
        "Piskent",
        "Quyichirchiq",
        "Oqqo‘rg‘on",
        "Toshkent tumani",
        "Uchtepa",
        "Yangiyo‘l",
        "Yuqorichirchiq",
        "Zangiota"
    ],

    "Andijon": [
        "Andijon shahri",
        "Asaka",
        "Baliqchi",
        "Bo‘ston",
        "Buloqboshi",
        "Izboskan",
        "Jalaquduq",
        "Marhamat",
        "Oltinko‘l",
        "Paxtaobod",
        "Qo‘rg‘ontepa",
        "Shahrixon",
        "Ulug‘nor",
        "Xo‘jaobod"
    ],

    "Buxoro": [
        "Buxoro shahri",
        "Buxoro tumani",
        "G‘ijduvon",
        "Jondor",
        "Kogon",
        "Kogon shahri",
        "Olot",
        "Peshku",
        "Qorako‘l",
        "Qorovulbozor",
        "Romitan",
        "Shofirkon",
        "Vobkent"
    ],

    "Farg‘ona": [
        "Farg‘ona shahri",
        "Bag‘dod",
        "Beshariq",
        "Buvayda",
        "Dang‘ara",
        "Furqat",
        "Qo‘qon",
        "Quva",
        "Quvasoy",
        "Oltiariq",
        "Rishton",
        "So‘x",
        "Toshloq",
        "Uchko‘prik",
        "Yozyovon"
    ],

    "Jizzax": [
        "Jizzax shahri",
        "Arnasoy",
        "Baxmal",
        "Do‘stlik",
        "Forish",
        "G‘allaorol",
        "Mirzacho‘l",
        "Paxtakor",
        "Sharof Rashidov",
        "Yangiobod",
        "Zarbdor",
        "Zomin"
    ],

    "Namangan": [
        "Namangan shahri",
        "Chortoq",
        "Chust",
        "Kosonsoy",
        "Mingbuloq",
        "Norin",
        "Pop",
        "To‘raqo‘rg‘on",
        "Uchqo‘rg‘on",
        "Uychi",
        "Yangiqo‘rg‘on"
    ],

    "Navoiy": [
        "Navoiy shahri",
        "Karmana",
        "Konimex",
        "Navbahor",
        "Nurota",
        "Qiziltepa",
        "Tomdi",
        "Uchquduq",
        "Xatirchi",
        "Zarafshon"
    ],

    "Qashqadaryo": [
        "Qarshi shahri",
        "Chiroqchi",
        "Dehqonobod",
        "G‘uzor",
        "Kasbi",
        "Kitob",
        "Koson",
        "Mirishkor",
        "Muborak",
        "Nishon",
        "Qamashi",
        "Shahrisabz",
        "Yakkabog‘"
    ],

    "Samarqand": [
        "Samarqand shahri",
        "Bulung‘ur",
        "Ishtixon",
        "Jomboy",
        "Kattaqo‘rg‘on",
        "Kattaqo‘rg‘on shahri",
        "Narpay",
        "Nurobod",
        "Oqdaryo",
        "Paxtachi",
        "Payariq",
        "Pastdarg‘om",
        "Qo‘shrabot",
        "Samarqand tumani",
        "Toyloq",
        "Urgut"
    ],

    "Sirdaryo": [
        "Guliston shahri",
        "Boyovut",
        "Guliston tumani",
        "Mirzaobod",
        "Oqoltin",
        "Sardoba",
        "Sayxunobod",
        "Shirin",
        "Sirdaryo",
        "Yangiyer"
    ],

    "Surxondaryo": [
        "Termiz shahri",
        "Angor",
        "Bandixon",
        "Boysun",
        "Denov",
        "Jarqo‘rg‘on",
        "Muzrabot",
        "Oltinsoy",
        "Qiziriq",
        "Qumqo‘rg‘on",
        "Sariosiyo",
        "Sherobod",
        "Sho‘rchi",
        "Uzun"
    ],

    "Xorazm": [
        "Urganch shahri",
        "Bog‘ot",
        "Gurlan",
        "Hazorasp",
        "Xiva",
        "Xonqa",
        "Qo‘shko‘pir",
        "Shovot",
        "Tuproqqal’a",
        "Urganch tumani",
        "Yangiariq",
        "Yangibozor"
    ],

    "Qoraqalpog‘iston": [
        "Nukus shahri",
        "Amudaryo",
        "Beruniy",
        "Bo‘zatov",
        "Chimboy",
        "Ellikqal’a",
        "Kegeyli",
        "Mo‘ynoq",
        "Qanliko‘l",
        "Qo‘ng‘irot",
        "Qorao‘zak",
        "Shumanay",
        "Taxtako‘pir",
        "To‘rtko‘l",
        "Xo‘jayli"
    ]

};


/* =========================================================
   HELPERS
   ========================================================= */

function $(id) {
    return document.getElementById(id);
}


function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


function formatMoney(value) {

    const number = Number(value || 0);

    return new Intl.NumberFormat("uz-UZ").format(number) + " so‘m";
}


function formatDate(value) {

    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleDateString("uz-UZ");
}


function showLoading(element, text = "Yuklanmoqda...") {

    if (!element) {
        return;
    }

    element.innerHTML = `
        <div class="loading-state">
            <div class="loading-spinner"></div>
            <span>${escapeHtml(text)}</span>
        </div>
    `;
}


/* =========================================================
   TOAST
   ========================================================= */

let toastTimer = null;

function toast(message, type = "info") {

    const element = $("toast");

    if (!element) {
        alert(message);
        return;
    }

    element.textContent = message;

    element.classList.remove(
        "show",
        "success",
        "error",
        "warning"
    );

    if (type === "success") {
        element.classList.add("success");
    }

    if (type === "error") {
        element.classList.add("error");
    }

    if (type === "warning") {
        element.classList.add("warning");
    }

    requestAnimationFrame(() => {
        element.classList.add("show");
    });

    clearTimeout(toastTimer);

    toastTimer = setTimeout(() => {
        element.classList.remove("show");
    }, 3000);
}


/* =========================================================
   API
   ========================================================= */

async function api(endpoint, options = {}) {

    const config = {
        method: options.method || "GET",
        headers: {
            ...(options.headers || {})
        }
    };


    /*
     Telegram Mini App authentication.
    */

    if (tg && tg.initData) {

        config.headers["X-Telegram-Init-Data"] = tg.initData;

    }


    /*
     JSON body.
    */

    if (
        options.body &&
        typeof options.body === "object" &&
        !(options.body instanceof FormData)
    ) {

        config.headers["Content-Type"] = "application/json";

        config.body = JSON.stringify(options.body);

    } else if (options.body) {

        config.body = options.body;

    }


    const response = await fetch(
        API_BASE + endpoint,
        config
    );


    let data = null;

    try {

        data = await response.json();

    } catch (error) {

        data = {
            success: false,
            message: await response.text()
        };

    }


    if (!response.ok) {

        throw new Error(
            data?.message ||
            data?.error ||
            `Server xatosi: ${response.status}`
        );

    }


    return data;
}


/* =========================================================
   TELEGRAM USER
   ========================================================= */

function getTelegramUser() {

    if (
        tg &&
        tg.initDataUnsafe &&
        tg.initDataUnsafe.user
    ) {

        return tg.initDataUnsafe.user;

    }

    return null;
}


function updateHeaderUser(user) {

    const nameElement = $("headerUserName");
    const phoneElement = $("headerUserPhone");
    const avatarElement = $("headerAvatar");

    if (!user) {

        if (nameElement) {
            nameElement.textContent = "Foydalanuvchi";
        }

        if (phoneElement) {
            phoneElement.textContent = "OPPER TAXI";
        }

        return;
    }


    const fullName = [
        user.first_name,
        user.last_name
    ]
        .filter(Boolean)
        .join(" ");


    if (nameElement) {
        nameElement.textContent =
            fullName ||
            user.username ||
            "Foydalanuvchi";
    }


    if (phoneElement) {

        phoneElement.textContent =
            user.username
                ? "@" + user.username
                : "OPPER TAXI";

    }


    if (
        avatarElement &&
        user.photo_url
    ) {

        avatarElement.innerHTML = `
            <img
                src="${escapeHtml(user.photo_url)}"
                alt="Avatar"
            >
        `;

    }

}


/* =========================================================
   PAGE NAVIGATION
   ========================================================= */

function openPage(page) {

    const pages = document.querySelectorAll(".page");

    pages.forEach(element => {

        element.classList.remove("active");

    });


    const target = $(`page-${page}`);

    if (!target) {

        console.warn(
            "Page topilmadi:",
            page
        );

        return;

    }


    target.classList.add("active");


    const navButtons =
        document.querySelectorAll(".nav-btn");


    navButtons.forEach(button => {

        button.classList.toggle(
            "active",
            button.dataset.page === page
        );

    });


    currentPage = page;


    /*
     Har bir sahifa ochilganda
     kerakli ma'lumotlarni yangilaymiz.
    */

    if (page === "search") {

        initSearchPage();

    }


    if (page === "driver") {

        initDriverPage();

    }


    if (page === "orders") {

        loadOrders();

    }


    if (page === "profile") {

        loadProfile();

    }


    if (page === "notifications") {

        loadNotifications();

    }


    if (tg) {

        try {

            tg.BackButton.hide();

            if (page !== "home") {
                tg.BackButton.show();
            }

        } catch (error) {}

    }


    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });

}


/* =========================================================
   REGIONS
   ========================================================= */

function fillRegions(selectId) {

    const select = $(selectId);

    if (!select) {
        return;
    }


    const oldValue = select.value;


    select.innerHTML = `
        <option value="">
            Viloyatni tanlang
        </option>
    `;


    Object.keys(REGIONS).forEach(region => {

        const option =
            document.createElement("option");

        option.value = region;
        option.textContent = region;

        select.appendChild(option);

    });


    if (oldValue) {

        select.value = oldValue;

    }

}


function fillDistricts(regionSelectId, districtSelectId) {

    const regionSelect =
        $(regionSelectId);

    const districtSelect =
        $(districtSelectId);


    if (
        !regionSelect ||
        !districtSelect
    ) {
        return;
    }


    const region =
        regionSelect.value;


    districtSelect.innerHTML = `
        <option value="">
            Tuman / shaharni tanlang
        </option>
    `;


    if (!region) {
        return;
    }


    const districts =
        REGIONS[region] || [];


    districts.forEach(district => {

        const option =
            document.createElement("option");

        option.value = district;
        option.textContent = district;

        districtSelect.appendChild(option);

    });

}


/* =========================================================
   INITIALIZE SELECTS
   ========================================================= */

function initializeAllRegions() {

    const regionSelects = [

        "searchFromRegion",
        "searchToRegion",
        "rideFromRegion",
        "rideToRegion",
        "driverRegion"

    ];


    regionSelects.forEach(id => {

        fillRegions(id);

    });


    const driverRegion =
        $("driverRegion");


    if (driverRegion) {

        driverRegion.addEventListener(
            "change",
            () => {
                fillDistricts(
                    "driverRegion",
                    "driverDistrict"
                );
            }
        );

    }

}


/* =========================================================
   SEARCH PAGE
   ========================================================= */

function initSearchPage() {

    fillRegions("searchFromRegion");
    fillRegions("searchToRegion");


    const dateInput =
        $("searchDate");


    if (
        dateInput &&
        !dateInput.value
    ) {

        const date =
            new Date();


        const year =
            date.getFullYear();


        const month =
            String(
                date.getMonth() + 1
            ).padStart(2, "0");


        const day =
            String(
                date.getDate()
            ).padStart(2, "0");


        dateInput.value =
            `${year}-${month}-${day}`;

    }

}


/* =========================================================
   QUICK SEARCH
   ========================================================= */

function quickSearch(from, to) {

    openPage("search");


    setTimeout(() => {

        const fromSelect =
            $("searchFromRegion");

        const toSelect =
            $("searchToRegion");


        if (fromSelect) {

            fromSelect.value =
                findRegionName(from);

            fromSelect.dispatchEvent(
                new Event("change")
            );

        }


        if (toSelect) {

            toSelect.value =
                findRegionName(to);

            toSelect.dispatchEvent(
                new Event("change")
            );

        }

    }, 100);

}


function findRegionName(name) {

    if (REGIONS[name]) {
        return name;
    }


    const normalized =
        String(name)
            .toLowerCase()
            .replace(/‘/g, "'");


    const key =
        Object.keys(REGIONS)
            .find(region =>
                region
                    .toLowerCase()
                    .replace(/‘/g, "'")
                    .includes(normalized)
            );


    return key || name;

}


/* =========================================================
   SEARCH RIDES
   ========================================================= */

async function searchRides() {

    const results =
        $("searchResults");


    if (!results) {
        return;
    }


    const fromRegion =
        $("searchFromRegion")?.value || "";


    const fromDistrict =
        $("searchFromDistrict")?.value || "";


    const toRegion =
        $("searchToRegion")?.value || "";


    const toDistrict =
        $("searchToDistrict")?.value || "";


    const date =
        $("searchDate")?.value || "";


    const seats =
        $("searchSeats")?.value || "1";


    if (!fromRegion) {

        toast(
            "Qayerdan yo‘nalishini tanlang.",
            "warning"
        );

        return;

    }


    if (!toRegion) {

        toast(
            "Qayerga yo‘nalishini tanlang.",
            "warning"
        );

        return;

    }


    showLoading(
        results,
        "Safarlar qidirilmoqda..."
    );


    try {

        const params =
            new URLSearchParams();


        params.set(
            "from_region",
            fromRegion
        );


        params.set(
            "to_region",
            toRegion
        );


        if (fromDistrict) {

            params.set(
                "from_district",
                fromDistrict
            );

        }


        if (toDistrict) {

            params.set(
                "to_district",
                toDistrict
            );

        }


        if (date) {

            params.set(
                "date",
                date
            );

        }


        params.set(
            "seats",
            seats
        );


        const data =
            await api(
                `/api/rides?${params.toString()}`
            );


        const rides =
            Array.isArray(data)
                ? data
                : (
                    data.rides ||
                    data.data ||
                    []
                );


        renderRides(
            rides,
            Number(seats)
        );


    } catch (error) {

        console.error(
            "Search error:",
            error
        );


        results.innerHTML = `
            <div class="empty-state error-state">

                <div class="empty-icon">
                    ⚠️
                </div>

                <h3>
                    Xatolik yuz berdi
                </h3>

                <p>
                    ${escapeHtml(error.message)}
                </p>

                <button
                    class="secondary-btn"
                    onclick="searchRides()"
                >
                    Qayta urinish
                </button>

            </div>
        `;

    }

}


/* =========================================================
   RENDER RIDES
   ========================================================= */

function renderRides(rides, requestedSeats = 1) {

    const results =
        $("searchResults");


    if (!results) {
        return;
    }


    if (
        !Array.isArray(rides) ||
        rides.length === 0
    ) {

        results.innerHTML = `
            <div class="empty-state">

                <div class="empty-icon">
                    🚕
                </div>

                <h3>
                    Safar topilmadi
                </h3>

                <p>
                    Tanlangan yo‘nalish bo‘yicha
                    hozircha faol safarlar mavjud emas.
                </p>

            </div>
        `;

        return;

    }


    results.innerHTML = rides
        .map(ride =>
            rideCard(
                ride,
                requestedSeats
            )
        )
        .join("");

}


function rideCard(ride, requestedSeats = 1) {

    const id =
        ride.id;


    const from =
        ride.from_region ||
        ride.fromRegion ||
        "—";


    const fromDistrict =
        ride.from_district ||
        ride.fromDistrict ||
        "";


    const to =
        ride.to_region ||
        ride.toRegion ||
        "—";


    const toDistrict =
        ride.to_district ||
        ride.toDistrict ||
        "";


    const date =
        ride.travel_date ||
        ride.date ||
        "—";


    const time =
        ride.travel_time ||
        ride.time ||
        "—";


    const price =
        ride.price || 0;


    const available =
        ride.available_seats ??
        ride.seats ??
        0;


    const driverName =
        ride.driver_name ||
        [
            ride.first_name,
            ride.last_name
        ]
            .filter(Boolean)
            .join(" ") ||
        "Haydovchi";


    const car =
        [
            ride.brand,
            ride.model
        ]
            .filter(Boolean)
            .join(" ") ||
        "Avtomobil";


    const color =
        ride.color || "";


    const plate =
        ride.plate || "";


    const routeFrom =
        fromDistrict
            ? `${from}, ${fromDistrict}`
            : from;


    const routeTo =
        toDistrict
            ? `${to}, ${toDistrict}`
            : to;


    return `
        <div class="ride-card">

            <div class="ride-top">

                <div class="ride-route">

                    <div class="route-point">
                        <span class="route-dot"></span>

                        <div>
                            <small>Qayerdan</small>
                            <strong>
                                ${escapeHtml(routeFrom)}
                            </strong>
                        </div>
                    </div>


                    <div class="route-line"></div>


                    <div class="route-point">
                        <span class="route-dot"></span>

                        <div>
                            <small>Qayerga</small>
                            <strong>
                                ${escapeHtml(routeTo)}
                            </strong>
                        </div>
                    </div>

                </div>


                <div class="ride-price">
                    ${formatMoney(price)}
                </div>

            </div>


            <div class="ride-details">

                <div class="ride-detail">
                    📅
                    <span>
                        ${escapeHtml(date)}
                    </span>
                </div>

                <div class="ride-detail">
                    🕐
                    <span>
                        ${escapeHtml(time)}
                    </span>
                </div>

                <div class="ride-detail">
                    💺
                    <span>
                        ${escapeHtml(available)} ta bo‘sh
                    </span>
                </div>

            </div>


            <div class="ride-driver">

                <div class="driver-avatar">
                    👤
                </div>

                <div class="driver-info">

                    <strong>
                        ${escapeHtml(driverName)}
                    </strong>

                    <span>
                        ${escapeHtml(car)}
                        ${color ? " • " + escapeHtml(color) : ""}
                        ${plate ? " • " + escapeHtml(plate) : ""}
                    </span>

                </div>

            </div>


            <button
                class="primary-btn"
                type="button"
                onclick="orderRide(${Number(id)}, ${Number(requestedSeats)})"
            >
                🚕 Shu safarga buyurtma berish
            </button>

        </div>
    `;

}


/* =========================================================
   ORDER RIDE
   ========================================================= */

async function orderRide(
    rideId,
    seats = 1
) {

    if (!rideId) {

        toast(
            "Safar ma’lumoti topilmadi.",
            "error"
        );

        return;

    }


    const phone =
        currentUser?.phone ||
        "";


    const note =
        "";


    try {

        const result =
            await api(
                "/api/passenger/order",
                {
                    method: "POST",

                    body: {
                        ride_id: rideId,
                        seats: Number(seats),
                        phone: phone,
                        note: note
                    }

                }
            );


        if (
            result &&
            result.success === false
        ) {

            throw new Error(
                result.message ||
                "Buyurtma berishda xatolik."
            );

        }


        toast(
            result?.message ||
            "Buyurtma muvaffaqiyatli yuborildi.",
            "success"
        );


        setTimeout(() => {

            openPage("orders");

        }, 500);


    } catch (error) {

        console.error(
            "Order error:",
            error
        );


        toast(
            error.message ||
            "Buyurtma berishda xatolik.",
            "error"
        );

    }

}


/* =========================================================
   DRIVER PAGE
   ========================================================= */

function initDriverPage() {

    fillRegions("rideFromRegion");
    fillRegions("rideToRegion");
    fillRegions("driverRegion");


    setDefaultDateTime();

}


function showDriverTab(tab) {

    const rideTab =
        $("driverRideTab");


    const registerTab =
        $("driverRegisterTab");


    const rideButton =
        $("driverTabRide");


    const registerButton =
        $("driverTabRegister");


    if (
        !rideTab ||
        !registerTab
    ) {
        return;
    }


    if (tab === "register") {

        rideTab.classList.add("hidden");
        registerTab.classList.remove("hidden");


        rideButton?.classList.remove("active");
        registerButton?.classList.add("active");

    } else {

        registerTab.classList.add("hidden");
        rideTab.classList.remove("hidden");


        registerButton?.classList.remove("active");
        rideButton?.classList.add("active");

    }

}


/* =========================================================
   DEFAULT DATE / TIME
   ========================================================= */

function setDefaultDateTime() {

    const dateInput =
        $("rideDate");


    const timeInput =
        $("rideTime");


    const now =
        new Date();


    if (
        dateInput &&
        !dateInput.value
    ) {

        const year =
            now.getFullYear();


        const month =
            String(
                now.getMonth() + 1
            ).padStart(2, "0");


        const day =
            String(
                now.getDate()
            ).padStart(2, "0");


        dateInput.value =
            `${year}-${month}-${day}`;

    }


    if (
        timeInput &&
        !timeInput.value
    ) {

        const hours =
            String(
                now.getHours()
            ).padStart(2, "0");


        const minutes =
            String(
                now.getMinutes()
            ).padStart(2, "0");


        timeInput.value =
            `${hours}:${minutes}`;

    }

}


/* =========================================================
   CREATE RIDE
   ========================================================= */

async function createRide() {

    const fromRegion =
        $("rideFromRegion")?.value || "";


    const fromDistrict =
        $("rideFromDistrict")?.value || "";


    const toRegion =
        $("rideToRegion")?.value || "";


    const toDistrict =
        $("rideToDistrict")?.value || "";


    const date =
        $("rideDate")?.value || "";


    const time =
        $("rideTime")?.value || "";


    const price =
        Number(
            $("ridePrice")?.value || 0
        );


    const seats =
        Number(
            $("rideSeats")?.value || 1
        );


    const note =
        $("rideNote")?.value?.trim() || "";


    if (!fromRegion) {

        toast(
            "Qayerdan yo‘nalishini tanlang.",
            "warning"
        );

        return;

    }


    if (!toRegion) {

        toast(
            "Qayerga yo‘nalishini tanlang.",
            "warning"
        );

        return;

    }


    if (!date) {

        toast(
            "Safar sanasini tanlang.",
            "warning"
        );

        return;

    }


    if (!time) {

        toast(
            "Safar vaqtini kiriting.",
            "warning"
        );

        return;

    }


    if (price <= 0) {

        toast(
            "Narxni kiriting.",
            "warning"
        );

        return;

    }


    if (
        seats < 1 ||
        seats > 4
    ) {

        toast(
            "O‘rinlar soni 1–4 oralig‘ida bo‘lishi kerak.",
            "warning"
        );

        return;

    }


    try {

        const result =
            await api(
                "/api/driver/ride",
                {
                    method: "POST",

                    body: {
                        from_region: fromRegion,
                        from_district: fromDistrict,
                        to_region: toRegion,
                        to_district: toDistrict,
                        date: date,
                        time: time,
                        price: price,
                        seats: seats,
                        note: note
                    }

                }
            );


        if (
            result &&
            result.success === false
        ) {

            throw new Error(
                result.message ||
                "Safar joylashda xatolik."
            );

        }


        toast(
            result?.message ||
            "Safar muvaffaqiyatli joylandi.",
            "success"
        );


        /*
         Formani tozalaymiz.
        */

        $("ridePrice").value = "";
        $("rideNote").value = "";


        setTimeout(() => {

            openPage("orders");

        }, 700);


    } catch (error) {

        console.error(
            "Create ride error:",
            error
        );


        toast(
            error.message ||
            "Safar joylashda xatolik.",
            "error"
        );

    }

}


/* =========================================================
   DRIVER REGISTER
   ========================================================= */

async function registerDriver() {

    const fullName =
        $("driverFullName")?.value?.trim() || "";


    const phone =
        $("driverPhone")?.value?.trim() || "";


    const region =
        $("driverRegion")?.value || "";


    const district =
        $("driverDistrict")?.value || "";


    const passportInput =
        $("driverPassport");


    const licenseInput =
        $("driverLicense");


    if (!fullName) {

        toast(
            "F.I.Sh.ni kiriting.",
            "warning"
        );

        return;

    }


    if (!phone) {

        toast(
            "Telefon raqamni kiriting.",
            "warning"
        );

        return;

    }


    if (!region) {

        toast(
            "Viloyatni tanlang.",
            "warning"
        );

        return;

    }


    if (!passportInput?.files?.length) {

        toast(
            "Pasport / ID faylini yuklang.",
            "warning"
        );

        return;

    }


    if (!licenseInput?.files?.length) {

        toast(
            "Haydovchilik guvohnomasi faylini yuklang.",
            "warning"
        );

        return;

    }


    try {

        const formData =
            new FormData();


        formData.append(
            "full_name",
            fullName
        );


        formData.append(
            "phone",
            phone
        );


        formData.append(
            "region",
            region
        );


        formData.append(
            "district",
            district
        );


        formData.append(
            "passport",
            passportInput.files[0]
        );


        formData.append(
            "driver_license",
            licenseInput.files[0]
        );


        const result =
            await api(
                "/api/driver/register",
                {
                    method: "POST",
                    body: formData
                }
            );


        /*
         Duplicate application.
        */

        if (
            result?.already_exists
        ) {

            const status =
                result.status;


            if (status === "approved") {

                toast(
                    "Siz allaqachon haydovchi sifatida tasdiqlangansiz.",
                    "warning"
                );

            } else if (
                status === "pending"
            ) {

                toast(
                    "Arizangiz allaqachon ko‘rib chiqilmoqda.",
                    "warning"
                );

            } else {

                toast(
                    result.message ||
                    "Ariza mavjud.",
                    "warning"
                );

            }

            return;

        }


        if (
            result &&
            result.success === false
        ) {

            throw new Error(
                result.message ||
                "Ariza yuborishda xatolik."
            );

        }


        toast(
            result?.message ||
            "Haydovchilik arizasi yuborildi.",
            "success"
        );


        /*
         Formani tozalaymiz.
        */

        $("driverFullName").value = "";
        $("driverPhone").value = "";


        if (passportInput) {
            passportInput.value = "";
        }


        if (licenseInput) {
            licenseInput.value = "";
        }


        setTimeout(() => {

            showDriverTab("ride");

        }, 700);


    } catch (error) {

        console.error(
            "Driver register error:",
            error
        );


        toast(
            error.message ||
            "Ariza yuborishda xatolik.",
            "error"
        );

    }

}


/* =========================================================
   ORDERS
   ========================================================= */

async function loadOrders() {

    const container =
        $("ordersList");


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
                "/api/orders"
            );


        const orders =
            Array.isArray(data)
                ? data
                : (
                    data.orders ||
                    data.data ||
                    []
                );


        renderOrders(orders);


    } catch (error) {

        console.error(
            "Orders error:",
            error
        );


        container.innerHTML = `
            <div class="empty-state">

                <div class="empty-icon">
                    ⚠️
                </div>

                <h3>
                    Safarlar yuklanmadi
                </h3>

                <p>
                    ${escapeHtml(error.message)}
                </p>

            </div>
        `;

    }

}


/* =========================================================
   RENDER ORDERS
   ========================================================= */

function renderOrders(orders) {

    const container =
        $("ordersList");


    if (!container) {
        return;
    }


    if (
        !Array.isArray(orders) ||
        orders.length === 0
    ) {

        container.innerHTML = `
            <div class="empty-state">

                <div class="empty-icon">
                    📋
                </div>

                <h3>
                    Hozircha safarlar yo‘q
                </h3>

                <p>
                    Safar qidirishingiz yoki
                    yangi safar joylashingiz mumkin.
                </p>

                <button
                    class="primary-btn"
                    onclick="openPage('search')"
                >
                    🔎 Safar qidirish
                </button>

            </div>
        `;

        return;

    }


    container.innerHTML =
        orders
            .map(order => orderCard(order))
            .join("");

}


function orderCard(order) {

    const id =
        order.id;


    const from =
        order.from_region ||
        order.fromRegion ||
        "—";


    const fromDistrict =
        order.from_district ||
        order.fromDistrict ||
        "";


    const to =
        order.to_region ||
        order.toRegion ||
        "—";


    const toDistrict =
        order.to_district ||
        order.toDistrict ||
        "";


    const date =
        order.travel_date ||
        order.date ||
        "—";


    const time =
        order.travel_time ||
        order.time ||
        "—";


    const price =
        order.price || 0;


    const seats =
        order.seats || 1;


    const status =
        order.status ||
        "pending";


    const statusText =
        getOrderStatusText(status);


    const routeFrom =
        fromDistrict
            ? `${from}, ${fromDistrict}`
            : from;


    const routeTo =
        toDistrict
            ? `${to}, ${toDistrict}`
            : to;


    const canCancel =
        [
            "pending",
            "accepted"
        ].includes(status);


    return `
        <div class="order-card">

            <div class="order-header">

                <span class="order-id">
                    #${escapeHtml(id)}
                </span>

                <span class="status-badge status-${escapeHtml(status)}">
                    ${escapeHtml(statusText)}
                </span>

            </div>


            <div class="order-route">

                <div>
                    📍
                    <strong>
                        ${escapeHtml(routeFrom)}
                    </strong>
                </div>

                <div class="route-arrow">
                    ↓
                </div>

                <div>
                    📍
                    <strong>
                        ${escapeHtml(routeTo)}
                    </strong>
                </div>

            </div>


            <div class="order-details">

                <span>
                    📅 ${escapeHtml(date)}
                </span>

                <span>
                    🕐 ${escapeHtml(time)}
                </span>

                <span>
                    💺 ${escapeHtml(seats)}
                </span>

                <span>
                    💰 ${formatMoney(price)}
                </span>

            </div>


            ${
                canCancel
                    ? `
                        <button
                            class="danger-btn"
                            type="button"
                            onclick="cancelOrder(${Number(id)})"
                        >
                            ✕ Buyurtmani bekor qilish
                        </button>
                    `
                    : ""
            }

        </div>
    `;

}


function getOrderStatusText(status) {

    const statuses = {

        pending: "Kutilmoqda",

        accepted: "Qabul qilindi",

        rejected: "Rad etildi",

        cancelled: "Bekor qilindi",

        finished: "Yakunlandi"

    };


    return statuses[status] ||
        status ||
        "Noma’lum";

}


/* =========================================================
   CANCEL ORDER
   ========================================================= */

async function cancelOrder(orderId) {

    if (!orderId) {
        return;
    }


    const confirmed =
        window.confirm(
            "Buyurtmani bekor qilmoqchimisiz?"
        );


    if (!confirmed) {
        return;
    }


    try {

        const result =
            await api(
                "/api/order/cancel",
                {
                    method: "POST",

                    body: {
                        order_id: orderId
                    }

                }
            );


        if (
            result &&
            result.success === false
        ) {

            throw new Error(
                result.message ||
                "Buyurtmani bekor qilishda xatolik."
            );

        }


        toast(
            result?.message ||
            "Buyurtma bekor qilindi.",
            "success"
        );


        loadOrders();


    } catch (error) {

        console.error(
            "Cancel order error:",
            error
        );


        toast(
            error.message ||
            "Buyurtmani bekor qilishda xatolik.",
            "error"
        );

    }

}


/* =========================================================
   PROFILE
   ========================================================= */

async function loadProfile() {

    try {

        const data =
            await api(
                "/api/profile"
            );


        const profile =
            data?.user ||
            data?.profile ||
            data;


        if (!profile) {
            return;
        }


        renderProfile(profile);


    } catch (error) {

        console.error(
            "Profile error:",
            error
        );


        /*
         Telegram ma'lumotlari bilan
         hech bo‘lmaganda profilni ko‘rsatamiz.
        */

        if (currentUser) {

            renderProfile({
                first_name:
                    currentUser.first_name,

                last_name:
                    currentUser.last_name,

                username:
                    currentUser.username
            });

        }

    }

}


function renderProfile(profile) {

    const name =
        [
            profile.first_name,
            profile.last_name
        ]
            .filter(Boolean)
            .join(" ") ||
        profile.full_name ||
        currentUser?.first_name ||
        "Foydalanuvchi";


    const username =
        profile.username ||
        currentUser?.username ||
        "";


    const phone =
        profile.phone ||
        "—";


    const driverStatus =
        profile.driver_status ||
        profile.status ||
        "Yo‘q";


    const rating =
        profile.rating ||
        profile.average_rating ||
        "—";


    if ($("profileName")) {

        $("profileName").textContent =
            name;

    }


    if ($("profileUsername")) {

        $("profileUsername").textContent =
            username
                ? "@" + username
                : "";

    }


    if ($("profilePhone")) {

        $("profilePhone").textContent =
            phone;

    }


    if ($("profileDriverStatus")) {

        $("profileDriverStatus").textContent =
            getDriverStatusText(
                driverStatus
            );

    }


    if ($("profileRating")) {

        $("profileRating").textContent =
            rating !== "—"
                ? `⭐ ${rating}`
                : "—";

    }


    if ($("profileAvatar")) {

        if (
            currentUser?.photo_url
        ) {

            $("profileAvatar").innerHTML = `
                <img
                    src="${escapeHtml(currentUser.photo_url)}"
                    alt="Avatar"
                >
            `;

        } else {

            $("profileAvatar").textContent =
                "👤";

        }

    }

}


function getDriverStatusText(status) {

    const values = {

        approved: "Tasdiqlangan",

        pending: "Tekshirilmoqda",

        rejected: "Rad etilgan",

        "Yo‘q": "Yo‘q"

    };


    return values[status] ||
        status ||
        "Yo‘q";

}


/* =========================================================
   NOTIFICATIONS
   ========================================================= */

async function loadNotifications() {

    const container =
        $("notificationsList");


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


        const notifications =
            Array.isArray(data)
                ? data
                : (
                    data.notifications ||
                    data.data ||
                    []
                );


        renderNotifications(
            notifications
        );


        updateNotificationBadge(
            notifications
        );


    } catch (error) {

        console.error(
            "Notifications error:",
            error
        );


        container.innerHTML = `
            <div class="empty-state">

                <div class="empty-icon">
                    🔔
                </div>

                <h3>
                    Bildirishnomalar yuklanmadi
                </h3>

                <p>
                    ${escapeHtml(error.message)}
                </p>

            </div>
        `;

    }

}


/* =========================================================
   RENDER NOTIFICATIONS
   ========================================================= */

function renderNotifications(
    notifications
) {

    const container =
        $("notificationsList");


    if (!container) {
        return;
    }


    if (
        !Array.isArray(notifications) ||
        notifications.length === 0
    ) {

        container.innerHTML = `
            <div class="empty-state">

                <div class="empty-icon">
                    🔔
                </div>

                <h3>
                    Bildirishnomalar yo‘q
                </h3>

                <p>
                    Yangi xabarlar shu yerda ko‘rinadi.
                </p>

            </div>
        `;

        return;

    }


    container.innerHTML =
        notifications
            .map(notification =>
                notificationCard(
                    notification
                )
            )
            .join("");

}


function notificationCard(notification) {

    const id =
        notification.id;


    const title =
        notification.title ||
        "Bildirishnoma";


    const message =
        notification.message ||
        "";


    const createdAt =
        notification.created_at ||
        "";


    const unread =
        Number(
            notification.is_read || 0
        ) === 0;


    return `
        <div
            class="notification-card ${unread ? "unread" : ""}"
            onclick="markNotificationRead(${Number(id)})"
        >

            <div class="notification-icon">
                🔔
            </div>

            <div class="notification-content">

                <strong>
                    ${escapeHtml(title)}
                </strong>

                <p>
                    ${escapeHtml(message)}
                </p>

                ${
                    createdAt
                        ? `
                            <small>
                                ${escapeHtml(createdAt)}
                            </small>
                        `
                        : ""
                }

            </div>

        </div>
    `;

}


/* =========================================================
   NOTIFICATION BADGE
   ========================================================= */

function updateNotificationBadge(
    notifications
) {

    const badge =
        $("notificationBadge");


    if (!badge) {
        return;
    }


    const unreadCount =
        Array.isArray(notifications)
            ? notifications.filter(
                item =>
                    Number(
                        item.is_read || 0
                    ) === 0
            ).length
            : 0;


    if (unreadCount > 0) {

        badge.textContent =
            unreadCount > 99
                ? "99+"
                : unreadCount;


        badge.classList.remove(
            "hidden"
        );

    } else {

        badge.classList.add(
            "hidden"
        );

    }

}


/* =========================================================
   MARK NOTIFICATION READ
   ========================================================= */

async function markNotificationRead(
    notificationId
) {

    if (!notificationId) {
        return;
    }


    try {

        /*
         Backend hozir barcha
         notificationlarni read qiladi.
        */

        await api(
            "/api/notifications/read",
            {
                method: "POST",

                body: {
                    notification_id:
                        notificationId
                }

            }
        );


        loadNotifications();


    } catch (error) {

        console.error(
            "Notification read error:",
            error
        );

    }

}


/* =========================================================
   HELP
   ========================================================= */

function showHelp() {

    const username =
        "Oppertaxibot";


    if (tg) {

        try {

            tg.openTelegramLink(
                `https://t.me/${username}`
            );

            return;

        } catch (error) {}

    }


    window.open(
        `https://t.me/${username}`,
        "_blank"
    );

}


/* =========================================================
   URL MODE
   ========================================================= */

function checkUrlMode() {

    const params =
        new URLSearchParams(
            window.location.search
        );


    const mode =
        params.get("mode");


    if (mode === "driver") {

        openPage("driver");

        showDriverTab("ride");

    }

}


/* =========================================================
   TELEGRAM BACK BUTTON
   ========================================================= */

function setupTelegramBackButton() {

    if (!tg) {
        return;
    }


    try {

        tg.BackButton.onClick(() => {

            openPage("home");

        });

    } catch (error) {

        console.error(
            "BackButton error:",
            error
        );

    }

}


/* =========================================================
   INITIALIZATION
   ========================================================= */

async function initializeApp() {

    console.log(
        "OPPER TAXI Mini App ishga tushmoqda..."
    );


    /*
     Telegram user
    */

    currentUser =
        getTelegramUser();


    updateHeaderUser(
        currentUser
    );


    /*
     Selectlar
    */

    initializeAllRegions();


    /*
     Default date
    */

    setDefaultDateTime();


    /*
     Search date
    */

    initSearchPage();


    /*
     Telegram back button
    */

    setupTelegramBackButton();


    /*
     URL mode
    */

    checkUrlMode();


    /*
     Profilni oldindan yuklash.
    */

    try {

        await loadProfile();

    } catch (error) {

        console.log(
            "Profile initial load:",
            error
        );

    }


    /*
     Bildirishnomalarni oldindan yuklash.
    */

    try {

        const data =
            await api(
                "/api/notifications"
            );


        const notifications =
            Array.isArray(data)
                ? data
                : (
                    data.notifications ||
                    data.data ||
                    []
                );


        updateNotificationBadge(
            notifications
        );

    } catch (error) {

        console.log(
            "Notification initial load:",
            error
        );

    }


    console.log(
        "OPPER TAXI Mini App tayyor."
    );

}


/* =========================================================
   DOM READY
   ========================================================= */

if (
    document.readyState ===
    "loading"
) {

    document.addEventListener(
        "DOMContentLoaded",
        initializeApp
    );

} else {

    initializeApp();

}


/* =========================================================
   GLOBAL EXPORTS
   =========================================================
   HTML onclick ishlashi uchun.
   ========================================================= */

window.openPage = openPage;
window.quickSearch = quickSearch;
window.fillRegions = fillRegions;
window.fillDistricts = fillDistricts;
window.searchRides = searchRides;
window.orderRide = orderRide;
window.createRide = createRide;
window.registerDriver = registerDriver;
window.showDriverTab = showDriverTab;
window.loadOrders = loadOrders;
window.cancelOrder = cancelOrder;
window.loadProfile = loadProfile;
window.loadNotifications = loadNotifications;
window.markNotificationRead = markNotificationRead;
window.showHelp = showHelp;
window.toast = toast;
window.escapeHtml = escapeHtml;
