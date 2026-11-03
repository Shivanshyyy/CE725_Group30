// Shared by every page: open/close native <dialog>s (mobile menu, help, welcome) from data attributes.
document.addEventListener("click", (e) => {
  const opener = e.target.closest("[data-open]");
  if (opener) document.getElementById(opener.dataset.open)?.showModal();
  const closer = e.target.closest("[data-close]");
  if (closer) closer.closest("dialog")?.close();
  if (e.target.closest("dialog.drawer a")) e.target.closest("dialog").close(); // following a menu link closes the menu
});
// A click on the backdrop (the dialog element itself, outside its content) closes it.
document.querySelectorAll("dialog").forEach((d) => d.addEventListener("click", (e) => { if (e.target === d) d.close(); }));
