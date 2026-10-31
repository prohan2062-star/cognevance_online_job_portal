const toggle = document.getElementById("menuToggle");
const links = document.getElementById("navLinks");

if (toggle && links) {
    toggle.addEventListener("click", () => {
        const isOpen = links.classList.toggle("open");
        toggle.setAttribute("aria-expanded", String(isOpen));
        toggle.setAttribute("aria-label", isOpen ? "Close navigation" : "Open navigation");
    });
}
