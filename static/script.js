"use strict";

const mainNav = document.querySelector(".main-nav");
const mainNavList = document.querySelector(".main-nav-list");
const footerDate = document.querySelector(".footer-date");
const menuBtn = document.querySelector(".menu-btn");
const menuBtnOpen = document.querySelector(".menu-btn-open");
const menuBtnClose = document.querySelector(".menu-btn-close");

footerDate.textContent = new Date().getFullYear();

menuBtn.addEventListener("click", () => {
  mainNav.classList.toggle("active");
  menuBtn.classList.toggle("opened");
  if (menuBtn.classList.contains("opened")) {
    menuBtnClose.style.display = "block";
    menuBtnOpen.style.display = "none";
  } else {
    menuBtnClose.style.display = "none";
    menuBtnOpen.style.display = "block";
  }
});
