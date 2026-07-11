(() => {
  document.documentElement.classList.add("js");

  const year = document.getElementById("copyrightYear");
  if (year) year.textContent = `© ${new Date().getFullYear()}`;

  const revealItems = [...document.querySelectorAll("[data-reveal]")];
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (reduceMotion || !("IntersectionObserver" in window)) {
    revealItems.forEach((item) => item.classList.add("is-visible"));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    },
    { rootMargin: "0px 0px -8%", threshold: 0.12 }
  );

  revealItems.forEach((item) => observer.observe(item));
})();
